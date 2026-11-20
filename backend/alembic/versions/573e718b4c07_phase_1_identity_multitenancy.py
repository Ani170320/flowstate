"""phase_1_identity_multitenancy

Revision ID: 573e718b4c07
Revises: 
Create Date: 2026-11-17 16:26:30.843326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '573e718b4c07'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define PostgreSQL Enum types with exact lowercase values matching domain model
subscription_plan_enum = postgresql.ENUM(
    'free', 'pro', 'enterprise',
    name='subscription_plan',
    create_type=False,
)

user_role_enum = postgresql.ENUM(
    'owner', 'admin', 'manager', 'developer', 'designer', 'viewer',
    name='user_role',
    create_type=False,
)


def upgrade() -> None:
    # 1. Create Enums if they do not exist
    sa.Enum('free', 'pro', 'enterprise', name='subscription_plan').create(op.get_bind(), checkfirst=True)
    sa.Enum('owner', 'admin', 'manager', 'developer', 'designer', 'viewer', name='user_role').create(op.get_bind(), checkfirst=True)

    # 2. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('plan', subscription_plan_enum, server_default='free', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # 3. Create users profile table (linked 1:1 to Supabase auth.users)
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(length=50), server_default='UTC', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Functional index ensuring case-insensitive email uniqueness
    op.create_index('ix_users_email_lower', 'users', [sa.text('lower(email)')], unique=True)
    op.create_index(op.f('ix_users_department'), 'users', ['department'], unique=False)

    # 4. Create workspace_settings table (1:1 with organizations)
    op.create_table(
        'workspace_settings',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='USD', nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='America/San_Francisco', nullable=False),
        sa.Column('working_days', postgresql.ARRAY(sa.SmallInteger()).with_variant(sa.JSON(), 'sqlite'), server_default='{1,2,3,4,5}', nullable=False),
        sa.Column('notifications_email', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notifications_desktop', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('theme', sa.String(length=20), server_default='dark', nullable=False),
        sa.Column('accent_color', sa.String(length=10), server_default='#8B7CFF', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', name='uq_workspace_settings_org_id'),
    )

    # 5. Create organization_members table (RBAC memberships)
    op.create_table(
        'organization_members',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', user_role_enum, server_default='developer', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_organization_members_org_user'),
    )
    op.create_index('idx_org_members_user_id', 'organization_members', ['user_id'], unique=False)
    op.create_index('idx_org_members_org_role', 'organization_members', ['organization_id', 'role'], unique=False)

    # 6. Function collision protection: Check if function exists before creating, abort if collision
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.proname = 'flowstate_handle_new_user'
        ) THEN
            RAISE EXCEPTION 'Safety check failed: Function "public.flowstate_handle_new_user" already exists. Aborting migration to avoid collision.';
        END IF;
    END $$;
    """)

    # Create FLOWSTATE-specific trigger function (CREATE FUNCTION, never CREATE OR REPLACE)
    op.execute("""
    CREATE FUNCTION public.flowstate_handle_new_user()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = ''
    AS $$
    -- FLOWSTATE_MANAGED_FUNCTION_V1
    DECLARE
        normalized_email text;
        initial_name text;
        initial_avatar text;
    BEGIN
        -- Email normalization and fallback handling for non-email / phone / anonymous signups
        IF NEW.email IS NOT NULL AND pg_catalog.btrim(NEW.email) <> '' THEN
            normalized_email := pg_catalog.lower(pg_catalog.btrim(NEW.email));
        ELSE
            normalized_email := NEW.id::text || '@no-email.flowstate.internal';
        END IF;

        -- Extract initial cosmetic metadata without trusting it for authorization
        -- Uses standard SQL COALESCE, NULLIF and btrim so empty strings fall back safely
        initial_name := COALESCE(
            NULLIF(pg_catalog.btrim(NEW.raw_user_meta_data->>'name'), ''),
            NULLIF(pg_catalog.btrim(pg_catalog.split_part(normalized_email, '@', 1)), ''),
            'User'
        );
        initial_avatar := NULLIF(pg_catalog.btrim(NEW.raw_user_meta_data->>'avatar_url'), '');

        -- On INSERT: Create new application profile.
        -- On UPDATE: Synchronize email ONLY if changed in auth.users.
        -- Crucial: NEVER overwrite user-edited profile fields (name, avatar, department, bio)
        -- on auth.users update events!
        INSERT INTO public.users (
            id,
            email,
            name,
            avatar_url,
            timezone,
            is_active,
            created_at,
            updated_at
        )
        VALUES (
            NEW.id,
            normalized_email,
            initial_name,
            initial_avatar,
            'UTC',
            TRUE,
            pg_catalog.clock_timestamp(),
            pg_catalog.clock_timestamp()
        )
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            updated_at = pg_catalog.clock_timestamp()
        WHERE public.users.email IS DISTINCT FROM EXCLUDED.email;

        RETURN NEW;
    END;
    $$;
    """)

    # 7. Restrict trigger function execution permissions (Security Best Practice)
    op.execute("REVOKE ALL ON FUNCTION public.flowstate_handle_new_user() FROM PUBLIC;")
    op.execute("REVOKE EXECUTE ON FUNCTION public.flowstate_handle_new_user() FROM anon, authenticated;")
    op.execute("GRANT EXECUTE ON FUNCTION public.flowstate_handle_new_user() TO supabase_auth_admin, service_role, postgres;")

    # 8. Trigger collision protection: Verify trigger does not exist on auth.users before creating
    op.execute("""
    DO $$
    DECLARE
        table_exists boolean;
        trigger_exists boolean;
    BEGIN
        SELECT EXISTS (
            SELECT 1
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'auth' AND c.relname = 'users'
        ) INTO table_exists;

        IF NOT table_exists THEN
            RAISE EXCEPTION 'Required table auth.users does not exist. Ensure Supabase Auth is enabled before running this migration.';
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE t.tgname = 'flowstate_on_auth_user_created'
              AND n.nspname = 'auth'
              AND c.relname = 'users'
              AND NOT t.tgisinternal
        ) INTO trigger_exists;

        IF trigger_exists THEN
            RAISE EXCEPTION 'Safety check failed: Trigger "flowstate_on_auth_user_created" already exists on auth.users. Aborting migration to avoid collision.';
        END IF;

        EXECUTE 'CREATE TRIGGER flowstate_on_auth_user_created
            AFTER INSERT OR UPDATE ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.flowstate_handle_new_user()';
    END $$;
    """)


