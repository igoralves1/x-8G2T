"""
X-8G2T Observability API  —  Jetson Orin Nano
==============================================
Full hardware + container metrics at 1-second resolution.

Board metrics:
  CPU   — utilisation per core, frequency per core, governor, temperature
  GPU   — utilisation %, current/max frequency, memory (unified), temperature
  RAM   — used / total / available / buffers / cached (unified memory pool)
  SWAP  — zram swap
  DISK  — per-device usage + read/write I/O counters (eMMC + NVMe0 + NVMe1)
  NET   — per-interface bytes/packets (host namespace via /proc/1/net/dev)
  POWER — INA3221 rails: VDD_IN / VDD_CPU_GPU_CV / VDD_SOC  (mA, mV, mW)
  TEMP  — all Jetson thermal zones from /sys/devices/virtual/thermal/
  EMC   — memory-controller utilisation % and frequency (via tegrastats)
  FAN   — fan RPM and PWM from hwmon0 / hwmon2 (if available)

Tegrastats (GPU util, EMC, per-core CPU util+freq) is read by running
  nsenter --target 1 --mount -- /usr/bin/tegrastats --interval 1000
in a background thread. Requires privileged: true in docker-compose.

REST:
  GET /health
  GET /api/metrics                    full snapshot
  GET /api/board                      board only
  GET /api/containers                 all containers (no logs)
  GET /api/containers/{name}/logs     last N log lines

WebSocket:
  WS /ws    →  full snapshot every 1 second
"""
import asyncio
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import docker
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="X-8G2T Observability API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

try:
    docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
except Exception:
    docker_client = None

executor = ThreadPoolExecutor(max_workers=32)
latest_metrics: dict = {}
connected_clients: list[WebSocket] = []


# ─── sysfs helpers ────────────────────────────────────────────────────────────

