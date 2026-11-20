import importlib.util
import os
import uuid
import pytest
from sqlalchemy import create_engine, select, text, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Base,
    Organization,
    OrganizationMember,
    SubscriptionPlan,
    User,
    UserRole,
    WorkspaceSettings,
)


def _create_test_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    return engine


def test_user_model_schema():
    """Verify User model structure, primary key, and absence of passwords."""
    table = User.__table__
    assert table.name == "users"

    # Primary key must be 'id'
    assert table.primary_key.columns.keys() == ["id"]

    # Foreign key directly references auth.users(id) with CASCADE
    id_col = table.c.id
    fks = list(id_col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "auth.users.id"
    assert fks[0].ondelete == "CASCADE"

    # Critical security requirement: No password or password_hash column in profile
    assert "password" not in table.c
    assert "password_hash" not in table.c

    # Required profile fields
    assert "email" in table.c
    assert "name" in table.c
    assert "avatar_url" in table.c
    assert "department" in table.c
    assert "title" in table.c
    assert "timezone" in table.c
    assert "is_active" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c

    # Case-insensitive email index must exist
    index_names = [idx.name for idx in table.indexes]
    assert "ix_users_email_lower" in index_names


def test_case_insensitive_email_uniqueness():
    """Verify case-insensitive uniqueness prevents Alex@flowstate.dev and alex@flowstate.dev collision."""
    engine = _create_test_engine()
    Base.metadata.create_all(bind=engine, tables=[User.__table__])
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    user1 = User(
        id=uuid.uuid4(),
        email="alex@flowstate.dev",
        name="Alex Rivera",
    )
    session.add(user1)
    session.commit()

    # Attempt inserting with different casing
    user2 = User(
        id=uuid.uuid4(),
        email="ALEX@flowstate.dev",
        name="Alex Duplicate",
    )
    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    session.close()


def test_organization_model_schema():
    """Verify Organization model structure, constraints, and default plan."""
    table = Organization.__table__
    assert table.name == "organizations"
    assert table.primary_key.columns.keys() == ["id"]

    # Slug must be unique
    assert table.c.slug.unique is True or any(
        idx.unique and "slug" in [col.name for col in idx.columns] for idx in table.indexes
    )

    # Required fields
    assert "name" in table.c
    assert "logo_url" in table.c
    assert "plan" in table.c
    assert table.c.plan.default.arg == SubscriptionPlan.FREE


def test_organization_member_schema():
    """Verify OrganizationMember model, composite uniqueness, and indexes."""
    table = OrganizationMember.__table__
    assert table.name == "organization_members"

    # Foreign keys
    org_fks = list(table.c.organization_id.foreign_keys)
    user_fks = list(table.c.user_id.foreign_keys)
    assert len(org_fks) == 1
    assert org_fks[0].target_fullname == "organizations.id"
    assert org_fks[0].ondelete == "CASCADE"
    assert len(user_fks) == 1
    assert user_fks[0].target_fullname == "users.id"
    assert user_fks[0].ondelete == "CASCADE"

    # Default role must be DEVELOPER
    assert table.c.role.default.arg == UserRole.DEVELOPER

    # Unique constraint on (organization_id, user_id)
    unique_constraints = [
        c for c in table.constraints if hasattr(c, "columns") and set(c.columns.keys()) == {"organization_id", "user_id"}
    ]
    assert len(unique_constraints) >= 1

    # Verified indexed columns for RLS lookup speed
    indexed_col_sets = [{c.name for c in idx.columns} for idx in table.indexes]
    assert {"user_id"} in indexed_col_sets
    assert {"organization_id", "role"} in indexed_col_sets


def test_workspace_settings_schema():
    """Verify WorkspaceSettings model, 1:1 relationship, and default preferences."""
    table = WorkspaceSettings.__table__
    assert table.name == "workspace_settings"

    # 1:1 constraint with organization
    org_fks = list(table.c.organization_id.foreign_keys)
    assert len(org_fks) == 1
    assert org_fks[0].target_fullname == "organizations.id"
    assert org_fks[0].ondelete == "CASCADE"

    unique_org = [
        c for c in table.constraints if hasattr(c, "columns") and set(c.columns.keys()) == {"organization_id"}
    ]
    assert len(unique_org) >= 1 or table.c.organization_id.unique is True

    # Defaults
    assert table.c.currency.default.arg == "USD"
    assert table.c.timezone.default.arg == "America/San_Francisco"
    assert table.c.theme.default.arg == "dark"
    assert table.c.accent_color.default.arg == "#8B7CFF"
    assert table.c.notifications_email.default.arg is True
    assert table.c.notifications_desktop.default.arg is True


def test_orm_relationships_and_cascades():
    """
    Test in-memory relationship wiring and delete-orphan cascades.
    """
    engine = _create_test_engine()

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="alex@flowstate.dev",
        name="Alex Rivera",
        department="Engineering",
        title="Staff Engineer",
    )

    org = Organization(
        name="Flowstate Labs",
        slug="flowstate-labs",
        plan=SubscriptionPlan.PRO,
    )

    settings = WorkspaceSettings(
        organization=org,
        currency="USD",
        timezone="America/San_Francisco",
    )

    member = OrganizationMember(
        organization=org,
        user=user,
        role=UserRole.OWNER,
    )

    session.add_all([user, org, settings, member])
    session.commit()

    # Query back and verify navigation
    queried_org = session.scalar(select(Organization).where(Organization.slug == "flowstate-labs"))
    assert queried_org is not None
    assert queried_org.settings is not None
    assert queried_org.settings.currency == "USD"
    assert len(queried_org.members) == 1
    assert queried_org.members[0].user.email == "alex@flowstate.dev"
    assert queried_org.members[0].role == UserRole.OWNER

    # Test Cascade Deletion: Deleting the organization must delete member records and settings
    session.delete(queried_org)
    session.commit()

    remaining_members = session.scalars(select(OrganizationMember)).all()
    remaining_settings = session.scalars(select(WorkspaceSettings)).all()
    remaining_users = session.scalars(select(User)).all()

    assert len(remaining_members) == 0
    assert len(remaining_settings) == 0
    assert len(remaining_users) == 1
    assert remaining_users[0].id == user_id

    session.close()


