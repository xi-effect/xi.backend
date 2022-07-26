"""mub-setup

Revision ID: 28e18c527412
Revises: ab118d9db832
Create Date: 2022-07-27 02:13:22.472482

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '28e18c527412'
down_revision = 'ab118d9db832'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('blocked-mod-tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(length=36), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mub-moderators',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=100), nullable=False),
    sa.Column('superuser', sa.Boolean(), nullable=False),
    sa.Column('mode', sa.Enum('DARK', 'LIGHT', name='interfacemode'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('mub-permissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('mub-modperms',
    sa.Column('moderator_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['moderator_id'], ['mub-moderators.id'], ),
    sa.ForeignKeyConstraint(['permission_id'], ['mub-permissions.id'], ),
    sa.PrimaryKeyConstraint('moderator_id', 'permission_id')
    )
    op.drop_table('moderators')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('moderators',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('mub-modperms')
    op.drop_table('mub-permissions')
    op.drop_table('mub-moderators')
    op.drop_table('blocked-mod-tokens')
    # ### end Alembic commands ###
