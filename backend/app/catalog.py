import json
from functools import lru_cache
from pathlib import Path

from .config import CATALOG_DIR


class CatalogError(Exception):
    pass


def _manifests() -> list[Path]:
    d = CATALOG_DIR / "apps"
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))


@lru_cache(maxsize=1)
def _cache() -> dict:
    apps = {}
    for p in _manifests():
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise CatalogError(f"invalid manifest {p.name}: {e}")
        for required in ("id", "name", "category", "image", "compose"):
            if required not in data:
                raise CatalogError(f"{p.name}: missing '{required}'")
        apps[data["id"]] = data
    return {"apps": apps, "loaded": len(apps)}


def invalidate():
    _cache.cache_clear()


def list_apps(category: str | None = None, q: str | None = None) -> list[dict]:
    apps = list(_cache()["apps"].values())
    if category and category != "all":
        apps = [a for a in apps if a["category"] == category]
    if q:
        ql = q.lower()
        apps = [a for a in apps if ql in a["name"].lower() or ql in a.get("description", "").lower()]
    return sorted(apps, key=lambda a: a["name"].lower())


def get_app(app_id: str) -> dict | None:
    return _cache()["apps"].get(app_id)


def categories() -> list[str]:
    return sorted({a["category"] for a in _cache()["apps"].values()})