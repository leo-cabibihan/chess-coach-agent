"""add sync jobs

Revision ID: 6c2a9df0c41b
Revises: e08fff1a2721
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "6c2a9df0c41b"
down_revision: str | None = "e08fff1a2721"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("player_id", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_games", sa.Integer(), nullable=False),
        sa.Column("analyzed_games", sa.Integer(), nullable=False),
        sa.Column("skipped_games", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_jobs_player_id"), "sync_jobs", ["player_id"])
    op.create_index(op.f("ix_sync_jobs_status"), "sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_jobs_status"), table_name="sync_jobs")
    op.drop_index(op.f("ix_sync_jobs_player_id"), table_name="sync_jobs")
    op.drop_table("sync_jobs")
