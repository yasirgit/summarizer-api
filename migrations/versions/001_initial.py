"""Initial migration

Revision ID: 001
Revises:
Create Date: 2025-08-23 04:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("data_progress", sa.Float(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("processing_time", sa.Float(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique constraints
    op.create_unique_constraint("uq_documents_name", "documents", ["name"])
    op.create_unique_constraint("uq_documents_url", "documents", ["url"])

    # Create indexes
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")

    # Drop unique constraints
    op.drop_constraint("uq_documents_url", "documents", type_="unique")
    op.drop_constraint("uq_documents_name", "documents", type_="unique")

    # Drop table
    op.drop_table("documents")
