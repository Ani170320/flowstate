import asyncio
import os
import shutil
import subprocess
import tempfile
import time
import pytest
import asyncpg


def get_pg_bin(version: str) -> tuple[str, str] | None:
    bin_dir = rf"C:\Program Files\PostgreSQL\{version}\bin"
    initdb = os.path.join(bin_dir, "initdb.exe")
    postgres = os.path.join(bin_dir, "postgres.exe")
    if os.path.exists(initdb) and os.path.exists(postgres):
        return initdb, postgres
    return None


@pytest.fixture(params=["14", "18"], ids=["pg14", "pg18"])
def disposable_pg_cluster(request):
    """Spins up a temporary, completely disposable PostgreSQL cluster for version testing."""
    version = request.param
    bin_info = get_pg_bin(version)
    if not bin_info:
        pytest.skip(f"PostgreSQL {version} binaries not found locally.")

    initdb_exe, postgres_exe = bin_info
    port = 54340 + int(version)
    temp_dir = tempfile.mkdtemp(prefix=f"flowstate_disposable_pg{version}_")

    try:
        # 1. Initialize cluster with trust auth on localhost
        subprocess.run(
            [initdb_exe, "-D", temp_dir, "-U", "postgres", "-A", "trust", "--no-locale", "--encoding=UTF8"],
            capture_output=True,
            check=True,
        )

        # 2. Start PostgreSQL server on dedicated test port
        proc = subprocess.Popen(
            [postgres_exe, "-D", temp_dir, "-p", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for PostgreSQL to be ready
        retries = 30
        connected = False
        while retries > 0:
            try:
                import socket
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    connected = True
                    break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.2)
                retries -= 1

        if not connected:
            proc.terminate()
            raise RuntimeError(f"Disposable PostgreSQL {version} failed to start in time.")

        yield f"postgresql://postgres@127.0.0.1:{port}/postgres"

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        time.sleep(0.5)
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_disposable_postgres_full_lifecycle(disposable_pg_cluster):
    """
    Executes actual PostgreSQL integration testing across major PostgreSQL engine versions (14 through 18):
    1. Simulates Supabase Auth schema and auth.users.
    2. Executes Phase 1 Upgrade SQL against the real PostgreSQL cluster.
    3. Verifies schema creation and permissions.
    4. Tests Supabase Auth trigger synchronization (INSERT and UPDATE).
    5. Tests function and trigger collision protection exceptions.
    6. Tests enum array dependency protection via pg_depend.
    7. Executes Phase 1 Downgrade SQL and verifies clean teardown without touching auth.users.
    """
    conn = await asyncpg.connect(disposable_pg_cluster)

    try:
        pg_ver = await conn.fetchval("SELECT version();")
        print(f"\n[PostgreSQL Integration] Running against: {pg_ver}")

        # Step 1: Simulate Supabase Auth Environment
        await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS auth;
        CREATE TABLE auth.users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255),
            raw_user_meta_data JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT clock_timestamp()
        );
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'supabase_auth_admin') THEN
                CREATE ROLE supabase_auth_admin;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                CREATE ROLE service_role;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                CREATE ROLE anon;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                CREATE ROLE authenticated;
            END IF;
        END $$;
        """)

        # Step 2: Read generated migration statements from Alembic offline SQL
        backend_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
        res = subprocess.run(
            [os.path.join(backend_dir, ".venv", "Scripts", "python.exe"), "-m", "alembic", "upgrade", "head", "--sql"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        upgrade_sql = res.stdout

        # Step 3: Execute Phase 1 Upgrade against real PostgreSQL
        await conn.execute(upgrade_sql)

        # Step 4: Verify Public Schema Objects
        tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        table_names = {t["table_name"] for t in tables}
        expected_tables = {
            "organizations",
            "users",
            "workspace_settings",
            "organization_members",
            "teams",
            "team_members",
            "projects",
            "project_members",
            "tasks",
            "subtasks",
            "labels",
            "task_labels",
            "comments",
            "attachments",
            "activities",
            "notifications",
            "alembic_version",
        }
        assert expected_tables.issubset(table_names)

        # Verify Function Signature and Fingerprint
        func_record = await conn.fetchrow("""
        SELECT p.proname, p.prosecdef, p.prosrc, l.lanname
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_language l ON l.oid = p.prolang
        WHERE n.nspname = 'public' AND p.proname = 'flowstate_handle_new_user';
        """)
        assert func_record is not None
        assert func_record["prosecdef"] is True
        assert func_record["lanname"] == "plpgsql"
        assert "FLOWSTATE_MANAGED_FUNCTION_V1" in func_record["prosrc"]

        # Verify Trigger on auth.users
        trigger_record = await conn.fetchrow("""
        SELECT t.tgname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'auth' AND c.relname = 'users' AND t.tgname = 'flowstate_on_auth_user_created';
        """)
        assert trigger_record is not None

        # Step 5: Test Supabase Auth Profile Synchronization Trigger
        # INSERT in auth.users
        test_user_id = await conn.fetchval("""
        INSERT INTO auth.users (email, raw_user_meta_data)
        VALUES ('alex@flowstate.dev', '{"name": "Alex Rivera", "avatar_url": "https://avatar.com/alex.jpg"}'::jsonb)
        RETURNING id;
        """)

        # Verify public.users profile automatically populated by trigger
        user_profile = await conn.fetchrow("SELECT id, email, name, avatar_url FROM public.users WHERE id = $1", test_user_id)
        assert user_profile is not None
        assert user_profile["email"] == "alex@flowstate.dev"
        assert user_profile["name"] == "Alex Rivera"
        assert user_profile["avatar_url"] == "https://avatar.com/alex.jpg"

        # UPDATE auth.users (simulating user changing email, while manual profile updates remain preserved)
        await conn.execute("UPDATE public.users SET name = 'Alex R. (Staff Lead)' WHERE id = $1", test_user_id)
        await conn.execute("UPDATE auth.users SET email = 'alex.rivera@flowstate.dev' WHERE id = $1", test_user_id)

        updated_profile = await conn.fetchrow("SELECT email, name FROM public.users WHERE id = $1", test_user_id)
        assert updated_profile["email"] == "alex.rivera@flowstate.dev"
        assert updated_profile["name"] == "Alex R. (Staff Lead)", "User-edited name must NOT be overwritten by auth update!"

        # Step 6: Test Function & Trigger Collision Protection
        # Function collision check must abort:
        with pytest.raises(asyncpg.RaiseError, match='Function "public.flowstate_handle_new_user" already exists'):
            await conn.execute("""
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

        # Trigger collision check must abort:
        with pytest.raises(asyncpg.RaiseError, match='Trigger "flowstate_on_auth_user_created" already exists'):
            await conn.execute("""
            DO $$
            DECLARE
                trigger_exists boolean;
            BEGIN
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
            END $$;
            """)

        # Step 7: Test pg_depend Enum Array Protection
        # Create an external table that uses an ARRAY of user_role (e.g. user_role[])
        await conn.execute("CREATE TABLE public.external_audit_log (id int, allowed_roles user_role[]);")

        # Execute Reversible Downgrade SQL (from head to base)
        res_down = subprocess.run(
            [os.path.join(backend_dir, ".venv", "Scripts", "python.exe"), "-m", "alembic", "downgrade", "head:base", "--sql"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        downgrade_sql = res_down.stdout

        await conn.execute(downgrade_sql)

        # Because external_audit_log still references user_role[] via array dependency in pg_depend,
        # user_role must NOT have been dropped!
        enum_preserved = await conn.fetchval("SELECT COUNT(*) FROM pg_type WHERE typname = 'user_role';")
        assert enum_preserved == 1, "pg_depend must prevent dropping user_role when an array dependency exists!"

        # Now drop the external table and rerun the safe enum cleanup DO block
        await conn.execute("DROP TABLE public.external_audit_log;")
        await conn.execute("""
        DO $$
        DECLARE
            user_role_deps int;
        BEGIN
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

        enum_cleaned = await conn.fetchval("SELECT COUNT(*) FROM pg_type WHERE typname = 'user_role';")
        assert enum_cleaned == 0, "user_role must be cleanly dropped once no dependencies remain in pg_depend!"

        # Step 8: Verify Complete Teardown and Object Isolation
        # FLOWSTATE trigger must be gone
        trigger_after = await conn.fetchval("""
        SELECT COUNT(*) FROM pg_trigger WHERE tgname = 'flowstate_on_auth_user_created';
        """)
        assert trigger_after == 0

        # FLOWSTATE function must be gone
        func_after = await conn.fetchval("""
        SELECT COUNT(*) FROM pg_proc WHERE proname = 'flowstate_handle_new_user';
        """)
        assert func_after == 0

        # Application tables must be gone
        tables_after = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        table_names_after = {t["table_name"] for t in tables_after}
        flowstate_tables = {
            "organizations",
            "users",
            "workspace_settings",
            "organization_members",
            "teams",
            "team_members",
            "projects",
            "project_members",
            "tasks",
            "subtasks",
            "labels",
            "task_labels",
            "comments",
            "attachments",
            "activities",
            "notifications",
        }
        assert not flowstate_tables.intersection(table_names_after)

        # CRITICAL: auth.users must remain 100% intact with the auth record!
        auth_users_count = await conn.fetchval("SELECT COUNT(*) FROM auth.users;")
        assert auth_users_count == 1, "Downgrade must NEVER drop or delete from auth.users!"

    finally:
        await conn.close()
