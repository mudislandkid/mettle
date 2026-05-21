"""dependency_licenses

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("dependency_licenses", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("dependency_license_summary", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "has_license_risk",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_index("ix_projects_has_license_risk", ["has_license_risk"])


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_has_license_risk")
        batch_op.drop_column("has_license_risk")
        batch_op.drop_column("dependency_license_summary")
        batch_op.drop_column("dependency_licenses")
