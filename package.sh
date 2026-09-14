#!/usr/bin/env bash
# Build a self-contained release tarball: whynothost-<ver>.tar.gz
# The tarball contains everything install.sh needs (no npm required at target).
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-$(date +%Y%m%d)}"
NAME="whynothost-${VERSION}"
STAGING="$(mktemp -d)/$NAME"

# frontend must be prebuilt
if [[ ! -f frontend/dist/ui/index.html ]]; then
  echo "building frontend…"
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

mkdir -p "$STAGING"
cp -r backend "$STAGING/backend"
rm -rf "$STAGING/backend/.venv" "$STAGING/backend/data" "$STAGING/backend/.pytest_cache"
# prebuilt frontend ships inside backend/ in the layout install.sh expects
mkdir -p "$STAGING/frontend"
cp -r frontend/dist "$STAGING/frontend/dist"
cp install.sh README.md Dockerfile docker-compose.yml "$STAGING/"

tar -czf "$NAME.tar.gz" -C "$(dirname "$STAGING")" "$(basename "$STAGING")"
echo "✔ built $NAME.tar.gz ($(du -h "$NAME.tar.gz" | cut -f1))"
echo "  deploy anywhere:  tar xzf $NAME.tar.gz && cd $NAME && sudo ./install.sh"