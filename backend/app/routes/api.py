from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .. import apps, backups, catalog, edge, events, proxy, store
from ..engine.driver import registry
from ..engine import compose_render
from .auth_routes import require_auth

router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


# ---------- catalog ----------

@router.get("/catalog")
def get_catalog(q: str | None = None, category: str | None = None):
    return {"apps": catalog.list_apps(category=category, q=q), "categories": catalog.categories()}


@router.get("/catalog/{app_id}")
def get_catalog_app(app_id: str):
    a = catalog.get_app(app_id)
    if not a:
        raise HTTPException(404, "unknown app")
    return a


# ---------- installed apps ----------

@router.get("/apps")
def list_apps():
    return apps.list_installed()


@router.get("/apps/{app_id}")
def get_app(app_id: str):
    a = apps.get_installed(app_id)
    if not a:
        raise HTTPException(404, "not installed")
    return a


@router.post("/apps/{app_id}/install")
def install_app(app_id: str, body: dict):
    res = apps.install(app_id, body.get("config") or {})
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "install failed"))
    return res


@router.post("/apps/{app_id}/{action}")
def app_action(app_id: str, action: str):
    if action not in ("start", "stop", "restart", "update", "uninstall"):
        raise HTTPException(400, "bad action")
    res = getattr(apps, action)(app_id)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "action failed"))
    return res


@router.post("/apps/{app_id}/backup/create")
def backup_app(app_id: str):
    try:
        return backups.create_backup(app_id)
    except backups.BackupError as e:
        raise HTTPException(400, str(e))


@router.get("/apps/{app_id}/logs")
def app_logs(app_id: str, tail: int = 200):
    a = apps.get_installed(app_id)
    if not a:
        raise HTTPException(404, "not installed")
    d = registry.driver()
    return {"logs": d.logs(app_id, str(compose_render.stack_dir(app_id)), tail=min(tail, 2000))}


@router.get("/apps/{app_id}/job")
def app_job(app_id: str):
    return apps.get_job(app_id) or {"running": False}


@router.get("/apps/{app_id}/backups")
def list_app_backups(app_id: str):
    return backups.list_backups(app_id)


@router.post("/apps/{app_id}/backups/{filename}/restore")
def restore_app_backup(app_id: str, filename: str):
    try:
        return backups.restore_backup(app_id, filename)
    except backups.BackupError as e:
        raise HTTPException(400, str(e))


@router.delete("/apps/{app_id}/backups/{filename}")
def delete_app_backup(app_id: str, filename: str):
    try:
        return backups.delete_backup(app_id, filename)
    except backups.BackupError as e:
        raise HTTPException(400, str(e))


# ---------- system ----------

@router.get("/system")
def system_info():
    caps = registry.capabilities()
    stats = registry.driver().system_stats()
    with store.db() as conn:
        installed = conn.execute("SELECT COUNT(*) AS c FROM apps").fetchone()["c"]
        activity = [
            dict(r) for r in conn.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT 20"
            ).fetchall()
        ]
    return {
        "mode": caps["mode"],
        "override": caps["override"],
        "live_available": caps["live_available"],
        "docker_cli": caps["docker_cli"],
        "stats": stats,
        "installed_count": installed,
        "backup_bytes": backups.total_backup_size(),
        "activity": activity,
        "proxy": {"caddyfile": str(proxy.config.CADDY_CONFIG_PATH), "domain_suffix": proxy.DOMAIN_SUFFIX},
    }


@router.post("/system/mode")
def set_mode(body: dict):
    mode = body.get("mode")
    if mode not in ("auto", "live", "simulated"):
        raise HTTPException(400, "mode must be auto|live|simulated")
    registry.set_mode(None if mode == "auto" else mode)
    return registry.capabilities()


@router.get("/system/proxy")
def get_proxy():
    return {"caddyfile": proxy.generate_caddyfile()}


@router.post("/system/proxy/write")
def write_proxy():
    path = proxy.write_caddyfile()
    return {"ok": True, "path": path}


# ---------- edge proxy (HTTPS / Let's Encrypt) ----------

@router.get("/system/edge")
def edge_status():
    return edge.status()


@router.post("/system/edge/enable")
def edge_enable():
    try:
        return edge.enable()
    except edge.EdgeError as e:
        raise HTTPException(400, str(e))


@router.post("/system/edge/disable")
def edge_disable():
    try:
        return edge.disable()
    except edge.EdgeError as e:
        raise HTTPException(400, str(e))


@router.post("/system/edge/reload")
def edge_reload():
    res = edge.reload()
    if not res.get("ok") and res.get("error"):
        raise HTTPException(400, res["error"])
    return res


# ---------- SSE events ----------

@router.get("/events")
def sse():
    q = events.subscribe()
    return StreamingResponse(
        events.event_stream(q),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/compose-preview/{app_id}")
def compose_preview(app_id: str, config_json: str = "{}"):
    import json as _json
    manifest = catalog.get_app(app_id)
    if not manifest:
        raise HTTPException(404, "unknown app")
    try:
        cfg = _json.loads(config_json)
        merged = compose_render.validate_config(manifest, cfg)
        return {"compose": compose_render.render_compose(manifest, merged)}
    except (compose_render.RenderError, ValueError) as e:
        raise HTTPException(400, str(e))