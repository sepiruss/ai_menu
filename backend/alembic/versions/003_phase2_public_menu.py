"""Add QR codes, customers, sessions, and events tables for Phase 2

Revision ID: 003_phase2_public_menu
Revises: 002_add_refresh_tokens
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_phase2_public_menu'
down_revision = '002_add_refresh_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # QR Codes table
    op.create_table(
        'qr_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('token', name='uq_qr_codes_token'),
    )
    op.create_index('ix_qr_codes_restaurant_branch', 'qr_codes', ['restaurant_id', 'branch_id'])
    op.create_index('ix_qr_codes_token_active', 'qr_codes', ['token', 'is_active'])

    # Customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=True),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='fa'),
        sa.Column('preferences', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_customers_restaurant_active', 'customers', ['restaurant_id', 'is_active'])
    op.create_index('ix_customers_restaurant_external', 'customers', ['restaurant_id', 'external_id'])

    # Customer Sessions table
    op.create_table(
        'customer_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('session_token', sa.String(64), nullable=False),
        sa.Column('device_info', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('session_token', name='uq_customer_sessions_token'),
    )
    op.create_index('ix_customer_sessions_restaurant_branch', 'customer_sessions', ['restaurant_id', 'branch_id'])
    op.create_index('ix_customer_sessions_token_active', 'customer_sessions', ['session_token', 'is_active'])
    op.create_index('ix_customer_sessions_customer_active', 'customer_sessions', ['customer_id', 'is_active'])

    # Customer Events table
    op.create_table(
        'customer_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.Enum('MENU_VIEW', 'CATEGORY_VIEW', 'ITEM_VIEW', 'ITEM_SEARCH', name='customer_event_type'), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['customer_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_customer_events_restaurant_branch_created', 'customer_events', ['restaurant_id', 'branch_id', 'created_at'])
    op.create_index('ix_customer_events_session_created', 'customer_events', ['session_id', 'created_at'])
    op.create_index('ix_customer_events_type_created', 'customer_events', ['event_type', 'created_at'])
    op.create_index('ix_customer_events_item_created', 'customer_events', ['menu_item_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('customer_events')
    op.drop_table('customer_sessions')
    op.drop_table('customers')
    op.drop_table('qr_codes')
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS customer_event_type")