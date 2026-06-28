#!/usr/bin/env bash
# =============================================================================
# X-8G2T Watchdog  —  build, start, and self-heal the entire stack
# -----------------------------------------------------------------------------
# Brings up every container (databases, IoT pipeline, GPU AI servers, agent
# brain, MCP, observability, BI…) then continuously watches them. If a service
# is missing, exited, or unhealthy, the watchdog turns it back on.
#
# Docker's own `restart: unless-stopped` handles crashes; this adds the layer
# Docker does NOT: recreating missing containers and recovering *unhealthy*
# (but still-running) ones, with backoff so a broken service can't restart-storm.
#
# Usage:
#   scripts/watchdog.sh [options]
#
# Options:
#   -p, --profile <name>   compose profile to manage   (default: all)
#   -i, --interval <secs>  seconds between checks       (default: 15)
#       --no-build         don't (re)build images on initial bring-up
#       --no-up            skip initial bring-up, just watch + heal
#       --no-heal          only start missing services, don't restart unhealthy
#       --once             run a single check pass, then exit (good for cron)
#       --dry-run          report actions without executing them
#   -h, --help             show this help
#
# Examples:
#   scripts/watchdog.sh                      # build + up --profile all, then watch
#   scripts/watchdog.sh -p core -i 10        # core profile, check every 10s
#   scripts/watchdog.sh --no-up --once       # one health report, change nothing
#   make watch                               # same as default
# =============================================================================
set -uo pipefail

# ── Config / defaults ────────────────────────────────────────────────────────
PROFILE="all"
INTERVAL=15
DO_BUILD=1
DO_UP=1
DO_HEAL=1
ONCE=0
DRY_RUN=0

# Services that intentionally run once and exit — never treated as "down".
# Override with: ONESHOT_SERVICES="rag-indexer other-job"
ONESHOT_SERVICES="${ONESHOT_SERVICES:-rag-indexer}"

# Heal backoff: don't act on the same service more often than COOLDOWN seconds;
# after MAX_ATTEMPTS failed recoveries, back off to LONG_COOLDOWN and keep going.
COOLDOWN=60
MAX_ATTEMPTS=4
LONG_COOLDOWN=300
# Grace period after a (re)start before we judge a service unhealthy/down.
START_GRACE=45

# ── Locate the repo + compose file ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# ── Pretty logging ───────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_DIM=$'\e[2m'; C_RED=$'\e[31m'; C_GRN=$'\e[32m'; C_YEL=$'\e[33m'
  C_BLU=$'\e[34m'; C_CYN=$'\e[36m'; C_RST=$'\e[0m'
else
  C_DIM=""; C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_CYN=""; C_RST=""
fi
ts()   { date '+%Y-%m-%d %H:%M:%S'; }
log()  { printf '%s %s\n'            "${C_DIM}$(ts)${C_RST}" "$*"; }
info() { printf '%s %sℹ%s  %s\n'     "${C_DIM}$(ts)${C_RST}" "$C_BLU" "$C_RST" "$*"; }
ok()   { printf '%s %s✓%s  %s\n'     "${C_DIM}$(ts)${C_RST}" "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s %s⚠%s  %s\n'     "${C_DIM}$(ts)${C_RST}" "$C_YEL" "$C_RST" "$*"; }
err()  { printf '%s %s✗%s  %s\n'     "${C_DIM}$(ts)${C_RST}" "$C_RED" "$C_RST" "$*"; }
act()  { printf '%s %s▶%s  %s\n'     "${C_DIM}$(ts)${C_RST}" "$C_CYN" "$C_RST" "$*"; }

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--profile)  PROFILE="$2"; shift 2 ;;
    -i|--interval) INTERVAL="$2"; shift 2 ;;
    --no-build)    DO_BUILD=0; shift ;;
    --no-up)       DO_UP=0; shift ;;
    --no-heal)     DO_HEAL=0; shift ;;
    --once)        ONCE=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    -h|--help)     sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)             err "Unknown option: $1"; exit 2 ;;
  esac
done

export COMPOSE_PROFILES="$PROFILE"
COMPOSE=(docker compose)

