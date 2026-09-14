"""App lifecycle manager: install, start/stop/restart/update/uninstall, status.
Runs driver operations in worker threads; status persisted in DB."""
import json
import threading

from . import catalog, store
from .engine import compose_render
from .engine.driver import registry, DeployError

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _set_job(app_id: str, data: dict):
    with _jobs_lock:
        _jobs[app_id] = data


def get_job(app_id: str) -> dict | None:
    with _jobs_lock:
        return _jobs.get(app_id)


def _run_job(app_id: str, action: str, fn, on_event=None):
    def emit(e):
        if on_event:
            try:
                on_event(e)
            except Exception:
                pass
        with _jobs_lock:
            _jobs[app_id] = {"action": action, "stage": e.get("stage"), "message": e.get("message"), "running": True}

    def wrapper():
        try:
            result = fn(emit)
            _set_job(app_id, {"action": action, "stage": "done", "message": "ok", "running": False, "ok": result.get("ok", True), "output": result.get("output", "")})
        except DeployError as e:
            _set_job(app_id, {"action": action, "stage": "error", "message": str(e), "running": False, "ok": False})
        except Exception as e:
            _set_job(app_id, {"action": action, "stage": "error", "message": f"unexpected: {e}", "running": False, "ok": False})

    threading.Thread(target=wrapper, daemon=True, name=f"job-{action}-{app_id}").start()


def install(app_id: str, app_config: dict, on_event=None) -> dict:
    manifest = catalog.get_app(app_id)
    if not manifest:
        return {"ok": False, "error": f"unknown app: {app_id}"}
    try:
        merged = compose_render.validate_config(manifest, app_config)
        compose_text = compose_render.render_compose(manifest, merged)
    except compose_render.RenderError as e:
        return {"ok": False, "error": str(e)}
    compose_render.persist_stack(app_id, compose_text)
    with store.db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO apps (id, name, catalog_version, status, config) VALUES (?, ?, ?, ?, ?)",
            (app_id, manifest["name"], manifest.get("version", "0"), "installing", json.dumps(merged)),
        )
    store.log_activity("install", f"Installing {manifest['name']}", app_id)

    d = registry.driver()
    sdir = str(compose_render.stack_dir(app_id))

    def finalize(emit):
        res = d.deploy(app_id, sdir, emit)
        with store.db() as conn:
            conn.execute("UPDATE apps SET status = 'running' WHERE id = ?", (app_id,))
        store.log_activity("install", f"{manifest['name']} installed and started", app_id)
        return res

    _run_job(app_id, "install", finalize, on_event)
    return {"ok": True, "job": "install"}


def _lifecycle(app_id: str, action: str, on_event=None) -> dict:
    with store.db() as conn:
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
    if not row:
        return {"ok": False, "error": f"not installed: {app_id}"}
    d = registry.driver()
    sdir = str(compose_render.stack_dir(app_id))
    status_map = {"start": "running", "restart": "running", "stop": "stopped", "update": "running", "uninstall": None}

    def finalize(emit):
        fn = getattr(d, action)
        res = fn(app_id, sdir, emit)
        new_status = status_map[action]
        with store.db() as conn:
            if new_status is None:
                conn.execute("DELETE FROM apps WHERE id = ?", (app_id,))
                try:
                    compose_render.stack_dir(app_id).joinpath("compose.yaml").unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                conn.execute("UPDATE apps SET status = ? WHERE id = ?", (new_status, app_id))
        verbs = {"start": "started", "stop": "stopped", "restart": "restarted", "update": "updated", "uninstall": "uninstalled"}
        store.log_activity(action, f"{row['name']} {verbs[action]}", app_id)
        return res

    _run_job(app_id, action, finalize, on_event)
    return {"ok": True, "job": action}


def start(app_id, on_event=None):
    return _lifecycle(app_id, "start", on_event)


def stop(app_id, on_event=None):
    return _lifecycle(app_id, "stop", on_event)


def restart(app_id, on_event=None):
    return _lifecycle(app_id, "restart", on_event)


def update(app_id, on_event=None):
    return _lifecycle(app_id, "update", on_event)


def uninstall(app_id, on_event=None):
    return _lifecycle(app_id, "uninstall", on_event)


def list_installed() -> list[dict]:
    with store.db() as conn:
        rows = conn.execute("SELECT * FROM apps ORDER BY name").fetchall()
    d = registry.driver()
    out = []
    for r in rows:
        item = dict(r)
        item["config"] = json.loads(item.get("config") or "{}")
        try:
            st = d.status(item["id"], str(compose_render.stack_dir(item["id"])))
            item["runtime"] = st
            # reconcile DB status with reality
            live_status = "running" if st.get("running") else ("stopped" if st.get("services") else item["status"])
        except Exception:
            item["runtime"] = {"running": False, "services": []}
            live_status = item["status"]
        item["status"] = live_status
        out.append(item)
    return out


def get_installed(app_id: str) -> dict | None:
    items = [i for i in list_installed() if i["id"] == app_id]
    return items[0] if items else None