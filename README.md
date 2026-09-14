# WhyNotHost 🐳

**Self-host anything, in one click.** A YunoHost-class app platform with a modern web dashboard, Docker Compose as the deploy engine, automatic HTTPS (Let's Encrypt), and a full demo mode when no Docker daemon is available.

## Deploy on any machine

**Option A — installer (systemd):**

```bash
tar xzf whynothost-<ver>.tar.gz && cd whynothost-<ver>
sudo ./install.sh                      # installs to /opt/whynothost, port 8022
sudo ./install.sh --port 9000 --dir /srv/whynothost   # custom
```

Creates a hardened systemd service (`whynothost.service`), a random secret key, and auto-installs Docker if missing. Data lives in `/opt/whynothost/backend/data`.

**Option B — Docker:**

```bash
docker compose up -d --build           # mounts docker.sock + /opt/whynothost dirs
```

**Build a release tarball yourself:** `make pack` (or `./package.sh <version>`) → `whynothost-<ver>.tar.gz` with the prebuilt frontend, backend, catalog and installer.

## Quick start (dev)

```bash
./run.sh                               # backend on :8022, serves built frontend
# or: make build && make run
```

Open **http://127.0.0.1:8022/** → dashboard at `/ui/`.
First-run credentials: **admin / whynothost** (change it in Users).

## HTTPS / Let's Encrypt

Open the dashboard → **System → HTTPS edge proxy → 🔒 Enable HTTPS**.

One managed Caddy stack (`wnh-edge`, host networking, ports 80/443) fronts the dashboard and every running app:

- **Public domains** (`app.example.com` — anything that isn't a reserved suffix) → automatic **Let's Encrypt** certificates, issued and renewed by Caddy's ACME client. Requires ports 80/443 reachable and the domain's DNS pointing at the host.
- **Local/reserved domains** (`*.home.arpa`, `*.local`, `*.lan`, `*.internal`, `*.localhost`, …) → self-signed certs via Caddy's `tls internal` — still HTTPS, just private-trust.

Certificates persist in `data/edge/caddy/data` across restarts. Config changes (new apps, changed domains) apply via **↻ Reload config** (zero-downtime `caddy reload`). API: `GET/POST /api/system/edge[/enable|/disable|/reload]`.

## Modes

- **Live mode** — real `docker compose` deployments (needs the Docker daemon reachable).
- **Demo mode** — full state-machine simulation, no containers; kicks in automatically when Docker is unreachable, or force it in *System → Deployment engine*.

## Features

- **App Store** — 15 curated apps (Nextcloud, Vaultwarden, Jellyfin, Gitea, n8n, Immich, Pi-hole, Home Assistant…), search, categories, live compose preview before install.
- **One-click deploy** — config modal → SSE progress stream → running app.
- **Lifecycle** — start / stop / restart / update / uninstall per app.
- **Logs** — live tailed container logs per app.
- **Backups** — one-click tar.gz per app, restore / delete.
- **Dashboard** — CPU/memory/disk charts (Recharts), app status, activity feed.
- **Reverse proxy** — auto-generated Caddyfile (`<app>.home.arpa`), one click to write.
- **Users** — admin creates accounts (argon2-hashed passwords, cookie sessions).
- **SSE events** — `/api/events` streams job progress live.

## Layout

```
backend/
  app/
    main.py             FastAPI entrypoint + static serving
    config.py           paths & settings (env-overridable)
    store.py            SQLite (users, sessions, apps, activity)
    auth.py             argon2 passwords, session cookies
    catalog.py          JSON app-catalog loader
    apps.py             install/lifecycle orchestration (background jobs)
    backups.py          tar.gz backup/restore
    proxy.py            Caddyfile generator (per-app, for external Caddy)
    edge.py             managed edge proxy: HTTPS, Let's Encrypt / tls internal
    events.py           SSE pub/sub
    engine/
      driver.py         LiveDriver (docker compose) + SimulatedDriver
      compose_render.py template rendering + validation
    routes/             auth + api routers
  catalog/apps/*.json   15 app manifests (compose templates)
  tests/                pytest suite (14 tests)
frontend/
  src/                  React (Vite + Bootstrap, dark glassmorphism theme)
  dist/ui/              production build (served by the backend)
```

Also at the repo root: `install.sh` (systemd installer), `Dockerfile` + `docker-compose.yml` (container deploy), `package.sh` (release tarball), `Makefile` (build/test/pack/run).

## Adding an app to the catalog

Drop a JSON file into `backend/catalog/apps/`:

```json
{
  "id": "myapp",
  "name": "My App",
  "tagline": "short line",
  "description": "longer text",
  "category": "media",
  "version": "1.0",
  "icon": "📦",
  "color": "#6c8cff",
  "featured": false,
  "image": "myorg/myapp:latest",
  "config": [
    {"key": "port", "label": "Port", "default": "8080", "type": "port", "required": true}
  ],
  "compose": "services:\n  myapp:\n    image: myorg/myapp:latest\n    ports:\n      - \"127.0.0.1:${{cfg.port}}:80\"\n"
}
```

Placeholders: `${{cfg.<key>}}` from the install form, `${{app.id}}`, `${{app.name}}`.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```