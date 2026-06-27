"""
X-8G2T Observability API
========================
Collects Jetson Orin Nano board metrics + Docker container metrics and
pushes a full snapshot to every connected WebSocket client every 1 second.

REST endpoints (for one-shot queries):
  GET  /health                        — liveness probe
  GET  /api/metrics                   — full snapshot (board + all containers)
  GET  /api/board                     — board metrics only
  GET  /api/containers                — all containers (no logs)
  GET  /api/containers/{name}/logs    — last N log lines for a container

WebSocket:
  WS   /ws   — streams a full snapshot every 1 second
"""
import asyncio
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import docker
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="X-8G2T Observability API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
except Exception as e:
    print(f"[warn] Docker client unavailable: {e}")
    docker_client = None

# Thread pool for blocking Docker/psutil calls (one thread per container + board)
executor = ThreadPoolExecutor(max_workers=32)

# Shared state updated by the background loop
latest_metrics: dict = {}
connected_clients: list[WebSocket] = []


# ─── Board metrics ─────────────────────────────────────────────────────────────

def _sysfs_read(path: Path) -> Optional[str]:
    """Read a sysfs virtual file safely — avoids buffered-IO issues with kernel files."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _read_thermal_zones() -> dict[str, float]:
    """Read Jetson thermal zones from /sys (mounted from host)."""
    temps: dict[str, float] = {}

    base = Path("/sys/devices/virtual/thermal")
    if base.exists():
        for zone in sorted(base.glob("thermal_zone*")):
            raw_temp = _sysfs_read(zone / "temp")
            raw_type = _sysfs_read(zone / "type")
            if raw_temp and raw_type:
                try:
                    temps[raw_type] = round(int(raw_temp) / 1000.0, 1)
                except (ValueError, TypeError):
                    pass

    # psutil sensors as supplement
    try:
        for chip, sensors in (psutil.sensors_temperatures() or {}).items():
            for s in sensors:
                if s.current is not None:
                    key = f"{chip}/{s.label}" if s.label else chip
                    temps.setdefault(key, round(s.current, 1))
    except Exception:
        pass

    return temps


def _parse_tegrastats(line: str) -> dict:
    """Extract GPU/EMC metrics from a tegrastats output line."""
    out: dict = {}
    m = re.search(r"GR3D_FREQ\s+(\d+)%", line)
    if m:
        out["gpu_percent"] = int(m.group(1))
    m = re.search(r"RAM\s+(\d+)/(\d+)MB", line)
    if m:
        out["tegra_ram_used_mb"] = int(m.group(1))
        out["tegra_ram_total_mb"] = int(m.group(2))
    m = re.search(r"EMC_FREQ\s+(\d+)%", line)
    if m:
        out["emc_percent"] = int(m.group(1))
    return out


def _get_tegrastats() -> dict:
    """Run tegrastats for one reading (best-effort — skipped if not available)."""
    try:
        out = subprocess.check_output(
            ["tegrastats", "--interval", "500", "--count", "1"],
            timeout=3, stderr=subprocess.DEVNULL,
        ).decode().strip().splitlines()
        for line in out:
            parsed = _parse_tegrastats(line)
            if parsed:
                return parsed
    except Exception:
        pass
    return {}


def collect_board_metrics() -> dict:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    net = psutil.net_io_counters()
    freq = psutil.cpu_freq()

    # Disk — deduplicate by device so container bind-mounts don't repeat the same device
    disks: dict = {}
    seen_devices: set = set()
    skip_fs = {"tmpfs", "devtmpfs", "squashfs", "overlay", "proc", "sysfs",
                "cgroup", "cgroup2", "devpts", "mqueue", "hugetlbfs", "nsfs",
                "pstore", "bpf", "tracefs", "securityfs", "configfs", "fusectl"}
    for part in psutil.disk_partitions(all=False):
        if not part.fstype or part.fstype in skip_fs:
            continue
        if part.device in seen_devices:
            continue
        seen_devices.add(part.device)
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks[part.device] = {
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
        except (PermissionError, OSError):
            pass

    # Network — read from /proc/1/net/dev (host network namespace via pid:host)
    # so we see the actual host interfaces, not just the container's veth
    net_ifaces: dict = {}
    host_net_dev = Path("/proc/1/net/dev")
    if host_net_dev.exists():
        try:
            lines = host_net_dev.read_text().splitlines()[2:]  # skip header rows
            for line in lines:
                parts = line.split()
                if len(parts) < 10:
                    continue
                iface = parts[0].rstrip(":")
                net_ifaces[iface] = {
                    "bytes_recv": int(parts[1]),
                    "packets_recv": int(parts[2]),
                    "errin": int(parts[3]),
                    "bytes_sent": int(parts[9]),
                    "packets_sent": int(parts[10]),
                    "errout": int(parts[11]),
                }
        except Exception:
            pass
    # fallback to psutil if /proc/1/net/dev unreadable
    if not net_ifaces:
        for iface, stats in psutil.net_io_counters(pernic=True).items():
            net_ifaces[iface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin,
                "errout": stats.errout,
            }

    board = {
        "cpu_percent": round(psutil.cpu_percent(), 1),
        "cpu_per_core": [round(p, 1) for p in psutil.cpu_percent(percpu=True)],
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_freq_mhz": round(freq.current, 0) if freq else None,
        "cpu_freq_max_mhz": round(freq.max, 0) if freq else None,
        "load_avg": [round(x, 2) for x in psutil.getloadavg()],
        "memory": {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "buffers": getattr(mem, "buffers", 0),
            "cached": getattr(mem, "cached", 0),
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
        },
        "disk": disks,
        "net_total": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        },
        "net_ifaces": net_ifaces,
        "temperatures": _read_thermal_zones(),
        "uptime_seconds": round(time.time() - psutil.boot_time()),
        "boot_time": psutil.boot_time(),
        **_get_tegrastats(),   # gpu_percent, emc_percent if tegrastats available
    }
    return board


# ─── Container metrics ─────────────────────────────────────────────────────────

def _cpu_percent_from_stats(stats: dict) -> float:
    try:
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        sys_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        num_cpus = stats["cpu_stats"].get(
            "online_cpus",
            len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or [1]),
        )
        if sys_delta > 0 and cpu_delta >= 0:
            return round((cpu_delta / sys_delta) * num_cpus * 100.0, 2)
    except (KeyError, ZeroDivisionError, TypeError):
        pass
    return 0.0


def _fetch_one_container(c) -> dict:
    info: dict = {
        "id": c.short_id,
        "name": c.name,
        "status": c.status,
        "image": c.image.tags[0] if c.image.tags else c.attrs.get("Image", "")[:20],
        "created": c.attrs["Created"],
        "health": (
            c.attrs.get("State", {}).get("Health", {}) or {}
        ).get("Status", "none"),
        "restart_count": c.attrs.get("RestartCount", 0),
        "ports": c.attrs.get("NetworkSettings", {}).get("Ports", {}),
        "cpu_percent": 0.0,
        "memory_usage": 0,
        "memory_limit": 0,
        "memory_percent": 0.0,
        "net_rx_bytes": 0,
        "net_tx_bytes": 0,
        "block_read_bytes": 0,
        "block_write_bytes": 0,
        "logs": [],
    }

    if c.status != "running":
        return info

    # Stats (CPU, memory, net, blkio)
    try:
        stats = c.stats(stream=False)
        info["cpu_percent"] = _cpu_percent_from_stats(stats)

        mem = stats.get("memory_stats", {})
        usage = mem.get("usage", 0)
        # Subtract cache so the number matches what `docker stats` shows
        cache = (mem.get("stats") or {}).get("cache", 0)
        info["memory_usage"] = max(usage - cache, 0)
        info["memory_limit"] = mem.get("limit", 0)
        info["memory_percent"] = round(
            info["memory_usage"] / info["memory_limit"] * 100
            if info["memory_limit"] else 0.0, 2
        )

        for iface in (stats.get("networks") or {}).values():
            info["net_rx_bytes"] += iface.get("rx_bytes", 0)
            info["net_tx_bytes"] += iface.get("tx_bytes", 0)

        for bio in (stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []):
            op = bio.get("op", "").lower()
            if op == "read":
                info["block_read_bytes"] += bio.get("value", 0)
            elif op == "write":
                info["block_write_bytes"] += bio.get("value", 0)
    except Exception as e:
        info["stats_error"] = str(e)

    # Last 30 log lines
    try:
        raw = c.logs(tail=30, timestamps=True)
        if isinstance(raw, bytes):
            info["logs"] = raw.decode("utf-8", errors="replace").splitlines()
    except Exception:
        pass

    return info


async def collect_container_metrics_async() -> list[dict]:
    if not docker_client:
        return []
    loop = asyncio.get_event_loop()
    containers = await loop.run_in_executor(
        executor, lambda: docker_client.containers.list(all=True)
    )
    results = await asyncio.gather(
        *[loop.run_in_executor(executor, _fetch_one_container, c) for c in containers],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


# ─── WebSocket manager ─────────────────────────────────────────────────────────

async def _broadcast(payload: dict) -> None:
    dead: list[WebSocket] = []
    for ws in connected_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connected_clients:
            connected_clients.remove(ws)


# ─── Background metrics loop ───────────────────────────────────────────────────

async def _metrics_loop() -> None:
    loop = asyncio.get_event_loop()
    psutil.cpu_percent()           # prime the counter (first call always returns 0)
    psutil.cpu_percent(percpu=True)

    while True:
        t0 = time.monotonic()

        # Collect board and containers independently so one failure can't kill the other
        try:
            board = await loop.run_in_executor(executor, collect_board_metrics)
        except Exception as e:
            print(f"[metrics_loop/board] {e}")
            board = latest_metrics.get("board", {})

        try:
            containers = await collect_container_metrics_async()
        except Exception as e:
            print(f"[metrics_loop/containers] {e}")
            containers = latest_metrics.get("containers", [])

        latest_metrics.update({
            "timestamp": time.time(),
            "board": board,
            "containers": containers,
        })

        if connected_clients:
            await _broadcast(latest_metrics)

        # Sleep for the remainder of the 1-second window
        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, 1.0 - elapsed))


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_metrics_loop())


# ─── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp": time.time(), "clients": len(connected_clients)}


@app.get("/api/metrics")
def api_metrics() -> dict:
    return latest_metrics or {"error": "metrics not yet collected — wait 1s"}


@app.get("/api/board")
def api_board() -> dict:
    return latest_metrics.get("board", {})


@app.get("/api/containers")
def api_containers() -> list:
    return [
        {k: v for k, v in c.items() if k != "logs"}
        for c in latest_metrics.get("containers", [])
    ]


@app.get("/api/containers/{name}/logs")
def api_logs(name: str, lines: int = 200) -> dict:
    if not docker_client:
        return {"error": "Docker unavailable"}
    try:
        c = docker_client.containers.get(name)
        raw = c.logs(tail=lines, timestamps=True)
        return {"name": name, "logs": raw.decode("utf-8", errors="replace").splitlines()}
    except Exception as e:
        return {"error": str(e)}


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    connected_clients.append(ws)
    # Send the latest snapshot immediately so the client doesn't wait 1s
    if latest_metrics:
        await ws.send_json(latest_metrics)
    try:
        while True:
            await ws.receive_text()   # absorb keep-alive pings from the client
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
