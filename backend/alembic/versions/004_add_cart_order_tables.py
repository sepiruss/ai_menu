"""Add cart and order tables for Phase 2

Revision ID: 004_add_cart_order_tables
Revises: 003_phase2_public_menu
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_cart_order_tables'
down_revision = '003_phase2_public_menu'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Carts table
    op.create_table(
        'carts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_session_id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_session_id'], ['customer_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_carts_session_active', 'carts', ['customer_session_id', 'is_active'])
    op.create_index('ix_carts_restaurant_branch', 'carts', ['restaurant_id', 'branch_id'])
    op.create_index('ix_carts_customer_session', 'carts', ['customer_session_id'], unique=True)

    # Cart Items table
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cart_id', sa.Integer(), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price_toman', sa.Numeric(15, 2), nullable=False),
        sa.Column('unit_price_rial', sa.Numeric(15, 2), nullable=False),
        sa.Column('selected_options', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('item_name_snapshot', sa.String(255), nullable=False),
        sa.Column('options_price_adjustment_toman', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('options_price_adjustment_rial', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_cart_items_cart_id', 'cart_items', ['cart_id'])
    op.create_index('ix_cart_items_menu_item_id', 'cart_items', ['menu_item_id'])

    # Orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_session_id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('order_number', sa.String(50), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'PREPARING', 'READY', 'SERVED', 'CANCELLED', name='order_status'), nullable=False, server_default='PENDING'),
        sa.Column('subtotal_toman', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('subtotal_rial', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('discount_toman', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('discount_rial', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('total_toman', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('total_rial', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='IRR'),
        sa.Column('customer_note', sa.String(1000), nullable=True),
        sa.Column('internal_note', sa.String(1000), nullable=True),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preparing_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('served_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_session_id'], ['customer_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_orders_session_status', 'orders', ['customer_session_id', 'status'])
    op.create_index('ix_orders_restaurant_branch_status', 'orders', ['restaurant_id', 'branch_id', 'status'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])
    op.create_index('ix_orders_idempotency_key', 'orders', ['idempotency_key'], unique=True)
    op.create_index('ix_orders_order_number', 'orders', ['order_number'], unique=True)

    # Order Items table
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('item_description', sa.String(1000), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price_toman', sa.Numeric(15, 2), nullable=False),
        sa.Column('unit_price_rial', sa.Numeric(15, 2), nullable=False),
        sa.Column('selected_options', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('options_price_adjustment_toman', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('options_price_adjustment_rial', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('subtotal_toman', sa.Numeric(15, 2), nullable=False),
        sa.Column('subtotal_rial', sa.Numeric(15, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_menu_item_id', 'order_items', ['menu_item_id'])


def downgrade() -> None:
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('cart_items')
    op.drop_table('carts')
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS order_status")