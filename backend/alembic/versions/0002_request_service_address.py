"""Add customer supplied service address to requests."""

import sqlalchemy as sa

from alembic import op

revision = "0002_request_service_address"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_requests", sa.Column("service_address", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("service_requests", "service_address")
