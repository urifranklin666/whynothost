from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import auth

router = APIRouter(prefix="/api/auth")


def current_user(request: Request) -> dict | None:
    token = request.cookies.get("wnh_session")
    return auth.resolve_session(token)


def require_auth(request: Request) -> dict:
    u = current_user(request)
    if not u:
        raise HTTPException(401, "not authenticated")
    return u


def require_admin(user: dict = Depends(require_auth)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "admin required")
    return user


@router.get("/me")
def me(user: dict = Depends(require_auth)):
    return {"username": user["username"], "role": user["role"]}


@router.post("/login")
def login(body: dict, response: Response):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    user = auth.authenticate(username, password)
    if not user:
        raise HTTPException(401, "invalid credentials")
    token, expires = auth.create_session(user["id"])
    response.set_cookie(
        "wnh_session", token,
        httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7, path="/",
    )
    return {"username": user["username"], "role": user["role"]}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("wnh_session")
    if token:
        auth.destroy_session(token)
    response.delete_cookie("wnh_session", path="/")
    return {"ok": True}


@router.get("/users")
def list_users(user: dict = Depends(require_admin)):
    with auth.store.db() as conn:
        rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.post("/users")
def create_user(body: dict, user: dict = Depends(require_admin)):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role = body.get("role") or "user"
    if not username or len(password) < 8:
        raise HTTPException(400, "username required, password >= 8 chars")
    if role not in ("user", "admin"):
        raise HTTPException(400, "bad role")
    try:
        auth.create_user(username, password, role)
    except Exception:
        raise HTTPException(409, "username taken")
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise HTTPException(400, "cannot delete yourself")
    with auth.store.db() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return {"ok": True}