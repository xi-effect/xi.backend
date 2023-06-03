"""user-themes

Revision ID: c82cbbf360d4
Revises: 666a1198f0a7
Create Date: 2023-06-03 23:57:00.810415

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c82cbbf360d4'
down_revision = '666a1198f0a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('theme', sa.String(length=10), nullable=False, server_default="system"))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('theme')
