setup:
	python -m pip install -e "backend[dev]"
	cd frontend && npm install

dev:
	docker compose up --build

up:
	docker compose up --build -d

down:
	docker compose down

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
