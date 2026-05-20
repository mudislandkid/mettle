"""analysis_completed_at

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_column("completed_at")
