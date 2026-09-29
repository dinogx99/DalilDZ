# Deployment

## Docker Compose

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

The default stack contains PostgreSQL, Redis, FastAPI, a Celery worker and the Next.js frontend.

## Production notes

- replace the example PostgreSQL password;
- use an external secret manager where available;
- terminate TLS at a trusted reverse proxy;
- add authentication/authorization before exposing sensitive cases;
- restrict database and Redis to private networks;
- configure backups and retention;
- monitor disk use for database growth;
- keep dependency scanning enabled.

## OCR

The minimal image intentionally excludes PaddlePaddle. For a dedicated OCR worker, install the optional OCR requirements and a Paddle runtime appropriate to the host CPU/GPU, then set `OCR_PROVIDER=paddle`.

## Database migrations

The backend runs `alembic upgrade head` before API startup. Review migrations as part of normal release procedures.

## Scaling

The FastAPI service is stateless except for database access. Expensive analysis can be moved to additional Celery workers sharing PostgreSQL/Redis.