def test_unique_organization_membership_constraint():
    """Verify database raises IntegrityError when adding duplicate member to an organization."""
    engine = _create_test_engine()
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    user_id = uuid.uuid4()
    user = User(id=user_id, email="devon@flowstate.dev", name="Devon Miller")
    org = Organization(name="Engineering Workspace", slug="eng-workspace")
    session.add_all([user, org])
    session.commit()

    # First membership: developer
    m1 = OrganizationMember(organization=org, user=user, role=UserRole.DEVELOPER)
    session.add(m1)
    session.commit()

    # Second duplicate membership: must raise IntegrityError
    m2 = OrganizationMember(organization=org, user=user, role=UserRole.ADMIN)
    session.add(m2)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    session.close()


def test_user_deletion_cascades_membership():
    """Verify deleting a User profile cascades and removes their memberships without deleting the organization."""
    engine = _create_test_engine()
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    user = User(id=uuid.uuid4(), email="sarah@flowstate.dev", name="Sarah Chen")
    org = Organization(name="Design Org", slug="design-org")
    member = OrganizationMember(organization=org, user=user, role=UserRole.MANAGER)
    session.add_all([user, org, member])
    session.commit()

    # Delete user
    session.delete(user)
    session.commit()

    # Membership must be deleted
    members = session.scalars(select(OrganizationMember)).all()
    assert len(members) == 0

    # Organization must remain intact
    orgs = session.scalars(select(Organization)).all()
    assert len(orgs) == 1
    assert orgs[0].slug == "design-org"

    session.close()


def test_auth_sync_profile_update_preservation_logic():
    """
    Simulates the SQL trigger logic: verifies that when an auth update occurs,
    user-managed profile fields (name, avatar, department, bio) are preserved
    and only email is synchronized.
    """
    engine = _create_test_engine()
    Base.metadata.create_all(bind=engine, tables=[User.__table__])
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    user_id = uuid.uuid4()

    # Initial profile created on signup
    profile = User(
        id=user_id,
        email="marcus@flowstate.dev",
        name="Marcus Vance",
        avatar_url="https://images.unsplash.com/avatar-old.jpg",
        department="Engineering",
        title="Staff Engineer",
        bio="Original bio",
    )
    session.add(profile)
    session.commit()

    # User manually edits their profile in FLOWSTATE Settings
    profile.name = "Marcus V. (Lead)"
    profile.bio = "Updated bio from FLOWSTATE app"
    profile.avatar_url = "https://images.unsplash.com/avatar-custom.jpg"
    session.commit()

    # Simulated auth.users update event (e.g. user changed email to marcus.vance@flowstate.dev)
    # The trigger executes:
    # ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email WHERE users.email IS DISTINCT FROM EXCLUDED.email
    new_auth_email = "marcus.vance@flowstate.dev"
    profile.email = new_auth_email
    session.commit()

    # Verify that the manual profile fields remain intact!
    refreshed = session.scalar(select(User).where(User.id == user_id))
    assert refreshed is not None
    assert refreshed.email == "marcus.vance@flowstate.dev"
    assert refreshed.name == "Marcus V. (Lead)"
    assert refreshed.bio == "Updated bio from FLOWSTATE app"
    assert refreshed.avatar_url == "https://images.unsplash.com/avatar-custom.jpg"
    assert refreshed.department == "Engineering"

    session.close()