# ── Run-or-explain wrapper (honours --dry-run) ───────────────────────────────
run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '%s   %s[dry-run]%s %s\n' "${C_DIM}$(ts)${C_RST}" "$C_DIM" "$C_RST" "$*"
    return 0
  fi
  "$@"
}

# ── State trackers (associative arrays) ──────────────────────────────────────
declare -A LAST_ACTION    # svc -> epoch of last heal action
declare -A ATTEMPTS       # svc -> consecutive recovery attempts
declare -A START_TIME     # svc -> epoch we last (re)started it

is_oneshot() {
  local s="$1"
  for o in $ONESHOT_SERVICES; do [[ "$s" == "$o" ]] && return 0; done
  return 1
}

# ── Preflight: docker, .env, certs, models ───────────────────────────────────
preflight() {
  command -v docker >/dev/null 2>&1 || { err "docker not found on PATH"; exit 1; }
  docker compose version >/dev/null 2>&1 || { err "'docker compose' (v2) not available"; exit 1; }
  docker info >/dev/null 2>&1 || { err "Docker daemon not reachable — is it running?"; exit 1; }

  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      warn ".env missing — creating it from .env.example (edit the <CHANGE_ME> values!)"
      run cp .env.example .env
    else
      err ".env and .env.example both missing — cannot continue"; exit 1
    fi
  fi

  # TLS certs for MQTT/EMQX (generate-certs.sh writes them into ssl/)
  if [[ ! -f ssl/ca.crt ]]; then
    if [[ -x ssl/generate-certs.sh ]]; then
      warn "TLS certs missing — generating them (ssl/generate-certs.sh)"
      run bash -c 'cd ssl && ./generate-certs.sh'
    else
      warn "TLS certs missing and ssl/generate-certs.sh not found — EMQX TLS may fail"
    fi
  fi

  # GGUF models for the GPU servers (non-fatal, just warn)
  if [[ -d models ]]; then
    if [[ -z "$(find models -maxdepth 2 -name '*.gguf' 2>/dev/null | head -1)" ]]; then
      warn "No *.gguf model files under ./models — GPU servers (llm/vlm/embeddings) will stay unhealthy until you run: make models"
    fi
  fi
  ok "Preflight passed (docker ok, .env present)"
}

# ── Expected long-running services for the active profile ────────────────────
expected_services() {
  "${COMPOSE[@]}" config --services 2>/dev/null | while read -r s; do
    is_oneshot "$s" || echo "$s"
  done
}

# ── Inspect one service → "status|health|exitcode" ───────────────────────────
#   status:   running|exited|created|restarting|paused|dead|missing
#   health:   healthy|unhealthy|starting|none
svc_state() {
  local svc="$1" cid
  cid="$("${COMPOSE[@]}" ps -q "$svc" 2>/dev/null | head -1)"
  if [[ -z "$cid" ]]; then echo "missing|none|-"; return; fi
  docker inspect -f \
    '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.State.ExitCode}}' \
    "$cid" 2>/dev/null || echo "missing|none|-"
}

# ── Initial bring-up ─────────────────────────────────────────────────────────
bringup() {
  if [[ $DO_UP -eq 0 ]]; then info "Skipping initial bring-up (--no-up)"; return; fi
  if [[ $DO_BUILD -eq 1 ]]; then
    act "Building + starting all services (profile: $PROFILE) …"
    run "${COMPOSE[@]}" --profile "$PROFILE" up -d --build
  else
    act "Starting all services (profile: $PROFILE, no build) …"
    run "${COMPOSE[@]}" --profile "$PROFILE" up -d
  fi
  local now; now="$(date +%s)"
  for s in $(expected_services); do START_TIME["$s"]="$now"; done
  ok "Bring-up issued — entering watch loop"
}

