"""menus, food items, inbox

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15 01:18:12.183783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('food_items',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('diet_label', sa.Enum('VEG', 'NON_VEG', 'EGG', name='diet_label', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('image_url', sa.Text(), nullable=True),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('inbox_items',
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inbox_items_customer_id'), 'inbox_items', ['customer_id'], unique=False)
    op.create_index(op.f('ix_inbox_items_user_id'), 'inbox_items', ['user_id'], unique=False)
    op.create_table('weekly_menus',
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', name='menu_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('published_version', sa.Integer(), nullable=False),
    sa.Column('published_entries', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_by_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['published_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('week_start')
    )
    op.create_table('menu_entries',
    sa.Column('menu_id', sa.UUID(), nullable=False),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('meal_window', sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='meal_window', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('food_item_id', sa.UUID(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['food_item_id'], ['food_items.id'], ),
    sa.ForeignKeyConstraint(['menu_id'], ['weekly_menus.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('menu_id', 'service_date', 'meal_window', 'food_item_id')
    )



def downgrade() -> None:

    op.drop_table('menu_entries')
    op.drop_table('weekly_menus')
    op.drop_index(op.f('ix_inbox_items_user_id'), table_name='inbox_items')
    op.drop_index(op.f('ix_inbox_items_customer_id'), table_name='inbox_items')
    op.drop_table('inbox_items')
    op.drop_table('food_items')

