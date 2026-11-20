"""complete_flowstate_schema

Revision ID: 8d4b3a1e9c2f
Revises: 573e718b4c07
Create Date: 2026-11-17 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8d4b3a1e9c2f'
down_revision: Union[str, None] = '573e718b4c07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define PostgreSQL Enum types matching domain models
project_status_enum = postgresql.ENUM(
    'planning', 'in_progress', 'in_review', 'completed', 'on_hold',
    name='project_status',
    create_type=False,
)

priority_level_enum = postgresql.ENUM(
    'low', 'medium', 'high', 'urgent',
    name='priority_level',
    create_type=False,
)

task_status_enum = postgresql.ENUM(
    'backlog', 'todo', 'in_progress', 'in_review', 'done',
    name='task_status',
    create_type=False,
)

notification_type_enum = postgresql.ENUM(
    'assignment', 'deadline', 'mention', 'project_update', 'system',
    name='notification_type',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Create Enums if not exist
    sa.Enum('planning', 'in_progress', 'in_review', 'completed', 'on_hold', name='project_status').create(bind, checkfirst=True)
    sa.Enum('low', 'medium', 'high', 'urgent', name='priority_level').create(bind, checkfirst=True)
    sa.Enum('backlog', 'todo', 'in_progress', 'in_review', 'done', name='task_status').create(bind, checkfirst=True)
    sa.Enum('assignment', 'deadline', 'mention', 'project_update', 'system', name='notification_type').create(bind, checkfirst=True)

    # 2. Teams
    op.create_table(
        'teams',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('lead_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_teams_id_org'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_teams_org_name'),
    )
    op.create_index('idx_teams_org_id', 'teams', ['organization_id'], unique=False)
    op.create_index('idx_teams_lead_id', 'teams', ['lead_id'], unique=False)

    # 3. Team Members
    op.create_table(
        'team_members',
        sa.Column('team_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('team_id', 'user_id'),
    )
    op.create_index('idx_team_members_user_id', 'team_members', ['user_id'], unique=False)

    # 4. Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('team_id', sa.Uuid(), nullable=True),
        sa.Column('key', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', project_status_enum, server_default='planning', nullable=False),
        sa.Column('priority', priority_level_enum, server_default='medium', nullable=False),
        sa.Column('color', sa.String(length=10), server_default='#8B7CFF', nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('manager_id', sa.Uuid(), nullable=True),
        sa.Column('progress', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('budget', sa.Numeric(precision=14, scale=2), server_default='0.00', nullable=True),
        sa.Column('spent', sa.Numeric(precision=14, scale=2), server_default='0.00', nullable=True),
        sa.Column('last_task_number', sa.Integer(), server_default='100', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='chk_projects_progress'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_projects_id_org'),
        sa.UniqueConstraint('organization_id', 'key', name='uq_projects_org_key'),
    )
    op.create_index('idx_projects_org_status', 'projects', ['organization_id', 'status'], unique=False)
    op.create_index('idx_projects_team_id', 'projects', ['team_id'], unique=False)
    op.create_index('idx_projects_manager_id', 'projects', ['manager_id'], unique=False)

    # 5. Project Members
    op.create_table(
        'project_members',
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id', 'user_id'),
    )
    op.create_index('idx_project_members_user_id', 'project_members', ['user_id'], unique=False)

    # 6. Tasks (with compound tenant isolation FK)
    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('task_number', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('status', task_status_enum, server_default='todo', nullable=False),
        sa.Column('priority', priority_level_enum, server_default='medium', nullable=False),
        sa.Column('assignee_id', sa.Uuid(), nullable=True),
        sa.Column('creator_id', sa.Uuid(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('estimated_hours', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('actual_hours', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('order', sa.Float().with_variant(sa.Double(), 'postgresql'), server_default='1000.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['project_id', 'organization_id'],
            ['projects.id', 'projects.organization_id'],
            ondelete='CASCADE',
            name='fk_tasks_project_org',
        ),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_tasks_id_org'),
        sa.UniqueConstraint('project_id', 'task_number', name='uq_tasks_proj_number'),
    )
    op.create_index('idx_tasks_project_status_order', 'tasks', ['project_id', 'status', 'order'], unique=False)
    op.create_index('idx_tasks_assignee_status', 'tasks', ['assignee_id', 'status'], unique=False)
    op.create_index('idx_tasks_org_status', 'tasks', ['organization_id', 'status'], unique=False)
    op.create_index('idx_tasks_due_date', 'tasks', ['due_date'], unique=False)

    # 7. Subtasks
    op.create_table(
        'subtasks',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_subtasks_task_order', 'subtasks', ['task_id', 'order'], unique=False)

    # 8. Labels
    op.create_table(
        'labels',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=10), server_default='#8B7CFF', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_labels_org_name'),
    )
    op.create_index('idx_labels_org_id', 'labels', ['organization_id'], unique=False)

    # 9. Task Labels
    op.create_table(
        'task_labels',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('label_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['label_id'], ['labels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'label_id'),
    )
    op.create_index('idx_task_labels_label_id', 'task_labels', ['label_id'], unique=False)

    # 10. Comments
    op.create_table(
        'comments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_comments_task_created', 'comments', ['task_id', 'created_at'], unique=False)
    op.create_index('idx_comments_author_id', 'comments', ['author_id'], unique=False)

    # 11. Attachments
    op.create_table(
        'attachments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('task_id', sa.Uuid(), nullable=True),
        sa.Column('comment_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('storage_bucket', sa.String(length=63), server_default='flowstate-attachments', nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint(
            'project_id IS NOT NULL OR task_id IS NOT NULL OR comment_id IS NOT NULL',
            name='chk_attachment_target',
        ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_attachments_org_id', 'attachments', ['organization_id'], unique=False)
    op.create_index('idx_attachments_project_id', 'attachments', ['project_id'], unique=False)
    op.create_index('idx_attachments_task_id', 'attachments', ['task_id'], unique=False)
    op.create_index('idx_attachments_comment_id', 'attachments', ['comment_id'], unique=False)
    op.create_index('idx_attachments_uploaded_by', 'attachments', ['uploaded_by'], unique=False)

    # 12. Activities
    op.create_table(
        'activities',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=30), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('target_title', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_activities_org_created', 'activities', ['organization_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_activities_project_created', 'activities', ['project_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_activities_user_id', 'activities', ['user_id'], unique=False)

    # 13. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('sender_id', sa.Uuid(), nullable=True),
        sa.Column('type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_notifications_user_all', 'notifications', ['user_id', sa.text('created_at DESC')], unique=False)


def downgrade() -> None:
    # Drop tables in reverse topological order
    op.drop_table('notifications')
    op.drop_table('activities')
    op.drop_table('attachments')
    op.drop_table('comments')
    op.drop_table('task_labels')
    op.drop_table('labels')
    op.drop_table('subtasks')
    op.drop_table('tasks')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('team_members')
    op.drop_table('teams')

    # Safely drop domain enums ONLY if no other objects in pg_depend reference them
    op.execute("""
    DO $$
    DECLARE
        notif_deps int;
        task_status_deps int;
        priority_deps int;
        proj_status_deps int;
    BEGIN
        SELECT COUNT(*) INTO notif_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'notification_type'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'notification_type')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF notif_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS notification_type';
        END IF;

        SELECT COUNT(*) INTO task_status_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'task_status'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'task_status')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF task_status_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS task_status';
        END IF;

        SELECT COUNT(*) INTO priority_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'priority_level'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'priority_level')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF priority_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS priority_level';
        END IF;

        SELECT COUNT(*) INTO proj_status_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'project_status'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'project_status')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF proj_status_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS project_status';
        END IF;
    END $$;
    """)