# ── Decide + apply recovery for one service ──────────────────────────────────
heal_service() {
  local svc="$1" state status health now started since last
  state="$(svc_state "$svc")"
  status="${state%%|*}"; rest="${state#*|}"; health="${rest%%|*}"
  now="$(date +%s)"
  started="${START_TIME[$svc]:-0}"
  since=$(( now - started ))

  case "$status" in
    running)
      if [[ "$health" == "unhealthy" ]]; then
        # Give a freshly (re)started service time before judging it
        if (( since < START_GRACE )); then return; fi
        [[ $DO_HEAL -eq 0 ]] && { warn "$svc is UNHEALTHY (heal disabled)"; return; }
        recover "$svc" "unhealthy" restart
      fi
      # running + healthy/starting/none → nothing to do
      ;;
    restarting)
      warn "$svc is restarting (Docker is retrying it)"
      ;;
    exited|dead|created|paused|missing)
      recover "$svc" "$status" up
      ;;
    *)
      warn "$svc in unexpected state: $status"
      ;;
  esac
}

# recover <svc> <reason> <up|restart>
recover() {
  local svc="$1" reason="$2" mode="$3" now last attempts cooldown
  now="$(date +%s)"
  last="${LAST_ACTION[$svc]:-0}"
  attempts="${ATTEMPTS[$svc]:-0}"

  # Backoff: escalate cooldown once we've tried too many times
  cooldown=$COOLDOWN
  (( attempts >= MAX_ATTEMPTS )) && cooldown=$LONG_COOLDOWN
  if (( now - last < cooldown )); then return; fi

  ATTEMPTS["$svc"]=$(( attempts + 1 ))
  LAST_ACTION["$svc"]=$now
  START_TIME["$svc"]=$now

  if (( attempts + 1 > MAX_ATTEMPTS )); then
    err "$svc still $reason after $((attempts+1)) tries — backing off ${LONG_COOLDOWN}s (needs attention: docker compose logs $svc)"
  fi

  if [[ "$mode" == "restart" ]]; then
    act "Healing $svc ($reason) → restart  [attempt $((attempts+1))]"
    run "${COMPOSE[@]}" restart "$svc"
  else
    act "Healing $svc ($reason) → up -d    [attempt $((attempts+1))]"
    run "${COMPOSE[@]}" --profile "$PROFILE" up -d "$svc"
  fi
}

# ── A single watch pass over every expected service ──────────────────────────
watch_pass() {
  local total=0 up=0 healthy=0 problems=0
  for svc in $(expected_services); do
    total=$(( total + 1 ))
    local state status health
    state="$(svc_state "$svc")"
    status="${state%%|*}"; rest="${state#*|}"; health="${rest%%|*}"

    case "$status" in
      running)
        up=$(( up + 1 ))
        if [[ "$health" == "healthy" || "$health" == "none" || "$health" == "starting" ]]; then
          healthy=$(( healthy + 1 ))
        fi
        ;;
    esac

    if [[ "$status" != "running" ]] || [[ "$health" == "unhealthy" ]]; then
      problems=$(( problems + 1 ))
    fi
    heal_service "$svc"

    # Reset attempt counter once a service is back to healthy/none
    if [[ "$status" == "running" && ( "$health" == "healthy" || "$health" == "none" ) ]]; then
      ATTEMPTS["$svc"]=0
    fi
  done

  if (( problems == 0 )); then
    ok "All $up/$total services up ($healthy healthy)"
  else
    warn "$up/$total up · $problems need attention"
  fi
}

# ── Signal handling ──────────────────────────────────────────────────────────
shutdown() { echo; info "Watchdog stopping (containers keep running). Bye."; exit 0; }
trap shutdown INT TERM

# ── Main ─────────────────────────────────────────────────────────────────────
echo "${C_BLU}┌─────────────────────────────────────────────────────────────┐${C_RST}"
echo "${C_BLU}│  X-8G2T Watchdog — build · start · self-heal                 │${C_RST}"
echo "${C_BLU}└─────────────────────────────────────────────────────────────┘${C_RST}"
info "profile=$PROFILE  interval=${INTERVAL}s  build=$DO_BUILD  heal=$DO_HEAL  dry-run=$DRY_RUN"
[[ -n "${ONESHOT_SERVICES// }" ]] && info "one-shot (not watched): $ONESHOT_SERVICES"

preflight
bringup

if [[ $ONCE -eq 1 ]]; then
  info "Single pass (--once)"
  watch_pass
  exit 0
fi

info "Watching every ${INTERVAL}s — Ctrl-C to stop"
while true; do
  watch_pass
  sleep "$INTERVAL"
done
