# workspace

Personal monorepo for Cursor **My Machines**, mobile agents, apps, games, and infra.

Pick this **one repo** in Cursor iOS instead of choosing a project each time.

## Layout

```
workspace/
├── apps/
│   └── chess-coach-agent/   # Adaptive chess learning platform (Render deploy)
├── games/                   # Godot and other game projects
├── infra/
│   └── hetzner/             # Cursor worker + VPS bootstrap scripts
└── render.yaml                # Render Blueprint (chess-coach-agent)
```

## Cursor iOS

1. Start a **new agent** → select repo **`workspace`**
2. **My Machines** → `cursor-devbox` (after Hetzner worker is set up)
3. Or on Mac: **Remote Control** to continue the same session without re-picking the repo

## Hetzner worker

```bash
export HCLOUD_TOKEN="..."
export SSH_KEY_NAME="your-key"

bash infra/hetzner/create-cursor-worker.sh
```

Defaults clone `https://github.com/leo-cabibihan/workspace.git` to `/home/ubuntu/workspace`.

See [infra/hetzner/README.md](infra/hetzner/README.md).

## chess-coach-agent (app)

Live: https://chess-coach-agent.onrender.com/

```bash
cd apps/chess-coach-agent
docker compose up --build
```

See [apps/chess-coach-agent/README.md](apps/chess-coach-agent/README.md).

## Publish this repo to GitHub

If `leo-cabibihan/workspace` does not exist yet, create it on GitHub (empty, no README), then:

```bash
bash scripts/publish-workspace.sh
```
