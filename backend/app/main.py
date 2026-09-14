"""WhyNotHost — one-click self-hosted app platform. FastAPI entrypoint."""
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth, events, store
from .routes import api, auth_routes

app = FastAPI(title="WhyNotHost", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.include_router(auth_routes.router, prefix="")
app.include_router(api.router, prefix="")


@app.on_event("startup")
def startup():
    store.init_db()
    auth.bootstrap_admin()
    auth.purge_expired_sessions()
    events.publish({"type": "startup"})


@app.get("/")
def index():
    return RedirectResponse("/ui/")


# SPA fallback: serve index.html for /ui/* paths not matched by static assets
@app.get("/ui/{path:path}")
async def ui_spa(path: str):
    from .config import BASE_DIR
    candidate = BASE_DIR.parent / "frontend" / "dist" / "ui" / path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(BASE_DIR.parent / "frontend" / "dist" / "ui" / "index.html")


# serve built frontend assets if present (frontend/dist/ui/assets)
from .config import BASE_DIR
_dist = BASE_DIR.parent / "frontend" / "dist" / "ui"
if _dist.exists():
    app.mount("/ui/assets", StaticFiles(directory=str(_dist / "assets")), name="ui-assets")


def serve(host="127.0.0.1", port=8022):
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    serve()