def _sysfs(path) -> Optional[str]:
    """Read a sysfs/procfs file safely (avoids buffered-IO issues with kernel vfs)."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _sysfs_int(path, scale: float = 1) -> Optional[float]:
    v = _sysfs(path)
    try:
        return round(int(v) * scale, 3) if v is not None else None
    except (ValueError, TypeError):
        return None


# ─── Tegrastats background reader ─────────────────────────────────────────────

class TegrastatsReader:
    """
    Runs tegrastats continuously via nsenter (host mount namespace) and
    keeps the latest parsed snapshot in self.latest.
    Requires the container to be privileged.
    """

    GPU_RE    = re.compile(r"GR3D_FREQ\s+(\d+)%@(\d+)")
    CPU_RE    = re.compile(r"CPU \[([^\]]+)\]")
    EMC_RE    = re.compile(r"EMC_FREQ\s+(\d+)%@(\d+)")
    VIC_RE    = re.compile(r"VIC_FREQ\s+(\d+)%@(\d+)")
    RAM_RE    = re.compile(r"RAM\s+(\d+)/(\d+)MB(?:\s+\(lfb\s+(\d+)x(\d+)MB\))?")
    SWAP_RE   = re.compile(r"SWAP\s+(\d+)/(\d+)MB")
    TEMP_RE   = re.compile(r"(\w+)@([\d.]+)C")
    POWER_RE  = re.compile(r"(VDD_\w+|VIN_\w+|VDDQ_\w+)\s+(\d+)/(\d+)")

    def __init__(self):
        self.latest: dict = {}
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self.available = False

    def start(self):
        try:
            self._proc = subprocess.Popen(
                ["nsenter", "--target", "1", "--mount", "--",
                 "/usr/bin/tegrastats", "--interval", "1000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self.available = True
            print("[tegrastats] started via nsenter")
        except Exception as e:
            print(f"[tegrastats] not available: {e}")

    def _loop(self):
        for raw in self._proc.stdout:
            try:
                self.latest = self._parse(raw.decode("utf-8", errors="replace"))
            except Exception:
                pass

    def _parse(self, line: str) -> dict:
        out: dict = {}

        m = self.GPU_RE.search(line)
        if m:
            out["gpu_util_percent"] = int(m.group(1))
            out["gpu_freq_mhz"]     = int(m.group(2))

        m = self.EMC_RE.search(line)
        if m:
            out["emc_util_percent"] = int(m.group(1))
            out["emc_freq_mhz"]     = int(m.group(2))

        m = self.VIC_RE.search(line)
        if m:
            out["vic_util_percent"] = int(m.group(1))

        m = self.RAM_RE.search(line)
        if m:
            out["tegra_ram_used_mb"]  = int(m.group(1))
            out["tegra_ram_total_mb"] = int(m.group(2))
            out["tegra_ram_percent"]  = round(int(m.group(1)) / int(m.group(2)) * 100, 1)
            if m.group(3):
                out["tegra_ram_lfb_blocks"] = int(m.group(3))
                out["tegra_ram_lfb_mb"]     = int(m.group(4))

        m = self.SWAP_RE.search(line)
        if m:
            out["tegra_swap_used_mb"]  = int(m.group(1))
            out["tegra_swap_total_mb"] = int(m.group(2))

        m = self.CPU_RE.search(line)
        if m:
            cores = []
            for token in m.group(1).split(","):
                try:
                    if token.strip() == "off":
                        cores.append({"util_percent": 0, "freq_mhz": 0, "active": False})
                    else:
                        u, f = token.split("@")
                        cores.append({
                            "util_percent": int(u.rstrip("%")),
                            "freq_mhz": int(f),
                            "active": True,
                        })
                except Exception:
                    pass
            if cores:
                out["cpu_cores"] = cores

        temps = {}
        for m in self.TEMP_RE.finditer(line):
            name = m.group(1)
            # skip frequency annotations like 1228 (just numbers after @)
            if name not in ("NC",):
                try:
                    temps[name] = float(m.group(2))
                except ValueError:
                    pass
        if temps:
            out["tegra_temps"] = temps

        power_rails = {}
        for m in self.POWER_RE.finditer(line):
            power_rails[m.group(1)] = {
                "current_mw": int(m.group(2)),
                "average_mw": int(m.group(3)),
            }
        if power_rails:
            out["tegra_power_rails"] = power_rails

        return out

    def get(self) -> dict:
        return self.latest.copy()

    def stop(self):
        if self._proc:
            self._proc.terminate()


tegrastats = TegrastatsReader()


# ─── GPU (sysfs) ──────────────────────────────────────────────────────────────

_GPU_DEVFREQ = "/sys/class/devfreq/17000000.gpu"

def collect_gpu_sysfs() -> dict:
    cur  = _sysfs_int(f"{_GPU_DEVFREQ}/cur_freq", 1e-6)   # Hz → MHz
    mx   = _sysfs_int(f"{_GPU_DEVFREQ}/max_freq", 1e-6)
    mn   = _sysfs_int(f"{_GPU_DEVFREQ}/min_freq", 1e-6)
    gov  = _sysfs(f"{_GPU_DEVFREQ}/governor")
    avail_raw = _sysfs(f"{_GPU_DEVFREQ}/available_frequencies")
    avail = []
    if avail_raw:
        avail = sorted(set(round(int(x) * 1e-6) for x in avail_raw.split()))

    gpu: dict = {}
    if cur  is not None: gpu["freq_mhz"]       = cur
    if mx   is not None: gpu["freq_max_mhz"]   = mx
    if mn   is not None: gpu["freq_min_mhz"]   = mn
    if gov  is not None: gpu["governor"]        = gov
    if avail:            gpu["available_freqs"] = avail

    # Merge tegrastats live data (GPU util %, EMC)
    ts = tegrastats.get()
    for key in ("gpu_util_percent", "emc_util_percent", "emc_freq_mhz", "vic_util_percent"):
        if key in ts:
            gpu[key] = ts[key]

    return gpu


# ─── CPU (sysfs per-core frequency) ───────────────────────────────────────────

def collect_cpu_freqs_sysfs() -> list[dict]:
    cores = []
    base = Path("/sys/devices/system/cpu")
    for cpu_dir in sorted(base.glob("cpu[0-9]*")):
        freq_dir = cpu_dir / "cpufreq"
        cur  = _sysfs_int(freq_dir / "scaling_cur_freq", 1e-3)   # kHz → MHz
        mx   = _sysfs_int(freq_dir / "scaling_max_freq", 1e-3)
        mn   = _sysfs_int(freq_dir / "scaling_min_freq", 1e-3)
        gov  = _sysfs(freq_dir / "scaling_governor")
        entry: dict = {"core": int(cpu_dir.name[3:])}
        if cur is not None: entry["freq_mhz"]     = cur
        if mx  is not None: entry["freq_max_mhz"] = mx
        if mn  is not None: entry["freq_min_mhz"] = mn
        if gov is not None: entry["governor"]      = gov
        cores.append(entry)

    # Overlay util % from tegrastats if available
    ts_cores = tegrastats.get().get("cpu_cores", [])
    for i, ts_core in enumerate(ts_cores):
        if i < len(cores):
            cores[i]["util_percent"] = ts_core.get("util_percent", 0)
            cores[i]["active"] = ts_core.get("active", True)

    return cores


# ─── Power  (INA3221 via hwmon1) ──────────────────────────────────────────────

def collect_power_ina3221() -> dict:
    hwmon = Path("/sys/class/hwmon/hwmon1")
    if not hwmon.exists():
        return {}

    rails: dict = {}
    total_mw = 0.0
    for ch in range(1, 4):
        label   = _sysfs(hwmon / f"in{ch}_label")
        curr_ma = _sysfs_int(hwmon / f"curr{ch}_input")   # mA
        volt_mv = _sysfs_int(hwmon / f"in{ch}_input")     # mV
        if label and curr_ma is not None and volt_mv is not None:
            mw = round(curr_ma * volt_mv / 1000, 1)
            rails[label] = {
                "current_ma": curr_ma,
                "voltage_mv": volt_mv,
                "power_mw":   mw,
            }
            total_mw += mw

    return {"rails": rails, "total_mw": round(total_mw, 1)} if rails else {}


# ─── Fan (hwmon0 = pwmfan, hwmon2 = pwm_tach) ─────────────────────────────────

def collect_fan() -> dict:
    fan: dict = {}
    for hwmon_name, hwmon_path in [("pwmfan", "/sys/class/hwmon/hwmon0"),
                                    ("pwm_tach", "/sys/class/hwmon/hwmon2")]:
        base = Path(hwmon_path)
        if not base.exists():
            continue
        for f in sorted(base.glob("fan*_input")):
            rpm = _sysfs_int(f)
            if rpm is not None:
                fan[f"{hwmon_name}/{f.name}"] = {"rpm": rpm}
        for f in sorted(base.glob("pwm*")):
            pwm = _sysfs_int(f)
            if pwm is not None:
                fan[f"{hwmon_name}/{f.name}"] = {"pwm": pwm}
    return fan


# ─── Thermal zones ────────────────────────────────────────────────────────────

def collect_thermal_zones() -> dict[str, float]:
    temps: dict[str, float] = {}
    base = Path("/sys/devices/virtual/thermal")
    if base.exists():
        for zone in sorted(base.glob("thermal_zone*")):
            raw_temp = _sysfs(zone / "temp")
            raw_type = _sysfs(zone / "type")
            if raw_temp and raw_type:
                try:
                    temps[raw_type] = round(int(raw_temp) / 1000.0, 1)
                except (ValueError, TypeError):
                    pass
    # Supplement with tegrastats temps
    for k, v in tegrastats.get().get("tegra_temps", {}).items():
        temps.setdefault(f"tegrastats/{k}", v)
    return temps


# ─── Disk (sysfs I/O stats + psutil usage) ────────────────────────────────────

# Sector size is 512 bytes on all these devices
_SECTOR = 512
# Stat field indices in /sys/block/*/stat
# reads_completed, reads_merged, sectors_read, ms_reading,
# writes_completed, writes_merged, sectors_written, ms_writing,
# ios_in_progress, ms_doing_io, ms_weighted, ...
_STAT_IDX = {
    "reads_completed": 0, "sectors_read": 2,
    "writes_completed": 4, "sectors_written": 6,
    "ios_in_progress": 8,
}

def _parse_block_stat(dev: str) -> dict:
    raw = _sysfs(f"/sys/block/{dev}/stat")
    if not raw:
        return {}
    parts = raw.split()
    out: dict = {}
    for name, idx in _STAT_IDX.items():
        try:
            out[name] = int(parts[idx])
        except (IndexError, ValueError):
            pass
    out["bytes_read"]    = out.get("sectors_read",    0) * _SECTOR
    out["bytes_written"] = out.get("sectors_written", 0) * _SECTOR
    return out


def _nvme_info(dev: str) -> dict:
    """Model name and size for an NVMe device."""
    info: dict = {}
    model = _sysfs(f"/sys/class/nvme/{dev}/model")
    if model:
        info["model"] = model.strip()
    size_sectors = _sysfs_int(f"/sys/block/{dev}n1/size")
    if size_sectors is not None:
        info["size_gb"] = round(size_sectors * _SECTOR / 1e9, 1)
    return info


def collect_disks() -> dict:
    disks: dict = {}

    # eMMC (system drive — mmcblk0p1 is mounted at /)
    blk = "mmcblk0"
    stat = _parse_block_stat(blk)
    size_sectors = _sysfs_int(f"/sys/block/{blk}/size")
    entry: dict = {
        "type": "emmc",
        "device": f"/dev/{blk}",
        "size_gb": round(size_sectors * _SECTOR / 1e9, 1) if size_sectors else None,
        "io": stat,
    }
    try:
        u = psutil.disk_usage("/")
        entry["usage"] = {"total": u.total, "used": u.used, "free": u.free, "percent": u.percent}
    except Exception:
        pass
    disks["emmc"] = entry

    # NVMe drives
    for nvme_dev in sorted(Path("/sys/class/nvme").glob("nvme*")):
        name = nvme_dev.name          # nvme0 / nvme1
        blk_dev = f"{name}n1"
        stat = _parse_block_stat(blk_dev)
        info = _nvme_info(name)
        entry = {
            "type": "nvme",
            "device": f"/dev/{blk_dev}",
            **info,
            "io": stat,
        }
        # Try to find usage for its main partition
        try:
            part_dev = f"/dev/{blk_dev}p1"
            # Check if any mountpoint uses this device
            for dp in psutil.disk_partitions():
                if dp.device == part_dev or dp.device.startswith(f"/dev/{blk_dev}"):
                    u = psutil.disk_usage(dp.mountpoint)
                    entry["mountpoint"] = dp.mountpoint
                    entry["usage"] = {"total": u.total, "used": u.used,
                                      "free": u.free, "percent": u.percent}
                    break
        except Exception:
            pass
        disks[name] = entry

    return disks


# ─── Network (host namespace via /proc/1/net/dev) ─────────────────────────────

def collect_net_ifaces() -> dict:
    ifaces: dict = {}
    try:
        lines = Path("/proc/1/net/dev").read_text().splitlines()[2:]
        for line in lines:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            ifaces[iface] = {
                "bytes_recv":    int(parts[1]),
                "packets_recv":  int(parts[2]),
                "errin":         int(parts[3]),
                "dropin":        int(parts[4]),
                "bytes_sent":    int(parts[9]),
                "packets_sent":  int(parts[10]),
                "errout":        int(parts[11]),
                "dropout":       int(parts[12]),
            }
    except Exception:
        for iface, s in psutil.net_io_counters(pernic=True).items():
            ifaces[iface] = {
                "bytes_sent": s.bytes_sent, "bytes_recv": s.bytes_recv,
                "packets_sent": s.packets_sent, "packets_recv": s.packets_recv,
                "errin": s.errin, "errout": s.errout,
            }
    return ifaces


# ─── Main board metrics ───────────────────────────────────────────────────────

def collect_board_metrics() -> dict:
    mem  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    freq = psutil.cpu_freq()
    ts   = tegrastats.get()

    return {
        # ── CPU ───────────────────────────────────────────────────────────────
        "cpu": {
            "util_percent":          round(psutil.cpu_percent(), 1),
            "util_per_core":         [round(p, 1) for p in psutil.cpu_percent(percpu=True)],
            "count_logical":         psutil.cpu_count(logical=True),
            "count_physical":        psutil.cpu_count(logical=False),
            "freq_mhz":              round(freq.current, 0) if freq else None,
            "freq_max_mhz":          round(freq.max, 0) if freq else None,
            "load_avg":              [round(x, 2) for x in psutil.getloadavg()],
            "cores":                 collect_cpu_freqs_sysfs(),
        },

        # ── GPU (Ampere, 1024 CUDA cores, 32 Tensor cores) ───────────────────
        "gpu": collect_gpu_sysfs(),

        # ── RAM (unified memory shared with GPU) ──────────────────────────────
        "memory": {
            "total":      mem.total,
            "available":  mem.available,
            "used":       mem.used,
            "percent":    mem.percent,
            "buffers":    getattr(mem, "buffers", 0),
            "cached":     getattr(mem, "cached", 0),
            # tegrastats unified-memory view
            "tegra_used_mb":  ts.get("tegra_ram_used_mb"),
            "tegra_total_mb": ts.get("tegra_ram_total_mb"),
            "tegra_lfb_blocks": ts.get("tegra_ram_lfb_blocks"),  # largest free block count
            "tegra_lfb_mb":     ts.get("tegra_ram_lfb_mb"),      # largest free block size
        },

        # ── Swap (zram) ───────────────────────────────────────────────────────
        "swap": {
            "total":   swap.total,
            "used":    swap.used,
            "free":    swap.free,
            "percent": swap.percent,
        },

        # ── Disk (eMMC + NVMe0 + NVMe1) ──────────────────────────────────────
        "disk": collect_disks(),

        # ── Network ───────────────────────────────────────────────────────────
        "net": collect_net_ifaces(),

        # ── Power (INA3221) ───────────────────────────────────────────────────
        "power": collect_power_ina3221(),

        # ── Temperatures ──────────────────────────────────────────────────────
        "temperatures": collect_thermal_zones(),

        # ── Fan ───────────────────────────────────────────────────────────────
        "fan": collect_fan(),

        # ── System ────────────────────────────────────────────────────────────
        "uptime_seconds": round(time.time() - psutil.boot_time()),
        "boot_time":      psutil.boot_time(),

        # ── tegrastats availability flag ──────────────────────────────────────
        "tegrastats_available": tegrastats.available,
    }


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
        "id":            c.short_id,
        "name":          c.name,
        "status":        c.status,
        "image":         c.image.tags[0] if c.image.tags else c.attrs.get("Image", "")[:20],
        "created":       c.attrs["Created"],
        "health":        ((c.attrs.get("State", {}).get("Health") or {}).get("Status", "none")),
        "restart_count": c.attrs.get("RestartCount", 0),
        "ports":         c.attrs.get("NetworkSettings", {}).get("Ports", {}),
        "cpu_percent":   0.0,
        "memory_usage":  0,
        "memory_limit":  0,
        "memory_percent":0.0,
        "net_rx_bytes":  0,
        "net_tx_bytes":  0,
        "block_read_bytes":  0,
        "block_write_bytes": 0,
        "logs": [],
    }

    if c.status != "running":
        return info

    try:
        stats = c.stats(stream=False)
        info["cpu_percent"] = _cpu_percent_from_stats(stats)

        mem  = stats.get("memory_stats", {})
        usage = mem.get("usage", 0)
        cache = (mem.get("stats") or {}).get("cache", 0)
        info["memory_usage"]   = max(usage - cache, 0)
        info["memory_limit"]   = mem.get("limit", 0)
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
                info["block_read_bytes"]  += bio.get("value", 0)
            elif op == "write":
                info["block_write_bytes"] += bio.get("value", 0)
    except Exception as e:
        info["stats_error"] = str(e)

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


# ─── WebSocket broadcast ───────────────────────────────────────────────────────

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
    psutil.cpu_percent()
    psutil.cpu_percent(percpu=True)

    while True:
        t0 = time.monotonic()

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
            "timestamp":  time.time(),
            "board":      board,
            "containers": containers,
        })

        if connected_clients:
            await _broadcast(latest_metrics)

        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, 1.0 - elapsed))


@app.on_event("startup")
async def _startup() -> None:
    tegrastats.start()
    asyncio.create_task(_metrics_loop())


# ─── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "timestamp": time.time(),
        "clients": len(connected_clients),
        "tegrastats": tegrastats.available,
    }


@app.get("/api/metrics")
def api_metrics() -> dict:
    return latest_metrics or {"error": "not yet collected — wait 1s"}


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
    if latest_metrics:
        await ws.send_json(latest_metrics)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
