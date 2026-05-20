"""scanner_columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("secrets_found", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("secrets_detail", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("license_spdx", sa.String(), nullable=True))
        batch_op.create_index("ix_projects_license_spdx", ["license_spdx"])


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_license_spdx")
        batch_op.drop_column("license_spdx")
        batch_op.drop_column("secrets_detail")
        batch_op.drop_column("secrets_found")
