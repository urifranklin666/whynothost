import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("WNH_DATA_DIR", BASE_DIR / "data"))
CATALOG_DIR = Path(os.environ.get("WNH_CATALOG_DIR", BASE_DIR / "catalog"))
STACKS_DIR = DATA_DIR / "stacks"
BACKUPS_DIR = DATA_DIR / "backups"

for d in (DATA_DIR, STACKS_DIR, BACKUPS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "whynothost.db"
SECRET_KEY = os.environ.get("WNH_SECRET_KEY", "dev-secret-change-me")
SESSION_TTL_SECONDS = int(os.environ.get("WNH_SESSION_TTL", 60 * 60 * 24 * 7))
CADDY_CONFIG_PATH = DATA_DIR / "Caddyfile"
DOMAIN_SUFFIX = os.environ.get("WNH_DOMAIN_SUFFIX", "home.arpa")
DEMO_FALLBACK = os.environ.get("WNH_DEMO_FALLBACK", "1") == "1"

# dashboard port as seen from the host (edge proxy targets this)
WNH_PORT = int(os.environ.get("WNH_PORT", "8022"))
# directory containing the built frontend (index.html) to serve at /ui/
WNH_UI_DIR = Path(os.environ.get("WNH_UI_DIR", BASE_DIR.parent / "frontend" / "dist" / "ui"))

# managed edge proxy (Caddy) state lives here
EDGE_DIR = DATA_DIR / "edge"