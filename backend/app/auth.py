import hashlib
import hmac
import secrets
import time

import argon2

from . import store

_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except argon2.exceptions.VerifyMismatchError:
        return False
    except argon2.exceptions.InvalidHashError:
        # legacy/plain hash fallback (first-run bootstrap)
        return hmac.compare_digest(password_hash, hashlib.sha256(password.encode()).hexdigest())


def _token() -> str:
    return secrets.token_urlsafe(32)


def create_user(username: str, password: str, role: str = "user") -> int:
    with store.db() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role),
        )
        return cur.lastrowid


def authenticate(username: str, password: str) -> dict | None:
    with store.db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row or not verify_password(row["password_hash"], password):
        return None
    return dict(row)


def create_session(user_id: int) -> tuple[str, float]:
    token = _token()
    from .config import SESSION_TTL_SECONDS
    expires = time.time() + SESSION_TTL_SECONDS
    with store.db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )
    return token, expires


def resolve_session(token: str) -> dict | None:
    if not token:
        return None
    with store.db() as conn:
        row = conn.execute(
            "SELECT u.id, u.username, u.role, s.expires_at FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    if not row or row["expires_at"] < time.time():
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def destroy_session(token: str):
    with store.db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def purge_expired_sessions():
    with store.db() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))


def bootstrap_admin():
    with store.db() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if count == 0:
            create_user("admin", "whynothost", role="admin")