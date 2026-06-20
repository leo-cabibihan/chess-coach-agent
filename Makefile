.PHONY: install test eval score dev backend frontend build

install:
	cd backend && uv sync --extra dev
	cd frontend && npm install

test:
	cd backend && uv run pytest -q
	cd frontend && npm run build

eval:
	cd backend && uv run python -m chess_coach_agent.evaluation --dataset data/eval/critical_moments.jsonl

score:
	python3 scripts/score_project.py

backend:
	cd backend && uv run uvicorn chess_coach_agent.api:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals: make backend and make frontend"

build:
	cd frontend && npm run build
