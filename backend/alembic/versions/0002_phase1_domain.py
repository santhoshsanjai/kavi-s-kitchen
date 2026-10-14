"""phase 1 domain: settings, subscriptions, slots, one-time orders, tasks, trips, payouts, ledger, audit

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14 15:53:41.573220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('audit_logs',
    sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('entity_type', sa.String(length=60), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_table('delivery_trips',
    sa.Column('driver_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('meal_window', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_window', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('status', sa.Enum('PLANNED', 'STARTED', 'ENDED', name='trip_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_reason', sa.Text(), nullable=True),
    sa.Column('distance_status', sa.Enum('NOT_CALCULATED', 'CALCULATED', 'NEEDS_MANUAL_ENTRY', name='distance_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('include_return_leg', sa.Boolean(), nullable=True),
    sa.Column('payable_km', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('driver_id', 'service_date', 'meal_window')
    )
    op.create_table('payments',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('method', sa.Enum('CASH', 'UPI', 'BANK_TRANSFER', 'OTHER', name='payment_method', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reference', sa.String(length=120), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('recorded_by_id', sa.UUID(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=120), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_payments_positive'),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_payments_customer_id'), 'payments', ['customer_id'], unique=False)
    op.create_table('plan_rate_versions',
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('monthly_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('included_meals', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('plan_id', 'effective_from')
    )
    op.create_table('service_date_exceptions',
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('is_open', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.String(length=200), nullable=False),
    sa.Column('created_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('service_date')
    )
    op.create_table('settings_versions',
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('effective_from')
    )
    op.create_table('driver_day_summaries',
    sa.Column('driver_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('PROPOSED', 'FINALIZED', name='day_summary_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('settings_version_id', sa.UUID(), nullable=True),
    sa.Column('policy_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finalized_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['finalized_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['settings_version_id'], ['settings_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('driver_id', 'service_date')
    )
    op.create_table('one_time_orders',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('enquiry_id', sa.UUID(), nullable=True),
    sa.Column('source', sa.Enum('CUSTOMER', 'ADMIN', name='order_source', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('status', sa.Enum('REQUEST_PENDING', 'CONFIRMED', 'REJECTED', 'CANCELLED', name='one_time_order_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('delivery_address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('request_notes', sa.Text(), nullable=True),
    sa.Column('estimated_delivery_fee', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('discount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('confirmed_by_id', sa.UUID(), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=80), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['confirmed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['enquiry_id'], ['enquiries.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_one_time_orders_status'), 'one_time_orders', ['status'], unique=False)
    op.create_table('subscriptions',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('plan_rate_version_id', sa.UUID(), nullable=False),
    sa.Column('settings_version_id', sa.UUID(), nullable=True),
    sa.Column('service_month', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'CANCELLED', name='subscription_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('plan_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('included_meals', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('service_days', sa.Integer(), nullable=False),
    sa.Column('total_slots', sa.Integer(), nullable=False),
    sa.Column('per_meal_value', sa.Numeric(precision=18, scale=8), nullable=False),
    sa.Column('credited_skip_total', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('activated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('activated_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['activated_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['plan_id'], ['meal_plans.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['plan_rate_version_id'], ['plan_rate_versions.id'], ),
    sa.ForeignKeyConstraint(['settings_version_id'], ['settings_versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_subscriptions_customer_month_active', 'subscriptions', ['customer_id', 'service_month'], unique=True, postgresql_where=sa.text("status <> 'CANCELLED'"))
    op.create_table('driver_earning_lines',
    sa.Column('summary_id', sa.UUID(), nullable=False),
    sa.Column('trip_id', sa.UUID(), nullable=True),
    sa.Column('code', sa.Enum('PER_KM', 'FIXED_ALLOWANCE', 'PER_DROP', 'ADJUSTMENT', name='earning_code', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=False),
    sa.Column('rate', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['summary_id'], ['driver_day_summaries.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['trip_id'], ['delivery_trips.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_driver_earning_lines_summary_id'), 'driver_earning_lines', ['summary_id'], unique=False)
    op.create_table('one_time_order_lines',
    sa.Column('order_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('meal_window', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_window', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['one_time_orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payment_allocations',
    sa.Column('payment_id', sa.UUID(), nullable=False),
    sa.Column('subscription_id', sa.UUID(), nullable=True),
    sa.Column('order_id', sa.UUID(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('(subscription_id IS NULL) <> (order_id IS NULL)', name='ck_payment_allocations_one_target'),
    sa.CheckConstraint('amount > 0', name='ck_payment_allocations_positive'),
    sa.ForeignKeyConstraint(['order_id'], ['one_time_orders.id'], ),
    sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('subscription_meal_slots',
    sa.Column('subscription_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('meal_window', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_window', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('status', sa.Enum('SCHEDULED', 'SKIPPED', name='slot_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('skip_credit_eligible', sa.Boolean(), nullable=True),
    sa.Column('skip_reason', sa.Text(), nullable=True),
    sa.Column('skipped_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('skipped_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['skipped_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('subscription_id', 'service_date', 'meal_window')
    )
    op.create_index('ix_slots_date_window', 'subscription_meal_slots', ['service_date', 'meal_window'], unique=False)
    op.create_table('delivery_tasks',
    sa.Column('task_type', sa.Enum('SUBSCRIPTION', 'ONE_TIME', name='task_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('slot_id', sa.UUID(), nullable=True),
    sa.Column('order_line_id', sa.UUID(), nullable=True),
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('meal_window', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_window', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('delivery_address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ASSIGNED', 'REASSIGNMENT_NEEDED', 'ACCEPTED', 'EN_ROUTE', 'DELIVERED', 'FAILED', 'PARTIAL', 'CANCELLED', name='task_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('assigned_driver_id', sa.UUID(), nullable=True),
    sa.Column('trip_id', sa.UUID(), nullable=True),
    sa.Column('stop_sequence', sa.Integer(), nullable=True),
    sa.Column('delivery_note', sa.Text(), nullable=True),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.Column('delivered_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('missing_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_by_id', sa.UUID(), nullable=True),
    sa.Column('customer_delivery_charge', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(slot_id IS NULL) <> (order_line_id IS NULL)', name='ck_delivery_tasks_one_source'),
    sa.ForeignKeyConstraint(['assigned_driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['completed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['order_line_id'], ['one_time_order_lines.id'], ),
    sa.ForeignKeyConstraint(['slot_id'], ['subscription_meal_slots.id'], ),
    sa.ForeignKeyConstraint(['trip_id'], ['delivery_trips.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_delivery_tasks_date_window', 'delivery_tasks', ['service_date', 'meal_window'], unique=False)
    op.create_index('ix_delivery_tasks_driver_date', 'delivery_tasks', ['assigned_driver_id', 'service_date'], unique=False)
    op.create_index(op.f('ix_delivery_tasks_status'), 'delivery_tasks', ['status'], unique=False)
    op.create_index('uq_delivery_tasks_live_order_line', 'delivery_tasks', ['order_line_id'], unique=True, postgresql_where=sa.text("order_line_id IS NOT NULL AND status <> 'CANCELLED'"))
    op.create_index('uq_delivery_tasks_live_slot', 'delivery_tasks', ['slot_id'], unique=True, postgresql_where=sa.text("slot_id IS NOT NULL AND status <> 'CANCELLED'"))
    op.create_table('admin_alerts',
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('task_id', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['delivery_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_alerts_kind'), 'admin_alerts', ['kind'], unique=False)
    op.create_table('customer_ledger_entries',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('entry_type', sa.Enum('SUBSCRIPTION_CHARGE', 'ORDER_CHARGE', 'DELIVERY_FEE', 'SKIP_CREDIT', 'MANUAL_ADJUSTMENT', 'PAYMENT', name='ledger_entry_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('subscription_id', sa.UUID(), nullable=True),
    sa.Column('order_id', sa.UUID(), nullable=True),
    sa.Column('task_id', sa.UUID(), nullable=True),
    sa.Column('payment_id', sa.UUID(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.UUID(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=120), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['one_time_orders.id'], ),
    sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['delivery_tasks.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_customer_ledger_entries_customer_id'), 'customer_ledger_entries', ['customer_id'], unique=False)
    op.create_table('delivery_events',
    sa.Column('task_id', sa.UUID(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('from_status', sa.String(length=32), nullable=True),
    sa.Column('to_status', sa.String(length=32), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['delivery_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_events_task_id'), 'delivery_events', ['task_id'], unique=False)
    op.create_table('driver_assignments',
    sa.Column('task_id', sa.UUID(), nullable=False),
    sa.Column('driver_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('OFFERED', 'ACCEPTED', 'DECLINED', 'EXPIRED', 'REVOKED', name='assignment_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('offered_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decline_reason', sa.Text(), nullable=True),
    sa.Column('assigned_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['delivery_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_driver_assignments_expiry', 'driver_assignments', ['status', 'expires_at'], unique=False)
    op.create_index('uq_driver_assignments_open_per_task', 'driver_assignments', ['task_id'], unique=True, postgresql_where=sa.text("status IN ('OFFERED', 'ACCEPTED')"))
    op.create_table('route_legs',
    sa.Column('trip_id', sa.UUID(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('to_task_id', sa.UUID(), nullable=True),
    sa.Column('is_return', sa.Boolean(), nullable=False),
    sa.Column('distance_km', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('source', sa.Enum('GOOGLE_MAPS', 'MANUAL', name='distance_source', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('provider_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('entered_by_id', sa.UUID(), nullable=True),
    sa.Column('manual_reason', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['to_task_id'], ['delivery_tasks.id'], ),
    sa.ForeignKeyConstraint(['trip_id'], ['delivery_trips.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('trip_id', 'sequence')
    )
    op.add_column('users', sa.Column('driver_code', sa.String(length=10), nullable=True))
    op.create_unique_constraint('users_driver_code_key', 'users', ['driver_code'])



def downgrade() -> None:

    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint('users_driver_code_key', 'users', type_='unique')
    op.drop_column('users', 'driver_code')
    op.drop_table('route_legs')
    op.drop_index('uq_driver_assignments_open_per_task', table_name='driver_assignments', postgresql_where=sa.text("status IN ('OFFERED', 'ACCEPTED')"))
    op.drop_index('ix_driver_assignments_expiry', table_name='driver_assignments')
    op.drop_table('driver_assignments')
    op.drop_index(op.f('ix_delivery_events_task_id'), table_name='delivery_events')
    op.drop_table('delivery_events')
    op.drop_index(op.f('ix_customer_ledger_entries_customer_id'), table_name='customer_ledger_entries')
    op.drop_table('customer_ledger_entries')
    op.drop_index(op.f('ix_admin_alerts_kind'), table_name='admin_alerts')
    op.drop_table('admin_alerts')
    op.drop_index('uq_delivery_tasks_live_slot', table_name='delivery_tasks', postgresql_where=sa.text("slot_id IS NOT NULL AND status <> 'CANCELLED'"))
    op.drop_index('uq_delivery_tasks_live_order_line', table_name='delivery_tasks', postgresql_where=sa.text("order_line_id IS NOT NULL AND status <> 'CANCELLED'"))
    op.drop_index(op.f('ix_delivery_tasks_status'), table_name='delivery_tasks')
    op.drop_index('ix_delivery_tasks_driver_date', table_name='delivery_tasks')
    op.drop_index('ix_delivery_tasks_date_window', table_name='delivery_tasks')
    op.drop_table('delivery_tasks')
    op.drop_index('ix_slots_date_window', table_name='subscription_meal_slots')
    op.drop_table('subscription_meal_slots')
    op.drop_table('payment_allocations')
    op.drop_table('one_time_order_lines')
    op.drop_index(op.f('ix_driver_earning_lines_summary_id'), table_name='driver_earning_lines')
    op.drop_table('driver_earning_lines')
    op.drop_index('uq_subscriptions_customer_month_active', table_name='subscriptions', postgresql_where=sa.text("status <> 'CANCELLED'"))
    op.drop_table('subscriptions')
    op.drop_index(op.f('ix_one_time_orders_status'), table_name='one_time_orders')
    op.drop_table('one_time_orders')
    op.drop_table('driver_day_summaries')
    op.drop_table('settings_versions')
    op.drop_table('service_date_exceptions')
    op.drop_table('plan_rate_versions')
    op.drop_index(op.f('ix_payments_customer_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_table('delivery_trips')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_table('audit_logs')

