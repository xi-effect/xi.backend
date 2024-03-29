"""cs-posts

Revision ID: 4d0c909957c7
Revises: 7ecc867e7b7c
Create Date: 2022-10-27 12:52:01.331064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d0c909957c7'
down_revision = '7ecc867e7b7c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cs_posts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('changed', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('community_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['community.id'], name=op.f('fk_cs_posts_community_id_community')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_cs_posts_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cs_posts'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('cs_posts')
    # ### end Alembic commands ###
