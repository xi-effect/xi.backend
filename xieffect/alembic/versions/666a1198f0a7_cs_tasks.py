"""cs-tasks

Revision ID: 666a1198f0a7
Revises: 975c513fbd34
Create Date: 2022-11-27 13:31:03.237724

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '666a1198f0a7'
down_revision = '975c513fbd34'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cs_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('community_id', sa.Integer(), nullable=False),
    sa.Column('page_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('updated', sa.DateTime(), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['community.id'], name=op.f('fk_cs_tasks_community_id_community')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_cs_tasks_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cs_tasks'))
    )
    op.create_table('cs_embeds',
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], name=op.f('fk_cs_embeds_file_id_files')),
    sa.ForeignKeyConstraint(['task_id'], ['cs_tasks.id'], name=op.f('fk_cs_embeds_task_id_cs_tasks')),
    sa.PrimaryKeyConstraint('task_id', 'file_id', name=op.f('pk_cs_embeds'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('cs_embeds')
    op.drop_table('cs_tasks')
    # ### end Alembic commands ###
