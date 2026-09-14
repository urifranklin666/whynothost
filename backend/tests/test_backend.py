import json
import time

import pytest
from fastapi.testclient import TestClient

from app import catalog, store
from app.engine import compose_render
from app.engine.driver import LiveDriver, SimulatedDriver, DriverRegistry
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WNH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WNH_CATALOG_DIR", str(tmp_path / "catalog"))
    import app.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data", raising=False)
    monkeypatch.setattr(cfg, "STACKS_DIR", tmp_path / "data" / "stacks", raising=False)
    monkeypatch.setattr(cfg, "BACKUPS_DIR", tmp_path / "data" / "backups", raising=False)
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "data" / "whynothost.db", raising=False)
    monkeypatch.setattr(cfg, "CADDY_CONFIG_PATH", tmp_path / "data" / "Caddyfile", raising=False)
    (tmp_path / "data" / "stacks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "backups").mkdir(parents=True, exist_ok=True)
    store.init_db()
    from app import auth as _auth
    _auth.bootstrap_admin()
    registry = DriverRegistry()
    registry.set_mode("simulated")
    import app.apps as apps_mod
    monkeypatch.setattr(apps_mod, "registry", registry)
    with TestClient(app) as c:
        # login
        r = c.post("/api/auth/login", json={"username": "admin", "password": "whynothost"})
        assert r.status_code == 200
        yield c


CATALOG_MANIFEST = {
    "id": "testapp",
    "name": "Test App",
    "category": "dev",
    "version": "1",
    "image": "nginx:alpine",
    "config": [
        {"key": "port", "label": "Port", "default": "8080", "type": "port", "required": True},
        {"key": "domain", "label": "Domain", "default": "test-app.home.arpa", "type": "domain"},
        {"key": "message", "label": "Message", "default": "hello", "type": "text"},
    ],
    "compose": 'services:\n  testapp:\n    image: nginx:alpine\n    ports:\n      - "127.0.0.1:${{cfg.port}}:80"\n    environment:\n      MSG: "${{cfg.message}}"\n',
}


@pytest.fixture()
def catalog_app(tmp_path, monkeypatch):
    # inject into catalog cache by pointing CATALOG_DIR at a temp catalog
    import app.config as cfg
    apps_dir = cfg.CATALOG_DIR / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    p = apps_dir / "testapp.json"
    p.write_text(json.dumps(CATALOG_MANIFEST))
    catalog.invalidate()
    yield CATALOG_MANIFEST
    p.unlink(missing_ok=True)
    catalog.invalidate()


def test_render_compose_substitution(catalog_app):
    text = compose_render.render_compose(CATALOG_MANIFEST, {"port": "9090", "message": "hi"})
    assert "127.0.0.1:9090:80" in text
    assert 'MSG: "hi"' in text


def test_render_rejects_unknown_placeholder(catalog_app):
    bad = dict(CATALOG_MANIFEST)
    bad["compose"] = "services:\n  x:\n    image: nginx\n    nope: ${{cfg.missing}}\n"
    with pytest.raises(compose_render.RenderError):
        compose_render.render_compose(bad, {})


def test_validate_config_fills_defaults_and_requires(catalog_app):
    merged = compose_render.validate_config(CATALOG_MANIFEST, {"port": "9999"})
    assert merged["message"] == "hello"  # default filled
    with pytest.raises(compose_render.RenderError):
        compose_render.validate_config(
            {**CATALOG_MANIFEST, "config": [
                {"key": "port", "label": "Port", "default": "", "type": "port", "required": True},
                {"key": "message", "label": "Message", "default": "hello", "type": "text"},
            ]},
            {},
        )  # required param with empty default and no user value must raise


def test_simulated_install_lifecycle(client, catalog_app):
    c = client
    r = c.post("/api/apps/testapp/install", json={"config": {"port": "8080"}})
    assert r.status_code == 200, r.text
    # wait for background job
    for _ in range(50):
        jobs = c.get("/api/apps/testapp/job").json()
        if not jobs.get("running"):
            break
        time.sleep(0.1)
    assert jobs.get("stage") == "done", jobs
    apps = c.get("/api/apps").json()
    assert len(apps) == 1
    assert apps[0]["status"] == "running"
    # stop/start
    assert c.post("/api/apps/testapp/stop").status_code == 200
    for _ in range(50):
        job = c.get("/api/apps/testapp/job").json()
        if job.get("running") is False and job.get("action") == "stop":
            break
        time.sleep(0.1)
    assert job.get("action") == "stop" and job.get("stage") == "done", job
    assert c.get("/api/apps").json()[0]["status"] == "stopped"
    assert c.post("/api/apps/testapp/start").status_code == 200
    for _ in range(50):
        job2 = c.get("/api/apps/testapp/job").json()
        if job2.get("running") is False and job2.get("action") == "start":
            break
        time.sleep(0.1)
    # logs
    logs = c.get("/api/apps/testapp/logs").json()["logs"]
    assert "testapp" in logs
    # uninstall
    assert c.post("/api/apps/testapp/uninstall").status_code == 200
    for _ in range(50):
        job3 = c.get("/api/apps/testapp/job").json()
        if job3.get("running") is False and job3.get("action") == "uninstall":
            break
        time.sleep(0.1)
    assert c.get("/api/apps").json() == []


def test_backup_create_restore(client, catalog_app):
    c = client
    r = c.post("/api/apps/testapp/install", json={"config": {"port": "8080"}})
    assert r.status_code == 200, r.text
    for _ in range(50):
        if not c.get("/api/apps/testapp/job").json().get("running"):
            break
        time.sleep(0.1)
    r = c.post("/api/apps/testapp/backup/create")
    assert r.status_code == 200, r.text
    lst = c.get("/api/apps/testapp/backups").json()
    assert len(lst) == 1
    fname = lst[0]["file"]
    # restore endpoint
    r = c.post(f"/api/apps/testapp/backups/{fname}/restore")
    assert r.status_code == 200, r.text
    # traversal rejected
    r = c.post("/api/apps/testapp/backups/..%2Fetc%2Fpasswd/restore")
    assert r.status_code in (400, 404)


def test_proxy_generation(client, catalog_app):
    c = client
    r = c.post("/api/apps/testapp/install", json={"config": {"port": "8080", "domain": "test.example.internal"}})
    assert r.status_code == 200, r.text
    for _ in range(50):
        if not c.get("/api/apps/testapp/job").json().get("running"):
            break
        time.sleep(0.1)
    apps_now = c.get("/api/apps").json()
    assert apps_now, f"testapp should be installed; job={c.get('/api/apps/testapp/job').json()}"
    if apps_now[0]["status"] != "running":
        c.post("/api/apps/testapp/start")
        for _ in range(50):
            if not c.get("/api/apps/testapp/job").json().get("running"):
                break
            time.sleep(0.1)
    text = c.get("/api/system/proxy").json()["caddyfile"]
    assert "test.example.internal" in text
    assert "reverse_proxy 127.0.0.1:8080" in text


def test_auth_flow(client):
    c = client
    me = c.get("/api/auth/me").json()
    assert me["username"] == "admin"
    assert me["role"] == "admin"
    # bad login
    import httpx
    r = c.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
    # unauth access
    fresh = TestClient(app)
    r = fresh.get("/api/apps")
    assert r.status_code == 401
    # user management
    r = c.post("/api/auth/users", json={"username": "bob", "password": "longenough1", "role": "user"})
    assert r.status_code == 200
    users = c.get("/api/auth/users").json()
    assert {u["username"] for u in users} >= {"admin", "bob"}


def test_system_endpoint(client, catalog_app):
    c = client
    c.post("/api/apps/testapp/install", json={"config": {"port": "8080"}})
    for _ in range(50):
        if not c.get("/api/apps/testapp/job").json().get("running"):
            break
        time.sleep(0.1)
    d = c.get("/api/system").json()
    assert d["mode"] == "simulated"
    assert "stats" in d and "memory" in d["stats"]
    assert d["installed_count"] == 1
    assert isinstance(d["activity"], list) and len(d["activity"]) >= 1


def test_live_driver_compose_ps_parse(tmp_path):
    # only validates the NDJSON parsing path with a fake ps output
    d = LiveDriver()
    import subprocess
    def fake_run(cmd, cwd, capture_output, text, timeout):
        class R:
            returncode = 0
            stdout = '{"Name":"a","State":"running"}\n{"Name":"b","State":"exited"}\n'
            stderr = ""
        return R()
    import app.engine.driver as drv
    orig = subprocess.run
    subprocess.run = fake_run
    try:
        st = d.status("x", str(tmp_path))
    finally:
        subprocess.run = orig
    assert st["running"] is False
    assert len(st["services"]) == 2


def test_simulated_driver_state_machine():
    s = SimulatedDriver()
    assert s.status("x", "/tmp")["running"] is False
    s.start("x", "/tmp")
    assert s.status("x", "/tmp")["running"] is True
    s.stop("x", "/tmp")
    assert s.status("x", "/tmp")["running"] is False
    s.restart("x", "/tmp")
    assert s.status("x", "/tmp")["running"] is True
    s.uninstall("x", "/tmp")
    assert s.status("x", "/tmp")["running"] is False


# ---------- edge proxy (HTTPS / Let's Encrypt) ----------

def test_edge_local_domain_detection():
    from app import edge
    assert edge.is_local_domain("cloud.home.arpa")
    assert edge.is_local_domain("foo.local")
    assert edge.is_local_domain("bar.lan")
    assert edge.is_local_domain("thing.internal")
    assert edge.is_local_domain("myhost.localhost")
    assert not edge.is_local_domain("cloud.example.com")
    assert not edge.is_local_domain("selfhosted.io")


def test_edge_caddyfile_tls_internal_vs_public(client, catalog_app):
    # two running apps: one local domain, one public domain
    from app import edge, store
    c = client
    with store.db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO apps (id, name, catalog_version, status, config) VALUES (?,?,?,?,?)",
            ("localapp", "Local App", "1", "running",
             json.dumps({"port": "8111", "domain": "local.home.arpa"})),
        )
        conn.execute(
            "INSERT OR REPLACE INTO apps (id, name, catalog_version, status, config) VALUES (?,?,?,?,?)",
            ("pubapp", "Public App", "1", "running",
             json.dumps({"port": "8112", "domain": "app.example.com"})),
        )
    text = edge.generate_caddyfile()
    assert "local.home.arpa {" in text
    assert "tls internal" in text
    assert "app.example.com {" in text
    # public domain block must NOT carry tls internal
    pub_block = text.split("app.example.com {")[1].split("}")[0]
    assert "tls internal" not in pub_block
    assert "reverse_proxy 127.0.0.1:8111" in text
    assert "reverse_proxy 127.0.0.1:8112" in text
    # cleanup
    with store.db() as conn:
        conn.execute("DELETE FROM apps WHERE id IN ('localapp', 'pubapp')")


