"""add_attendee_order_tables

Revision ID: f8a9b2c3d4e5
Revises: 1a31ce608336
Create Date: 2025-12-26 14:11:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f8a9b2c3d4e5"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade():
    # Create attendee table
    op.create_table(
        "attendee",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("shopify_customer_id", sa.BigInteger(), nullable=True),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("first_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("last_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("country", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attendee_email"), "attendee", ["email"], unique=True)
    op.create_index(op.f("ix_attendee_shopify_customer_id"), "attendee", ["shopify_customer_id"], unique=True)

    # Create order table
    op.create_table(
        "order",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("shopify_order_id", sa.BigInteger(), nullable=True),
        sa.Column("attendee_id", sa.String(36), nullable=False),
        sa.Column("order_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False, server_default="USD"),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["attendee_id"], ["attendee.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_shopify_order_id"), "order", ["shopify_order_id"], unique=True)
    op.create_index(op.f("ix_order_attendee_id"), "order", ["attendee_id"])

    # Create order_item table
    op.create_table(
        "order_item",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("shopify_variant_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=True),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("checked_in", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_item_order_id"), "order_item", ["order_id"])

    # Create processed_webhooks table for idempotency
    op.create_table(
        "processed_webhook",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("webhook_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("topic", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_processed_webhook_webhook_id"), "processed_webhook", ["webhook_id"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_processed_webhook_webhook_id"), table_name="processed_webhook")
    op.drop_table("processed_webhook")
    
    op.drop_index(op.f("ix_order_item_order_id"), table_name="order_item")
    op.drop_table("order_item")
    
    op.drop_index(op.f("ix_order_attendee_id"), table_name="order")
    op.drop_index(op.f("ix_order_shopify_order_id"), table_name="order")
    op.drop_table("order")
    
    op.drop_index(op.f("ix_attendee_shopify_customer_id"), table_name="attendee")
    op.drop_index(op.f("ix_attendee_email"), table_name="attendee")
    op.drop_table("attendee")