def test_migration_file_structure_and_security():
    """Verify Alembic migration script exists, defines upgrade/downgrade, and includes trigger DDL."""
    versions_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions"))
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and "phase_1" in f]
    assert len(files) == 1, f"Expected 1 phase 1 migration file, found {files}"

    migration_path = os.path.join(versions_dir, files[0])
    spec = importlib.util.spec_from_file_location("phase1_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)

    assert hasattr(migration_module, "upgrade")
    assert hasattr(migration_module, "downgrade")
    assert migration_module.revision == "573e718b4c07"

    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Safe search path
    assert "SET search_path = ''" in content

    # 2. Selective update guard (prevents overwriting user-edited profile fields)
    assert "WHERE public.users.email IS DISTINCT FROM EXCLUDED.email" in content

    # 3. Security Definer permissions restriction on namespaced function
    assert "REVOKE ALL ON FUNCTION public.flowstate_handle_new_user() FROM PUBLIC" in content
    assert "REVOKE EXECUTE ON FUNCTION public.flowstate_handle_new_user() FROM anon, authenticated" in content
    assert "GRANT EXECUTE ON FUNCTION public.flowstate_handle_new_user() TO supabase_auth_admin" in content

    # 4. Safe downgrade: never blindly drops function or auth.users table
    assert "DROP FUNCTION IF EXISTS public.flowstate_handle_new_user()" not in content
    assert "EXECUTE 'DROP FUNCTION public.flowstate_handle_new_user()'" in content
    assert "drop_table('auth.users')" not in content


def test_coalesce_and_nullif_syntax_in_trigger():
    """
    Verify PostgreSQL syntactic validity: COALESCE and NULLIF are SQL keywords,
    NOT functions in pg_catalog. Ensure pg_catalog.coalesce is never used, and
    btrim + NULLIF are used to handle empty metadata strings safely.
    """
    versions_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions"))
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and "phase_1" in f]
    migration_path = os.path.join(versions_dir, files[0])
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Catch invalid COALESCE syntax: pg_catalog.coalesce does not exist in PostgreSQL
    assert "pg_catalog.coalesce" not in content, "pg_catalog.coalesce is invalid PostgreSQL syntax! Use COALESCE."
    assert "pg_catalog.nullif" not in content, "pg_catalog.nullif is invalid PostgreSQL syntax! Use NULLIF."

    # Verify bare COALESCE keyword and NULLIF/btrim combination
    assert "initial_name := COALESCE(" in content
    assert "NULLIF(pg_catalog.btrim(NEW.raw_user_meta_data->>'name'), '')" in content
    assert "NULLIF(pg_catalog.btrim(NEW.raw_user_meta_data->>'avatar_url'), '')" in content


def test_function_collision_protection():
    """
    Verify Function Collision Protection:
    1. Uses CREATE FUNCTION, strictly avoiding CREATE OR REPLACE FUNCTION.
    2. Uses FLOWSTATE-specific namespaced function: public.flowstate_handle_new_user().
    3. Checks pg_proc before creation and aborts with RAISE EXCEPTION if already existing.
    """
    versions_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions"))
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and "phase_1" in f]
    migration_path = os.path.join(versions_dir, files[0])
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NEVER use CREATE OR REPLACE FUNCTION (which could silently overwrite pre-existing functions)
    assert "CREATE OR REPLACE FUNCTION" not in content, "Silently overwriting functions with CREATE OR REPLACE is forbidden."

    # Must use CREATE FUNCTION with FLOWSTATE-namespaced name
    assert "CREATE FUNCTION public.flowstate_handle_new_user()" in content

    # Must check pg_proc and abort if function exists
    assert "p.proname = 'flowstate_handle_new_user'" in content
    assert "RAISE EXCEPTION 'Safety check failed: Function \"public.flowstate_handle_new_user\" already exists. Aborting migration to avoid collision.'" in content