def test_edge_write_files_and_status(client, catalog_app):
    from app import edge, config
    import os
    c = client
    c.post("/api/apps/testapp/install", json={"config": {"port": "8080"}})
    for _ in range(50):
        if not c.get("/api/apps/testapp/job").json().get("running"):
            break
        time.sleep(0.1)
    if c.get("/api/apps").json() and c.get("/api/apps").json()[0]["status"] != "running":
        c.post("/api/apps/testapp/start")
        for _ in range(50):
            if not c.get("/api/apps/testapp/job").json().get("running"):
                break
            time.sleep(0.1)
    files = edge.write_edge_files()
    assert os.path.exists(files["caddyfile"])
    assert os.path.exists(files["compose"])
    compose_text = open(files["compose"]).read()
    assert "caddy:2-alpine" in compose_text
    assert "network_mode: host" in compose_text
    cf = open(files["caddyfile"]).read()
    assert "test-app.home.arpa" in cf  # default slug domain
    st = c.get("/api/system/edge").json()
    assert st["supported"] is True
    assert "running" in st
    assert st["caddyfile"]
    # in simulated mode enable must be refused
    r = c.post("/api/system/edge/enable")
    assert r.status_code == 400
    assert "live mode" in r.json()["detail"]


def test_edge_slug_default_domain(client, catalog_app):
    from app import edge
    assert edge.slugify("Test App") == "test-app"
    assert edge.slugify("Uptime Kuma!") == "uptime-kuma"
    assert edge.slugify("###") == "app"