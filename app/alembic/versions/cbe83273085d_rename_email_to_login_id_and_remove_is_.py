"""rename email to login_id and remove is_active

Revision ID: cbe83273085d
Revises: 19ad5d84c3f7
Create Date: 2026-05-22 16:28:37.906121

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'cbe83273085d'
down_revision = '19ad5d84c3f7'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop the old index on email
    op.drop_index(op.f('ix_user_email'), table_name='user')
    # 2. Rename email column to login_id
    op.alter_column('user', 'email', new_column_name='login_id')
    # 3. Create the new index on login_id
    op.create_index(op.f('ix_user_login_id'), 'user', ['login_id'], unique=True)
    # 4. Drop is_active column
    op.drop_column('user', 'is_active')


def downgrade():
    # 1. Re-add is_active column
    op.add_column('user', sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), nullable=False))
    # 2. Drop the new index on login_id
    op.drop_index(op.f('ix_user_login_id'), table_name='user')
    # 3. Rename login_id column back to email
    op.alter_column('user', 'login_id', new_column_name='email')
    # 4. Re-create the index on email
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