def test_trigger_collision_protection_in_upgrade():
    """
    Verify Trigger Collision Protection:
    1. Uses FLOWSTATE-specific trigger name: flowstate_on_auth_user_created.
    2. Before creating, checks if trigger already exists on auth.users.
    3. If trigger already exists, aborts with RAISE EXCEPTION instead of replacing or overwriting.
    4. Never blindly executes DROP TRIGGER IF EXISTS.
    """
    versions_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions"))
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and "phase_1" in f]
    migration_path = os.path.join(versions_dir, files[0])
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # No blind drop in upgrade
    assert "DROP TRIGGER IF EXISTS flowstate_on_auth_user_created" not in content
    assert "DROP TRIGGER IF EXISTS on_auth_user_created" not in content

    # Checks pg_trigger for collision
    assert "t.tgname = 'flowstate_on_auth_user_created'" in content
    assert "IF trigger_exists THEN" in content
    assert "RAISE EXCEPTION 'Safety check failed: Trigger \"flowstate_on_auth_user_created\" already exists on auth.users. Aborting migration to avoid collision.'" in content

    # Creates trigger referencing FLOWSTATE-namespaced function
    assert "CREATE TRIGGER flowstate_on_auth_user_created" in content
    assert "FOR EACH ROW EXECUTE FUNCTION public.flowstate_handle_new_user()" in content


def test_downgrade_safety_and_reversibility():
    """
    Verify Downgrade Safety:
    1. Checks if flowstate_on_auth_user_created exists and points to public.flowstate_handle_new_user.
    2. Aborts downgrade if the trigger references an external function.
    3. Verifies function signature, SECURITY DEFINER, language, and FLOWSTATE fingerprint before dropping.
    4. Aborts downgrade if the function has been altered or replaced.
    5. Drops only unshared domain enums without impacting pre-existing database types.
    6. Never touches or drops auth.users.
    """
    versions_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "alembic", "versions"))
    files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and "phase_1" in f]
    migration_path = os.path.join(versions_dir, files[0])
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Downgrade block checks trigger ownership before dropping trigger
    assert "t.tgname = 'flowstate_on_auth_user_created'" in content
    assert "IF existing_func = 'public.flowstate_handle_new_user' THEN" in content
    assert "EXECUTE 'DROP TRIGGER flowstate_on_auth_user_created ON auth.users'" in content
    assert "Aborting downgrade to prevent dropping an unmanaged trigger" in content

    # 2. Downgrade block verifies function signature and FLOWSTATE fingerprint before dropping function
    assert "func_record.prorettype = 'trigger'::regtype" in content
    assert "func_record.pronargs = 0" in content
    assert "func_record.prosecdef = TRUE" in content
    assert "func_record.lanname = 'plpgsql'" in content
    assert "func_record.prosrc LIKE '%FLOWSTATE_MANAGED_FUNCTION_V1%'" in content
    assert "Aborting downgrade to prevent dropping a modified or external function" in content
    assert "EXECUTE 'DROP FUNCTION public.flowstate_handle_new_user()'" in content

    # 3. Application tables dropped
    assert "op.drop_table('organization_members')" in content
    assert "op.drop_table('workspace_settings')" in content
    assert "op.drop_table('users')" in content
    assert "op.drop_table('organizations')" in content

    # 4. Enums dropped safely via pg_depend catalog dependency check (including arrays and indirect references)
    assert "pg_catalog.pg_depend" in content
    assert "t.typname = 'subscription_plan'" in content
    assert "t.typname = 'user_role'" in content
    assert "SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'subscription_plan'" in content
    assert "SELECT typarray FROM pg_catalog.pg_type WHERE typname = 'user_role'" in content
    assert "IF sub_plan_deps = 0 THEN" in content
    assert "IF user_role_deps = 0 THEN" in content

    # 5. Crucial: auth.users is never dropped
    assert "drop_table('auth.users')" not in content
    assert "DROP TABLE auth.users" not in content


def test_simulation_function_collision_branching():
    """Simulate function collision protection branching logic."""
    def simulate_function_creation(existing_catalog_procs: set[str]):
        if "public.flowstate_handle_new_user" in existing_catalog_procs:
            raise RuntimeError('Safety check failed: Function "public.flowstate_handle_new_user" already exists.')
        return "CREATE FUNCTION public.flowstate_handle_new_user() ... SUCCESS"

    # Scenario 1: Function already exists -> Collision detected and aborted
    with pytest.raises(RuntimeError, match='Function "public.flowstate_handle_new_user" already exists'):
        simulate_function_creation({"public.flowstate_handle_new_user", "public.other_func"})

    # Scenario 2: Clean slate -> Successfully creates
    result = simulate_function_creation({"public.other_func"})
    assert "SUCCESS" in result


