"""Compose file rendering from catalog templates with user config substitution."""
import json
import re
from pathlib import Path

from .. import config


class RenderError(Exception):
    pass


def render_compose(manifest: dict, app_config: dict) -> str:
    """Render the manifest's compose template. Substitutes ${{cfg.key}} from
    app_config, ${{app.id}} and ${{app.name}}. Raises RenderError on unresolved
    or unknown placeholders so bad stacks never reach disk."""
    tpl = manifest["compose"]
    params = {"app.id": manifest["id"], "app.name": manifest["name"]}
    params.update({f"cfg.{k}": _stringify(v) for k, v in app_config.items()})

    def sub(m):
        key = m.group(1).strip()
        if key not in params:
            raise RenderError(f"unknown placeholder {{{{{key}}}}} in compose template")
        return params[key]

    out = re.sub(r"\$\{\{([^}]+)\}\}", sub, tpl)
    return out


def _stringify(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v)


def default_config(manifest: dict) -> dict:
    out = {}
    for p in manifest.get("config", []):
        out[p["key"]] = p.get("default")
    return out


def validate_config(manifest: dict, app_config: dict) -> dict:
    known = {p["key"] for p in manifest.get("config", [])}
    extra = set(app_config) - known
    if extra:
        raise RenderError(f"unknown config keys: {sorted(extra)}")
    merged = default_config(manifest)
    # an empty user value means "use default" except when the default is empty too
    merged.update({
        k: v for k, v in app_config.items()
        if v not in (None, "") or merged.get(k) in (None, "")
    })
    for p in manifest.get("config", []):
        if p.get("required") and merged.get(p["key"]) in (None, ""):
            raise RenderError(f"missing required config: {p['key']}")
    return merged


def persist_stack(app_id: str, compose_text: str) -> None:
    d = config.STACKS_DIR / app_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "compose.yaml").write_text(compose_text)


def stack_dir(app_id: str) -> Path:
    return config.STACKS_DIR / Path(app_id).name