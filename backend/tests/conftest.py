import os

os.environ["DATABASE_URL"] = "sqlite:///./test_dalildz.db"
os.environ["OCR_PROVIDER"] = "none"
os.environ["AI_PROVIDER"] = "none"

import pytest

from app.core.db import Base, engine
import app.models.entities  # noqa: F401


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