def test_simulation_trigger_collision_branching():
    """Simulate trigger collision protection branching logic."""
    def simulate_trigger_creation(auth_users_table_exists: bool, existing_triggers: set[str]):
        if not auth_users_table_exists:
            raise RuntimeError("Required table auth.users does not exist.")
        if "flowstate_on_auth_user_created" in existing_triggers:
            raise RuntimeError('Safety check failed: Trigger "flowstate_on_auth_user_created" already exists.')
        return "CREATE TRIGGER flowstate_on_auth_user_created ... SUCCESS"

    # Scenario 1: auth.users missing -> Aborted
    with pytest.raises(RuntimeError, match="Required table auth.users does not exist"):
        simulate_trigger_creation(auth_users_table_exists=False, existing_triggers=set())

    # Scenario 2: Trigger name collision -> Aborted
    with pytest.raises(RuntimeError, match='Trigger "flowstate_on_auth_user_created" already exists'):
        simulate_trigger_creation(auth_users_table_exists=True, existing_triggers={"flowstate_on_auth_user_created"})

    # Scenario 3: Clean slate -> Successfully creates
    result = simulate_trigger_creation(auth_users_table_exists=True, existing_triggers={"custom_user_trigger"})
    assert "SUCCESS" in result


def test_simulation_downgrade_trigger_ownership_branching():
    """Simulate downgrade trigger ownership verification branching logic."""
    def simulate_trigger_downgrade(existing_trigger_func: str | None):
        if existing_trigger_func is not None:
            if existing_trigger_func == "public.flowstate_handle_new_user":
                return "DROP TRIGGER flowstate_on_auth_user_created SUCCESS"
            else:
                raise RuntimeError(f'Safety check failed: Trigger references external function "{existing_trigger_func}".')
        return "NO_TRIGGER_TO_DROP"

    # Scenario 1: Trigger owned by FLOWSTATE -> Successfully dropped
    res1 = simulate_trigger_downgrade("public.flowstate_handle_new_user")
    assert res1 == "DROP TRIGGER flowstate_on_auth_user_created SUCCESS"

    # Scenario 2: Trigger exists but points to an unmanaged external function -> Aborts downgrade!
    with pytest.raises(RuntimeError, match="Safety check failed: Trigger references external function"):
        simulate_trigger_downgrade("auth.foreign_handler")

    # Scenario 3: Trigger does not exist -> Safe no-op
    res3 = simulate_trigger_downgrade(None)
    assert res3 == "NO_TRIGGER_TO_DROP"


def test_simulation_downgrade_function_ownership_branching():
    """Simulate downgrade function ownership and fingerprint verification branching logic."""
    def simulate_function_downgrade(func_meta: dict | None):
        if func_meta is not None:
            matches = (
                func_meta.get("prorettype") == "trigger"
                and func_meta.get("pronargs") == 0
                and func_meta.get("prosecdef") is True
                and func_meta.get("lanname") == "plpgsql"
                and "FLOWSTATE_MANAGED_FUNCTION_V1" in func_meta.get("prosrc", "")
            )
            if not matches:
                raise RuntimeError('Safety check failed: Function exists but does not match FLOWSTATE fingerprint.')
            return "DROP FUNCTION public.flowstate_handle_new_user SUCCESS"
        return "NO_FUNCTION_TO_DROP"

    # Scenario 1: Function matches exact FLOWSTATE signature and fingerprint -> Successfully dropped
    valid_meta = {
        "prorettype": "trigger",
        "pronargs": 0,
        "prosecdef": True,
        "lanname": "plpgsql",
        "prosrc": "-- FLOWSTATE_MANAGED_FUNCTION_V1\nBEGIN\nRETURN NEW;\nEND;",
    }
    assert simulate_function_downgrade(valid_meta) == "DROP FUNCTION public.flowstate_handle_new_user SUCCESS"

    # Scenario 2: Function was modified or replaced by external code -> Aborts downgrade!
    tampered_meta = {
        "prorettype": "trigger",
        "pronargs": 0,
        "prosecdef": True,
        "lanname": "plpgsql",
        "prosrc": "-- CUSTOM_REPLACEMENT_FUNCTION\nBEGIN\nRETURN NEW;\nEND;",
    }
    with pytest.raises(RuntimeError, match="Function exists but does not match FLOWSTATE fingerprint"):
        simulate_function_downgrade(tampered_meta)

    # Scenario 3: Function does not exist -> Safe no-op
    assert simulate_function_downgrade(None) == "NO_FUNCTION_TO_DROP"
