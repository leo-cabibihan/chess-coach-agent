#!/usr/bin/env bash
# Bootstrap a Hetzner (or any Ubuntu) VM as a Cursor "My Machines" worker.
# Run as root on a fresh Ubuntu 22.04/24.04 server.
set -euo pipefail

WORKER_NAME="${WORKER_NAME:-cursor-devbox}"
WORKER_USER="${WORKER_USER:-ubuntu}"
REPO_URL="${REPO_URL:-https://github.com/leo-cabibihan/chess-coach-agent.git}"
REPO_DIR="${REPO_DIR:-/home/${WORKER_USER}/chess-coach-agent}"
INSTALL_TAILSCALE="${INSTALL_TAILSCALE:-false}"

log() { printf '[bootstrap] %s\n' "$*"; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

log "Updating packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

log "Installing base tools..."
apt-get install -y -qq \
  build-essential \
  ca-certificates \
  curl \
  git \
  jq \
  tmux \
  unzip \
  docker.io \
  docker-compose-v2

systemctl enable --now docker
usermod -aG docker "$WORKER_USER" || true

log "Installing Cursor agent CLI for ${WORKER_USER}..."
sudo -u "$WORKER_USER" bash -lc 'curl https://cursor.com/install -fsS | bash'
AGENT_BIN="/home/${WORKER_USER}/.local/bin/agent"
if [[ ! -x "$AGENT_BIN" ]]; then
  echo "Cursor agent CLI not found at ${AGENT_BIN}" >&2
  exit 1
fi

log "Cloning repo (if missing)..."
sudo -u "$WORKER_USER" bash -lc "
  if [[ ! -d '${REPO_DIR}/.git' ]]; then
    git clone '${REPO_URL}' '${REPO_DIR}'
  fi
"

if [[ "$INSTALL_TAILSCALE" == "true" ]]; then
  log "Installing Tailscale (optional remote access without public SSH)..."
  curl -fsSL https://tailscale.com/install.sh | sh
  log "Run: tailscale up   (as root) and approve the device in Tailscale admin."
fi

log "Writing systemd unit for Cursor worker..."
cat > /etc/systemd/system/cursor-worker.service <<EOF
[Unit]
Description=Cursor My Machines worker (${WORKER_NAME})
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${WORKER_USER}
WorkingDirectory=${REPO_DIR}
Environment=PATH=/home/${WORKER_USER}/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=HOME=/home/${WORKER_USER}
ExecStart=${AGENT_BIN} worker start --name ${WORKER_NAME} --worker-dir ${REPO_DIR}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cursor-worker.service

log "Bootstrap complete."
cat <<EOF

Next steps (required — cannot be automated from a cloud agent):

1. Sign in to Cursor on this VM as YOUR account:
     sudo -u ${WORKER_USER} -H bash -lc 'agent login'

2. Start the worker:
     sudo systemctl start cursor-worker.service

3. Check status:
     sudo systemctl status cursor-worker.service
     sudo -u ${WORKER_USER} -H bash -lc 'agent worker debug'

4. On desktop Cursor: Settings → Agents → enable Remote Control (if using handoff).

5. On iPhone: start a cloud agent → pick worker "${WORKER_NAME}" under My Machines.

Firewall: worker only needs OUTBOUND HTTPS to api2.cursor.sh and S3 artifacts.
No inbound ports required for Cursor.

EOF
