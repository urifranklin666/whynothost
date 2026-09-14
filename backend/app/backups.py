"""One-click backups: tar.gz of a stack's data dir; restore overwrites in place."""
import tarfile
import time

from . import store, config


class BackupError(Exception):
    pass


def list_backups(app_id: str) -> list[dict]:
    d = config.BACKUPS_DIR / app_id
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.tar.gz")):
        out.append({
            "file": p.name,
            "size": p.stat().st_size,
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)),
        })
    return sorted(out, key=lambda b: b["created"], reverse=True)


def create_backup(app_id: str) -> dict:
    src = config.STACKS_DIR / app_id
    if not src.exists():
        raise BackupError(f"no stack dir for {app_id}")
    dest_dir = config.BACKUPS_DIR / app_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{app_id}-{stamp}.tar.gz"
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(src, arcname=app_id)
    store.log_activity("backup", f"Backup created for {app_id}", app_id)
    return {"ok": True, "file": dest.name, "size": dest.stat().st_size}


def restore_backup(app_id: str, filename: str) -> dict:
    if "/" in filename or ".." in filename or not filename.endswith(".tar.gz"):
        raise BackupError("bad filename")
    src = config.BACKUPS_DIR / app_id / filename
    if not src.exists():
        raise BackupError("backup not found")
    target_parent = config.STACKS_DIR
    with tarfile.open(src, "r:gz") as tar:
        # defend against path traversal
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in m.name:
                raise BackupError("unsafe path in backup")
        tar.extractall(target_parent, filter="data")
    store.log_activity("backup", f"Restored {filename} for {app_id}", app_id)
    return {"ok": True}


def delete_backup(app_id: str, filename: str) -> dict:
    if "/" in filename or ".." in filename or not filename.endswith(".tar.gz"):
        raise BackupError("bad filename")
    p = config.BACKUPS_DIR / app_id / filename
    if p.exists():
        p.unlink()
    return {"ok": True}


def total_backup_size() -> int:
    total = 0
    if config.BACKUPS_DIR.exists():
        for p in config.BACKUPS_DIR.rglob("*.tar.gz"):
            total += p.stat().st_size
    return total