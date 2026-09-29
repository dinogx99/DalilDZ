up:
	docker compose up --build
down:
	docker compose down
test:
	cd backend && pytest -q
dev:
	docker compose up --build
