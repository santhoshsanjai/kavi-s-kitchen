"""initial schema: users, customers, enquiries, meal plans, orders

Revision ID: 0001
Revises: 
Create Date: 2026-10-14 15:38:10.846111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('customers',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('alternate_phone', sa.String(length=20), nullable=True),
    sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
    sa.Column('customer_type', sa.Enum('INDIVIDUAL', 'FAMILY', 'OFFICE', 'OTHER', name='customer_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('meal_preference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone')
    )
    op.create_index(op.f('ix_customers_is_active'), 'customers', ['is_active'], unique=False)
    op.create_index(op.f('ix_customers_name'), 'customers', ['name'], unique=False)
    op.create_table('meal_plans',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('diet_type', sa.Enum('VEG', 'NON_VEG', 'EGG', 'CUSTOM', name='diet_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('meal_sessions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('billing_cycle', sa.String(length=20), nullable=False),
    sa.Column('service_days', sa.Integer(), nullable=False),
    sa.Column('delivery_eligible', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('full_name', sa.String(length=100), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('SUPER_ADMIN', 'ADMIN', 'DRIVER', name='user_role', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('driving_status', sa.String(length=20), nullable=False),
    sa.Column('vehicle_type', sa.String(length=50), nullable=True),
    sa.Column('vehicle_number', sa.String(length=30), nullable=True),
    sa.Column('last_latitude', sa.Float(), nullable=True),
    sa.Column('last_longitude', sa.Float(), nullable=True),
    sa.Column('last_location_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('phone'),
    sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_table('enquiries',
    sa.Column('customer_name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('enquiry_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('requested_meal', sa.String(length=100), nullable=True),
    sa.Column('requested_date', sa.String(length=20), nullable=True),
    sa.Column('number_of_persons', sa.Integer(), nullable=False),
    sa.Column('diet_type', sa.Enum('VEG', 'NON_VEG', 'EGG', 'CUSTOM', name='diet_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('subscription_type', sa.String(length=30), nullable=False),
    sa.Column('delivery_location', sa.Text(), nullable=False),
    sa.Column('quoted_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('follow_up_date', sa.String(length=20), nullable=True),
    sa.Column('assigned_admin', sa.String(length=100), nullable=True),
    sa.Column('status', sa.Enum('NEW', 'CONTACTED', 'QUOTED', 'FOLLOW_UP', 'CONFIRMED', 'REJECTED', 'CONVERTED', 'CLOSED', name='enquiry_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enquiries_phone'), 'enquiries', ['phone'], unique=False)
    op.create_index(op.f('ix_enquiries_status'), 'enquiries', ['status'], unique=False)
    op.create_table('orders',
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('customer_name', sa.String(length=100), nullable=False),
    sa.Column('customer_phone', sa.String(length=20), nullable=False),
    sa.Column('delivery_address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('meal_session', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_session', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('diet_type', sa.Enum('VEG', 'NON_VEG', 'EGG', 'CUSTOM', name='diet_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('order_type', sa.Enum('SUBSCRIPTION', 'AD_HOC', 'BULK', name='order_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('spice_level', sa.Enum('MILD', 'NORMAL', 'SPICY', name='spice_level', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('rice_preference', sa.String(length=100), nullable=True),
    sa.Column('special_notes', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PLANNED', 'CONFIRMED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'CANCELLED', 'SKIPPED', name='order_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('status_reason', sa.String(length=100), nullable=True),
    sa.Column('assigned_driver_id', sa.UUID(), nullable=True),
    sa.Column('assigned_driver_name', sa.String(length=100), nullable=True),
    sa.Column('sequence_number', sa.Integer(), nullable=True),
    sa.Column('delivery_notes', sa.Text(), nullable=True),
    sa.Column('recipient_name', sa.String(length=100), nullable=True),
    sa.Column('proof_photo_url', sa.Text(), nullable=True),
    sa.Column('delivery_charge', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('out_for_delivery_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_driver_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_orders_date_driver', 'orders', ['order_date', 'assigned_driver_id'], unique=False)
    op.create_index(op.f('ix_orders_order_date'), 'orders', ['order_date'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index('uq_orders_subscription_customer_date_session', 'orders', ['customer_id', 'order_date', 'meal_session'], unique=True, postgresql_where=sa.text("order_type = 'SUBSCRIPTION'"))



def downgrade() -> None:

    op.drop_index('uq_orders_subscription_customer_date_session', table_name='orders', postgresql_where=sa.text("order_type = 'SUBSCRIPTION'"))
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_order_date'), table_name='orders')
    op.drop_index('ix_orders_date_driver', table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_enquiries_status'), table_name='enquiries')
    op.drop_index(op.f('ix_enquiries_phone'), table_name='enquiries')
    op.drop_table('enquiries')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_table('users')
    op.drop_table('meal_plans')
    op.drop_index(op.f('ix_customers_name'), table_name='customers')
    op.drop_index(op.f('ix_customers_is_active'), table_name='customers')
    op.drop_table('customers')

