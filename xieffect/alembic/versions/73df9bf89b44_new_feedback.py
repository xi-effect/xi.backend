"""new-feedback

Revision ID: 73df9bf89b44
Revises: 4d0c909957c7
Create Date: 2022-11-07 04:40:37.253883

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73df9bf89b44'
down_revision = '4d0c909957c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('feedback_images',
    sa.Column('feedback_id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['feedback_id'], ['feedbacks.id'], name=op.f('fk_feedback_images_feedback_id_feedbacks')),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], name=op.f('fk_feedback_images_file_id_files')),
    sa.PrimaryKeyConstraint('feedback_id', 'file_id', name=op.f('pk_feedback_images'))
    )
    op.drop_table('feedback-images')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('feedback-images',
    sa.Column('id', sa.INTEGER(), server_default=sa.text('nextval(\'"feedback-images_id_seq"\'::regclass)'), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id', name='pk_feedback-images')
    )
    op.drop_table('feedback_images')
    # ### end Alembic commands ###
