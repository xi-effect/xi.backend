"""fk-constraints

Revision ID: 928f100cf232
Revises: e999c40cedf1
Create Date: 2023-03-04 13:10:42.433680

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '928f100cf232'
down_revision = 'e999c40cedf1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('communities_users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_communities_users_id_users', type_='foreignkey')
        batch_op.drop_constraint('fk_communities_users_avatar_id_files', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_communities_users_id_users'), 'users', ['id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_communities_users_avatar_id_files'), 'files', ['avatar_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')

    with op.batch_alter_table('community_invites', schema=None) as batch_op:
        batch_op.drop_constraint('fk_community_invites_community_id_community', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_community_invites_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('community_lists', schema=None) as batch_op:
        batch_op.drop_constraint('fk_community_lists_user_id_communities_users', type_='foreignkey')
        batch_op.drop_constraint('fk_community_lists_community_id_community', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_community_lists_user_id_communities_users'), 'communities_users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_community_lists_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('community_participant', schema=None) as batch_op:
        batch_op.drop_constraint('fk_community_participant_community_id_community', type_='foreignkey')
        batch_op.drop_constraint('fk_community_participant_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_community_participant_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_community_participant_user_id_users'), 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_chat_messages', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_chat_messages_community_id_community', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_chat_messages_sender_id_users', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_chat_messages_sender_id_users'), 'users', ['sender_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
        batch_op.create_foreign_key(batch_op.f('fk_cs_chat_messages_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_chat_participants', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_chat_participants_community_id_community', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_chat_participants_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_chat_participants_user_id_users'), 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_cs_chat_participants_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_embeds', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_embeds_file_id_files', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_embeds_task_id_cs_tasks', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_embeds_task_id_cs_tasks'), 'cs_tasks', ['task_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_cs_embeds_file_id_files'), 'files', ['file_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_participant_roles', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_participant_roles_participant_id_community_participant', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_participant_roles_role_id_cs_roles', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_participant_roles_participant_id_community_participant'), 'community_participant', ['participant_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_cs_participant_roles_role_id_cs_roles'), 'cs_roles', ['role_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_posts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_posts_user_id_users', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_posts_community_id_community', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_posts_user_id_users'), 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_cs_posts_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_role_permissions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_role_permissions_role_id_cs_roles', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_role_permissions_role_id_cs_roles'), 'cs_roles', ['role_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_roles', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_roles_community_id_community', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_roles_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('cs_tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cs_tasks_community_id_community', type_='foreignkey')
        batch_op.drop_constraint('fk_cs_tasks_user_id_users', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_cs_tasks_user_id_users'), 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_cs_tasks_community_id_community'), 'community', ['community_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('feedback_images', schema=None) as batch_op:
        batch_op.drop_constraint('fk_feedback_images_feedback_id_feedbacks', type_='foreignkey')
        batch_op.drop_constraint('fk_feedback_images_file_id_files', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_feedback_images_file_id_files'), 'files', ['file_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_feedback_images_feedback_id_feedbacks'), 'feedbacks', ['feedback_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('feedbacks', schema=None) as batch_op:
        batch_op.drop_constraint('feedbacks.123', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_feedbacks_user_id_users'), 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.drop_constraint('fk_files_uploader_id_users', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_files_uploader_id_users'), 'users', ['uploader_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_invite_id_invites', type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_users_invite_id_invites'), 'invites', ['invite_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_users_invite_id_invites'), type_='foreignkey')
        batch_op.create_foreign_key('fk_users_invite_id_invites', 'invites', ['invite_id'], ['id'])

    with op.batch_alter_table('files', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_files_uploader_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_files_uploader_id_users', 'users', ['uploader_id'], ['id'])

    with op.batch_alter_table('feedbacks', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_feedbacks_user_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('feedbacks.123', 'users', ['user_id'], ['id'])

    with op.batch_alter_table('feedback_images', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_feedback_images_feedback_id_feedbacks'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_feedback_images_file_id_files'), type_='foreignkey')
        batch_op.create_foreign_key('fk_feedback_images_file_id_files', 'files', ['file_id'], ['id'])
        batch_op.create_foreign_key('fk_feedback_images_feedback_id_feedbacks', 'feedbacks', ['feedback_id'], ['id'])

    with op.batch_alter_table('cs_tasks', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_tasks_community_id_community'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_tasks_user_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_tasks_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.create_foreign_key('fk_cs_tasks_community_id_community', 'community', ['community_id'], ['id'])

    with op.batch_alter_table('cs_roles', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_roles_community_id_community'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_roles_community_id_community', 'community', ['community_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('cs_role_permissions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_role_permissions_role_id_cs_roles'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_role_permissions_role_id_cs_roles', 'cs_roles', ['role_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('cs_posts', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_posts_community_id_community'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_posts_user_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_posts_community_id_community', 'community', ['community_id'], ['id'])
        batch_op.create_foreign_key('fk_cs_posts_user_id_users', 'users', ['user_id'], ['id'])

    with op.batch_alter_table('cs_participant_roles', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_participant_roles_role_id_cs_roles'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_participant_roles_participant_id_community_participant'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_participant_roles_role_id_cs_roles', 'cs_roles', ['role_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_cs_participant_roles_participant_id_community_participant', 'community_participant', ['participant_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('cs_embeds', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_embeds_file_id_files'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_embeds_task_id_cs_tasks'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_embeds_task_id_cs_tasks', 'cs_tasks', ['task_id'], ['id'])
        batch_op.create_foreign_key('fk_cs_embeds_file_id_files', 'files', ['file_id'], ['id'])

    with op.batch_alter_table('cs_chat_participants', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_chat_participants_community_id_community'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_chat_participants_user_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_chat_participants_user_id_users', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_cs_chat_participants_community_id_community', 'community', ['community_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('cs_chat_messages', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cs_chat_messages_community_id_community'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_cs_chat_messages_sender_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_cs_chat_messages_sender_id_users', 'users', ['sender_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_cs_chat_messages_community_id_community', 'community', ['community_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('community_participant', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_community_participant_user_id_users'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_community_participant_community_id_community'), type_='foreignkey')
        batch_op.create_foreign_key('fk_community_participant_user_id_users', 'users', ['user_id'], ['id'])
        batch_op.create_foreign_key('fk_community_participant_community_id_community', 'community', ['community_id'], ['id'])

    with op.batch_alter_table('community_lists', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_community_lists_community_id_community'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_community_lists_user_id_communities_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_community_lists_community_id_community', 'community', ['community_id'], ['id'])
        batch_op.create_foreign_key('fk_community_lists_user_id_communities_users', 'communities_users', ['user_id'], ['id'])

    with op.batch_alter_table('community_invites', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_community_invites_community_id_community'), type_='foreignkey')
        batch_op.create_foreign_key('fk_community_invites_community_id_community', 'community', ['community_id'], ['id'])

    with op.batch_alter_table('communities_users', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_communities_users_avatar_id_files'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_communities_users_id_users'), type_='foreignkey')
        batch_op.create_foreign_key('fk_communities_users_avatar_id_files', 'files', ['avatar_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_communities_users_id_users', 'users', ['id'], ['id'])

    # ### end Alembic commands ###
