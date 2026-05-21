"""markdown_columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("markdown_files", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("markdown_lines", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("markdown_lines")
        batch_op.drop_column("markdown_files")
