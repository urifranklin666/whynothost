"""Deployment driver interface. Two implementations: LiveDriver (docker compose)
and SimulatedDriver (state machine, no containers). Selected by daemon availability."""
import shutil
import subprocess
import threading
import time


class DeployError(Exception):
    pass


class BaseDriver:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def deploy(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def start(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def stop(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def restart(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def update(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def uninstall(self, app_id: str, project_dir: str, on_event) -> dict:
        raise NotImplementedError

    def status(self, app_id: str, project_dir: str) -> dict:
        raise NotImplementedError

    def logs(self, app_id: str, project_dir: str, tail: int = 200) -> str:
        raise NotImplementedError

    def system_stats(self) -> dict:
        raise NotImplementedError


def _run_compose(args: list[str], project_dir: str, on_event=None, timeout: int = 600) -> tuple[int, str]:
    compose_bin = shutil.which("docker") or "docker"
    cmd = [compose_bin, "compose", *args]
    proc = subprocess.run(
        cmd, cwd=project_dir, capture_output=True, text=True, timeout=timeout
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


class LiveDriver(BaseDriver):
    name = "live"

    def __init__(self):
        self._compose_ok = shutil.which("docker") is not None

    def available(self) -> bool:
        if not self._compose_ok:
            return False
        try:
            r = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=15
            )
            return r.returncode == 0
        except Exception:
            return False

    def _check(self, rc: int, out: str, action: str):
        if rc != 0:
            raise DeployError(f"docker compose {action} failed: {out[-2000:]}")

    def deploy(self, app_id, project_dir, on_event=None):
        on_event = on_event or (lambda e: None)
        on_event({"stage": "pull", "message": "Pulling images…"})
        rc, out = _run_compose(["pull", "--ignore-pull-failures"], project_dir)
        if rc != 0:
            on_event({"stage": "pull", "message": "Some images failed to pull, continuing…", "level": "warn"})
        on_event({"stage": "up", "message": "Starting services…"})
        rc, out = _run_compose(["up", "-d", "--remove-orphans"], project_dir, timeout=900)
        self._check(rc, out, "up")
        on_event({"stage": "done", "message": "Deployed"})
        return {"ok": True, "output": out[-2000:]}

    def start(self, app_id, project_dir, on_event=None):
        rc, out = _run_compose(["start"], project_dir)
        self._check(rc, out, "start")
        return {"ok": True, "output": out[-2000:]}

    def stop(self, app_id, project_dir, on_event=None):
        rc, out = _run_compose(["stop"], project_dir)
        self._check(rc, out, "stop")
        return {"ok": True, "output": out[-2000:]}

    def restart(self, app_id, project_dir, on_event=None):
        rc, out = _run_compose(["restart"], project_dir)
        self._check(rc, out, "restart")
        return {"ok": True, "output": out[-2000:]}

    def update(self, app_id, project_dir, on_event=None):
        on_event = on_event or (lambda e: None)
        on_event({"stage": "pull", "message": "Checking for new images…"})
        rc, out = _run_compose(["pull", "--ignore-pull-failures"], project_dir, timeout=900)
        on_event({"stage": "up", "message": "Recreating changed services…"})
        rc2, out2 = _run_compose(["up", "-d", "--remove-orphans"], project_dir, timeout=900)
        self._check(rc2, out2, "up")
        on_event({"stage": "done", "message": "Updated"})
        return {"ok": True, "output": (out + "\n" + out2)[-2000:]}

    def uninstall(self, app_id, project_dir, on_event=None):
        rc, out = _run_compose(["down", "--remove-orphans"], project_dir)
        if rc != 0:
            # stack may already be gone; not fatal
            pass
        return {"ok": True, "output": out[-2000:]}

    def status(self, app_id, project_dir) -> dict:
        rc, out = _run_compose(["ps", "--format", "json", "--all"], project_dir, timeout=30)
        if rc != 0:
            return {"running": False, "services": []}
        services = []
        try:
            import json as _json
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                # docker compose v2 may emit a JSON array or NDJSON
                if line.startswith("["):
                    services.extend(_json.loads(line))
                else:
                    services.append(_json.loads(line))
        except Exception:
            pass
        running = bool(services) and all(
            s.get("State") == "running" for s in services
        ) if services else False
        return {"running": running, "services": services}

    def logs(self, app_id, project_dir, tail=200):
        rc, out = _run_compose(["logs", "--tail", str(tail), "--no-color"], project_dir, timeout=60)
        return out if out else ""

    def system_stats(self) -> dict:
        import os
        # CPU/MEM via /proc, disk via shutil
        stats = {}
        try:
            with open("/proc/uptime") as f:
                stats["uptime_s"] = float(f.read().split()[0])
            load1, load5, load15 = os.getloadavg()
            ncpu = os.cpu_count() or 1
            stats["load"] = {"1m": load1, "5m": load5, "15m": load15, "cores": ncpu}
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    mem[k.strip()] = int(v.strip().split()[0])  # kB
            total = mem.get("MemTotal", 0) * 1024
            avail = mem.get("MemAvailable", 0) * 1024
            stats["memory"] = {
                "total": total,
                "used": total - avail,
                "available": avail,
                "percent": round((total - avail) / total * 100, 1) if total else 0,
            }
            import shutil as _sh
            du = _sh.disk_usage("/")
            stats["disk"] = {
                "total": du.total,
                "used": du.used,
                "free": du.free,
                "percent": round(du.used / du.total * 100, 1),
            }
        except Exception as e:
            stats["error"] = str(e)
        return stats


class SimulatedDriver(BaseDriver):
    """Full-fidelity state machine for demo mode. Per-app simulated health,
    log streams, and system stats — no containers involved."""
    name = "simulated"

    def __init__(self):
        self._state: dict[str, dict] = {}  # app_id -> {"running": bool, "started_at": float}
        self._lock = threading.Lock()
        self._t0 = time.time()

    def available(self) -> bool:
        return True

    def _st(self, app_id) -> dict:
        with self._lock:
            return self._state.setdefault(app_id, {"running": False, "started_at": None})

    def _transition(self, app_id, running: bool):
        with self._lock:
            st = self._state.setdefault(app_id, {"running": False, "started_at": None})
            st["running"] = running
            st["started_at"] = time.time() if running else None

    def _sim_logs(self, app_id: str, running: bool) -> str:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        if running:
            return "\n".join(
                f"[{now}] {app_id}: service healthy, listening on internal port"
                for _ in range(3)
            )
        return f"[{now}] {app_id}: stopped"

    def deploy(self, app_id, project_dir, on_event=None):
        on_event = on_event or (lambda e: None)
        for stage, msg in [("pull", "Simulating image pull…"), ("up", "Simulating service start…"), ("done", "Deployed (simulated)")]:
            on_event({"stage": stage, "message": msg})
            time.sleep(0.4)
        self._transition(app_id, True)
        return {"ok": True, "output": "simulated deploy ok"}

    def start(self, app_id, project_dir, on_event=None):
        self._transition(app_id, True)
        return {"ok": True, "output": "simulated start ok"}

    def stop(self, app_id, project_dir, on_event=None):
        self._transition(app_id, False)
        return {"ok": True, "output": "simulated stop ok"}

    def restart(self, app_id, project_dir, on_event=None):
        self._transition(app_id, False)
        time.sleep(0.2)
        self._transition(app_id, True)
        return {"ok": True, "output": "simulated restart ok"}

    def update(self, app_id, project_dir, on_event=None):
        on_event = on_event or (lambda e: None)
        on_event({"stage": "pull", "message": "Simulating update pull…"})
        time.sleep(0.4)
        self._transition(app_id, True)
        return {"ok": True, "output": "simulated update ok"}

    def uninstall(self, app_id, project_dir, on_event=None):
        with self._lock:
            self._state.pop(app_id, None)
        return {"ok": True, "output": "simulated uninstall ok"}

    def status(self, app_id, project_dir) -> dict:
        st = self._st(app_id)
        svc = {
            "Name": app_id,
            "State": "running" if st["running"] else "exited",
            "Health": "healthy" if st["running"] else "",
        }
        return {"running": st["running"], "services": [svc] if st["running"] else []}

    def logs(self, app_id, project_dir, tail=200):
        return self._sim_logs(app_id, self._st(app_id)["running"])

    def system_stats(self) -> dict:
        # plausible static-ish numbers with slight drift
        import random
        r = random.Random(int(time.time() // 5))
        mem_pct = 38 + r.randint(0, 6)
        total = 16 * 1024**3
        return {
            "uptime_s": time.time() - self._t0 + 3600 * 72,
            "load": {"1m": round(r.uniform(0.3, 1.4), 2), "5m": round(r.uniform(0.3, 1.2), 2), "15m": round(r.uniform(0.2, 1.0), 2), "cores": 8},
            "memory": {"total": total, "used": int(total * mem_pct / 100), "available": int(total * (100 - mem_pct) / 100), "percent": mem_pct},
            "disk": {"total": 952 * 1024**3, "used": int(952 * 1024**3 * 0.23), "free": int(952 * 1024**3 * 0.77), "percent": 23},
        }


class DriverRegistry:
    def __init__(self, fallback_to_simulated: bool = True):
        self.live = LiveDriver()
        self.simulated = SimulatedDriver()
        self._mode_override: str | None = None
        self._lock = threading.Lock()

    def set_mode(self, mode: str | None):
        """None = auto, 'live', 'simulated'."""
        self._mode_override = mode

    @property
    def mode(self) -> str:
        if self._mode_override == "simulated":
            return "simulated"
        if self._mode_override == "live":
            return "live"
        return "live" if self.live.available() else "simulated"

    def driver(self) -> BaseDriver:
        return self.live if self.mode == "live" else self.simulated

    def capabilities(self) -> dict:
        live_ok = self.live.available()
        return {
            "docker_cli": shutil.which("docker") is not None,
            "live_available": live_ok,
            "mode": self.mode,
            "override": self._mode_override,
        }


registry = DriverRegistry()