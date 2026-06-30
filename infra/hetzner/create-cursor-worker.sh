#!/usr/bin/env bash
# Create a Hetzner Cloud VM and bootstrap it as a Cursor My Machines worker.
# Run from your laptop or this environment — requires HCLOUD_TOKEN.
set -euo pipefail

SERVER_NAME="${SERVER_NAME:-cursor-worker}"
SERVER_TYPE="${SERVER_TYPE:-cx32}"
LOCATION="${LOCATION:-nbg1}"
IMAGE="${IMAGE:-ubuntu-24.04}"
SSH_KEY_NAME="${SSH_KEY_NAME:-}"
WORKER_NAME="${WORKER_NAME:-cursor-devbox}"
REPO_URL="${REPO_URL:-https://github.com/leo-cabibihan/workspace.git}"
INSTALL_TAILSCALE="${INSTALL_TAILSCALE:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_URL="${BOOTSTRAP_URL:-}"

if ! command -v hcloud >/dev/null 2>&1; then
  echo "hcloud CLI not found. Install: https://github.com/hetznercloud/cli" >&2
  exit 1
fi

if [[ -z "${HCLOUD_TOKEN:-}" ]]; then
  echo "Set HCLOUD_TOKEN to your Hetzner Cloud API token." >&2
  echo "Create one at: https://console.hetzner.cloud/ → Project → Security → API tokens" >&2
  exit 1
fi

if [[ -z "$SSH_KEY_NAME" ]]; then
  echo "Available SSH keys in this Hetzner project:"
  hcloud ssh-key list -o columns=id,name
  echo
  echo "Set SSH_KEY_NAME to one of the names above, e.g.:"
  echo "  export SSH_KEY_NAME=my-laptop"
  exit 1
fi

# cloud-init: download bootstrap script and run it
read -r -d '' USER_DATA <<EOF || true
#cloud-config
package_update: true
runcmd:
  - curl -fsSL -o /tmp/cursor-worker-bootstrap.sh "${BOOTSTRAP_URL:-file-will-be-inlined}"
  - chmod +x /tmp/cursor-worker-bootstrap.sh
  - WORKER_NAME=${WORKER_NAME} REPO_URL=${REPO_URL} INSTALL_TAILSCALE=${INSTALL_TAILSCALE} /tmp/cursor-worker-bootstrap.sh
EOF

# Inline bootstrap if no URL provided (embed script for reliability)
if [[ -z "$BOOTSTRAP_URL" ]]; then
  BOOTSTRAP_B64="$(base64 -w0 "${SCRIPT_DIR}/cursor-worker-bootstrap.sh")"
  USER_DATA="#cloud-config
write_files:
  - path: /tmp/cursor-worker-bootstrap.sh
    encoding: b64
    content: ${BOOTSTRAP_B64}
    permissions: '0755'
runcmd:
  - WORKER_NAME=${WORKER_NAME} REPO_URL=${REPO_URL} INSTALL_TAILSCALE=${INSTALL_TAILSCALE} /tmp/cursor-worker-bootstrap.sh
"
fi

TMP_USER_DATA="$(mktemp)"
printf '%s\n' "$USER_DATA" > "$TMP_USER_DATA"

log() { printf '[create] %s\n' "$*"; }

log "Creating server ${SERVER_NAME} (${SERVER_TYPE} @ ${LOCATION})..."
CREATE_OUT="$(hcloud server create \
  --name "$SERVER_NAME" \
  --type "$SERVER_TYPE" \
  --image "$IMAGE" \
  --location "$LOCATION" \
  --ssh-key "$SSH_KEY_NAME" \
  --user-data-from-file "$TMP_USER_DATA" \
  -o json)"

rm -f "$TMP_USER_DATA"

SERVER_IP="$(printf '%s' "$CREATE_OUT" | jq -r '.server.public_net.ipv4.ip')"
SERVER_ID="$(printf '%s' "$CREATE_OUT" | jq -r '.server.id')"

log "Server created: id=${SERVER_ID} ip=${SERVER_IP}"
log "Cloud-init bootstrap runs on first boot (~2-5 min)."
cat <<EOF

SSH in once cloud-init finishes:
  ssh root@${SERVER_IP}

Then complete Cursor auth (one-time):
  sudo -u ubuntu -H bash -lc 'agent login'
  systemctl start cursor-worker

Verify worker:
  systemctl status cursor-worker
  sudo -u ubuntu -H bash -lc 'agent worker debug'

Use from iPhone:
  Cursor app → new agent → My Machines → "${WORKER_NAME}"

EOF
