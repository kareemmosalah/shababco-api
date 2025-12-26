"""add_google_oauth_fields

Revision ID: a1b2c3d4e5f6
Revises: f8a9b2c3d4e5
Create Date: 2025-12-26 16:08:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f8a9b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    # Add google_id column
    op.add_column(
        "attendee",
        sa.Column("google_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True)
    )
    op.create_index(op.f("ix_attendee_google_id"), "attendee", ["google_id"], unique=True)
    
    # Make hashed_password nullable (for OAuth users who don't have passwords)
    op.alter_column("attendee", "hashed_password", nullable=True)


def downgrade():
    # Remove google_id
    op.drop_index(op.f("ix_attendee_google_id"), table_name="attendee")
    op.drop_column("attendee", "google_id")
    
    # Make hashed_password required again
    op.alter_column("attendee", "hashed_password", nullable=False)
