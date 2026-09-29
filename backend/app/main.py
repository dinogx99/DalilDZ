from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import r
from app.core.db import init_db
from app.core.middleware import RateLimitMiddleware, SecurityAndCorrelationMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

app = FastAPI(
    title="DalilDZ",
    version="1.0.0",
    description=(
        "Open-source evidence and consistency engine for Algerian business verification. "
        "DalilDZ does not produce trust scores."
    ),
    lifespan=lifespan,
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityAndCorrelationMiddleware)
app.include_router(r)
