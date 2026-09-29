"""Initial DalilDZ evidence schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-29
"""

from alembic import op

from app.core.db import Base
import app.models.entities  # noqa: F401


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
