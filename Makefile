.PHONY: setup dev up down test lint format demo logs backend frontend

setup:
	python -m pip install -e "backend[dev]"
	cd frontend && npm ci

# Full stack with PostgreSQL, Redis, API, worker and web app.
dev:
	docker compose up --build

up:
	docker compose up --build -d

down:
	docker compose down

# Local development without Docker (SQLite database, no worker needed).
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && BACKEND_URL=http://localhost:8000 npm run dev

test:
	pytest backend/tests -q
	python scripts/run_evals.py

lint:
	ruff check backend/app backend/tests scripts
	cd frontend && npm run typecheck

format:
	ruff format backend/app backend/tests scripts

demo:
	python -m app.cli doctor

logs:
	docker compose logs -f backend worker frontend