def downgrade() -> None:
    # 1. Cleanly and safely remove trigger and function with ownership verification
    # Ensures downgrade removes ONLY the FLOWSTATE-owned trigger and function
    op.execute("""
    DO $$
    DECLARE
        existing_func text;
        table_exists boolean;
    BEGIN
        SELECT EXISTS (
            SELECT 1
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'auth' AND c.relname = 'users'
        ) INTO table_exists;

        IF table_exists THEN
            SELECT n_proc.nspname || '.' || p.proname INTO existing_func
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
            JOIN pg_catalog.pg_namespace n_table ON n_table.oid = c.relnamespace
            JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
            JOIN pg_catalog.pg_namespace n_proc ON n_proc.oid = p.pronamespace
            WHERE t.tgname = 'flowstate_on_auth_user_created'
              AND n_table.nspname = 'auth'
              AND c.relname = 'users'
              AND NOT t.tgisinternal;

            IF existing_func IS NOT NULL THEN
                IF existing_func = 'public.flowstate_handle_new_user' THEN
                    EXECUTE 'DROP TRIGGER flowstate_on_auth_user_created ON auth.users';
                ELSE
                    RAISE EXCEPTION 'Safety check failed: Trigger "flowstate_on_auth_user_created" on auth.users references external function "%" instead of "public.flowstate_handle_new_user". Aborting downgrade to prevent dropping an unmanaged trigger.', existing_func;
                END IF;
            END IF;
        END IF;
    END $$;
    """)
    # 2. Function verification before dropping: verify ownership, signature, and body fingerprint
    # Aborts if ownership, signature, or FLOWSTATE fingerprint cannot be established
    op.execute("""
    DO $$
    DECLARE
        func_record RECORD;
        func_matches boolean;
    BEGIN
        SELECT 
            p.oid,
            p.prorettype,
            p.pronargs,
            p.prosecdef,
            p.prosrc,
            l.lanname
        INTO func_record
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_language l ON l.oid = p.prolang
        WHERE n.nspname = 'public'
          AND p.proname = 'flowstate_handle_new_user';

        IF func_record.oid IS NOT NULL THEN
            func_matches := (
                func_record.prorettype = 'trigger'::regtype
                AND func_record.pronargs = 0
                AND func_record.prosecdef = TRUE
                AND func_record.lanname = 'plpgsql'
                AND func_record.prosrc LIKE '%FLOWSTATE_MANAGED_FUNCTION_V1%'
            );

            IF NOT func_matches THEN
                RAISE EXCEPTION 'Safety check failed: Function "public.flowstate_handle_new_user" exists but does not match the FLOWSTATE signature/fingerprint. Aborting downgrade to prevent dropping a modified or external function.';
            END IF;

            EXECUTE 'DROP FUNCTION public.flowstate_handle_new_user()';
        END IF;
    END $$;
    """)

    # 3. Drop tables in reverse topological order
    op.drop_index('idx_org_members_org_role', table_name='organization_members')
    op.drop_index('idx_org_members_user_id', table_name='organization_members')
    op.drop_table('organization_members')

    op.drop_table('workspace_settings')

    op.drop_index(op.f('ix_users_department'), table_name='users')
    op.drop_index('ix_users_email_lower', table_name='users')
    op.drop_table('users')

    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_table('organizations')

    # 4. Safely drop domain enums ONLY if no dependent objects remain in pg_depend
    # Checks both direct dependencies and indirect / array dependencies (via typarray)
    op.execute("""
    DO $$
    DECLARE
        sub_plan_deps int;
        user_role_deps int;
    BEGIN
        -- Check pg_depend for subscription_plan (including array dependencies via typarray)
        SELECT COUNT(*) INTO sub_plan_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'subscription_plan'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'subscription_plan')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF sub_plan_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS subscription_plan';
        END IF;

        -- Check pg_depend for user_role (including array dependencies via typarray)
        SELECT COUNT(*) INTO user_role_deps
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_type t ON t.oid = d.refobjid
        WHERE (
            t.typname = 'user_role'
            OR t.oid = (SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'user_role')
        )
        AND d.deptype <> 'i'
        AND d.classid <> 'pg_catalog.pg_type'::regclass;

        IF user_role_deps = 0 THEN
            EXECUTE 'DROP TYPE IF EXISTS user_role';
        END IF;
    END $$;
    """)
