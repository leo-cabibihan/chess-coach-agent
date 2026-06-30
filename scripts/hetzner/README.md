# Hetzner + Cursor My Machines

Run Cursor cloud agents with **tool calls on your own VM** (full filesystem access), steered from desktop or **Cursor iOS**.

## What you need

| Item | Where |
|------|--------|
| Hetzner Cloud account | [console.hetzner.cloud](https://console.hetzner.cloud/) |
| API token | Project → Security → API tokens → Read & Write |
| SSH key in Hetzner | Security → SSH keys |
| Cursor Pro+ (cloud agents) | [cursor.com](https://cursor.com) |

## Quick start

### 1. Install hcloud (once)

```bash
curl -sSLO https://github.com/hetznercloud/cli/releases/latest/download/hcloud-linux-amd64.tar.gz
sudo tar -C /usr/local/bin --no-same-owner -xzf hcloud-linux-amd64.tar.gz hcloud
```

### 2. Create the worker VM

```bash
export HCLOUD_TOKEN="your-hetzner-api-token"
export SSH_KEY_NAME="your-ssh-key-name-in-hetzner"

bash scripts/hetzner/create-cursor-worker.sh
```

Defaults: `cx32` in `nbg1`, repo `chess-coach-agent`, worker name `cursor-devbox`.

### 3. One-time Cursor login on the VM

```bash
ssh root@<server-ip>
sudo -u ubuntu -H bash -lc 'agent login'
systemctl start cursor-worker
```

### 4. Use from phone

1. Open **Cursor iOS**
2. Start an agent on your repo
3. Choose **My Machines** → `cursor-devbox`

Or on desktop: enable **Settings → Agents → Remote Control**, then `/remote-control` in a session.

## Manual bootstrap (existing VM)

```bash
curl -fsSL https://raw.githubusercontent.com/leo-cabibihan/chess-coach-agent/main/scripts/hetzner/cursor-worker-bootstrap.sh | sudo bash
```

## Limits reminder

The VM gives **unrestricted tool access on your server**. **Composer 2.5 / API usage limits are still Cursor billing** — the VM does not increase your Composer pool.

## Outbound firewall

Allow HTTPS to:

- `api2.cursor.sh`, `api2direct.cursor.sh`
- `cloud-agent-artifacts.s3.us-east-1.amazonaws.com`

No inbound ports required for Cursor workers.
