#!/usr/bin/env bash
# WhyNotHost installer — deploy on any Linux machine with systemd + Docker.
#
#   sudo ./install.sh
#
# What it does:
#   1. Checks prerequisites (python3, docker; installs docker if missing on Debian/Ubuntu/Fedora/Arch)
#   2. Creates /opt/whynothost with the app files
#   3. Builds the frontend (or uses the prebuilt dist)
#   4. Sets up a Python venv + deps
#   5. Installs a hardened systemd unit and starts it
#   6. Prints the URL + first-run credentials
#
# Flags:
#   --port N        dashboard port (default 8022)
#   --dir PATH      install directory (default /opt/whynothost)
#   --domain SUFFIX default app domain suffix (default home.arpa)
set -euo pipefail

PORT="${WNH_PORT:-8022}"
INSTALL_DIR="${WNH_DIR:-/opt/whynothost}"
DOMAIN_SUFFIX="${WNH_DOMAIN_SUFFIX:-home.arpa}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --dir) INSTALL_DIR="$2"; shift 2 ;;
    --domain) DOMAIN_SUFFIX="$2"; shift 2 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "→ run with sudo (systemd install requires root)"; exit 1
fi

echo "━━ WhyNotHost installer ━━"

# ---------- prerequisites ----------
command -v python3 >/dev/null || { echo "✖ python3 required"; exit 1; }

if ! command -v docker >/dev/null; then
  echo "→ Docker not found. Installing…"
  if command -v apt-get >/dev/null; then
    curl -fsSL https://get.docker.com | sh
  elif command -v dnf >/dev/null; then
    dnf install -y docker && systemctl enable --now docker
  elif command -v pacman >/dev/null; then
    pacman -Sy --noconfirm docker && systemctl enable --now docker
  else
    echo "✖ install Docker manually, then re-run"; exit 1
  fi
fi
systemctl is-active --quiet docker || systemctl enable --now docker || true

# ---------- copy app ----------
echo "→ installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r backend catalog README.md "$INSTALL_DIR/" 2>/dev/null || true
if [[ -d frontend/dist/ui ]]; then
  mkdir -p "$INSTALL_DIR/frontend/dist"
  cp -r frontend/dist/ui "$INSTALL_DIR/frontend/dist/"
elif [[ -d frontend ]]; then
  echo "→ no prebuilt frontend found; building…"
  command -v npm >/dev/null || { echo "✖ npm required to build frontend (or ship dist/)"; exit 1; }
  cp -r frontend "$INSTALL_DIR/frontend"
  (cd "$INSTALL_DIR/frontend" && npm install --no-audit --no-fund && npm run build)
fi

# ---------- python env ----------
echo "→ setting up Python environment"
python3 -m venv "$INSTALL_DIR/backend/.venv"
"$INSTALL_DIR/backend/.venv/bin/pip" install -q -r "$INSTALL_DIR/backend/requirements.txt"

# ---------- env file ----------
ENV_FILE="$INSTALL_DIR/whynothost.env"
cat > "$ENV_FILE" <<EOF
WNH_PORT=$PORT
WNH_DOMAIN_SUFFIX=$DOMAIN_SUFFIX
WNH_SECRET_KEY=$(head -c 24 /dev/urandom | base64)
WNH_DATA_DIR=$INSTALL_DIR/backend/data
EOF
chmod 600 "$ENV_FILE"

# ---------- systemd service ----------
echo "→ installing systemd service"
cat > /etc/systemd/system/whynothost.service <<EOF
[Unit]
Description=WhyNotHost — one-click self-hosted app platform
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=$ENV_FILE
ExecStart=$INSTALL_DIR/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=on-failure
RestartSec=3
# hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$INSTALL_DIR
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now whynothost

sleep 2
if curl -fs -o /dev/null "http://127.0.0.1:$PORT/api/docs"; then
  echo ""
  echo "✔ WhyNotHost is running!"
  echo "  Dashboard : http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo localhost):$PORT/"
  echo "  Login     : admin / whynothost   (change it in Users)"
  echo "  Data      : $INSTALL_DIR/backend/data"
  echo ""
  echo "  HTTPS     : open the dashboard → System → 'Enable HTTPS'"
  echo "              (public domains get real Let's Encrypt certs;"
  echo "               *.home.arpa style names use self-signed TLS)"
else
  echo "✖ service did not come up — check: journalctl -u whynothost -e"
  exit 1
fi