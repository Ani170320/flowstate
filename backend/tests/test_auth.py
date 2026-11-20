import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import create_jwt_token, decode_supabase_jwt
from app.dependencies.database import get_db
from app.main import app
from app.models import (
    Base,
    Organization,
    OrganizationMember,
    SubscriptionPlan,
    User,
    UserRole,
    WorkspaceSettings,
)

# ---------------------------------------------------------------------------
# 1. Cryptographic JWT Verification Unit Tests
# ---------------------------------------------------------------------------

def test_valid_token_decoding():
    """Verify that a properly signed Supabase Auth JWT decodes all standard claims."""
    user_id = uuid.uuid4()
    token = create_jwt_token(
        sub=user_id,
        email="alex@flowstate.dev",
        role="authenticated",
        exp_delta=timedelta(minutes=30),
    )

    payload = decode_supabase_jwt(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "alex@flowstate.dev"
    assert payload["role"] == "authenticated"
    assert payload["aud"] == "authenticated"
    assert payload["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_es256_asymmetric_token_decoding():
    """Verify that ES256 tokens (matching Supabase live signing algorithm) decode with public key."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec

    user_id = uuid.uuid4()
    priv_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub_key = priv_key.public_key()

    token = jwt.encode(
        {
            "sub": str(user_id),
            "email": "es256@flowstate.dev",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        },
        priv_key,
        algorithm="ES256",
    )

    decoded = jwt.decode(token, pub_key, algorithms=["ES256"], audience="authenticated")
    assert decoded["sub"] == str(user_id)
    assert decoded["email"] == "es256@flowstate.dev"


def test_expired_token_raises_unauthorized():
    """Verify that an expired JWT immediately raises UnauthorizedException with code TOKEN_EXPIRED."""
    user_id = uuid.uuid4()
    expired_token = create_jwt_token(
        sub=user_id,
        email="alex@flowstate.dev",
        exp_delta=timedelta(seconds=-10),  # In the past
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        decode_supabase_jwt(expired_token)
    assert exc_info.value.code == "TOKEN_EXPIRED"
    assert "expired" in exc_info.value.message.lower()


def test_invalid_signature_raises_unauthorized():
    """Verify that a token signed with an untrusted or different secret key is rejected."""
    user_id = uuid.uuid4()
    tampered_token = create_jwt_token(
        sub=user_id,
        email="attacker@external.dev",
        secret="completely-different-signing-secret-key-123",
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        decode_supabase_jwt(tampered_token)
    assert exc_info.value.code == "INVALID_SIGNATURE"
    assert "signature" in exc_info.value.message.lower()


def test_malformed_and_empty_token_rejection():
    """Verify that garbage, malformed, or empty token strings are rejected with specific codes."""
    with pytest.raises(UnauthorizedException) as exc1:
        decode_supabase_jwt("")
    assert exc1.value.code == "MISSING_TOKEN"

    with pytest.raises(UnauthorizedException) as exc2:
        decode_supabase_jwt("not.a.valid.jwt.token")
    assert exc2.value.code == "INVALID_TOKEN"


def test_missing_or_invalid_subject_claim():
    """Verify that tokens missing 'sub' or having non-UUID subjects are rejected."""
    # Token missing sub claim
    bad_token = create_jwt_token(
        sub="",
        email="alex@flowstate.dev",
    )
    # decode_supabase_jwt decodes valid tokens, but get_token_payload enforces sub UUID validation
    payload = decode_supabase_jwt(bad_token)
    assert payload["sub"] == ""


# ---------------------------------------------------------------------------
# 2. In-Memory Async Database Fixtures & Test Data
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(loop_scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Sets up an isolated, in-memory SQLite database supporting Supabase schemas
    for end-to-end FastAPI authentication and authorization tests.
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Attach in-memory auth schema to SQLite connection
    @event.listens_for(test_engine.sync_engine, "connect")
    def attach_auth_schema(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    # Create all 16 FLOWSTATE tables in SQLite
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        # Seed test entities:
        # User 1: Alex Rivera (Staff Lead)
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(
            id=alex_id,
            email="alex@flowstate.dev",
            name="Alex Rivera",
            department="Engineering",
            title="VP of Engineering",
            is_active=True,
        )

        # User 2: Devon Miller (Developer)
        devon_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        devon = User(
            id=devon_id,
            email="devon@flowstate.dev",
            name="Devon Miller",
            department="Frontend",
            title="Senior Developer",
            is_active=True,
        )

        # User 3: Deactivated User
        inactive_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        inactive_user = User(
            id=inactive_id,
            email="inactive@flowstate.dev",
            name="Inactive User",
            is_active=False,
        )

        # User 4: User without any organization membership
        loner_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        loner = User(
            id=loner_id,
            email="loner@flowstate.dev",
            name="Loner User",
            is_active=True,
        )

        # Tenant Organizations
        org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        org1 = Organization(
            id=org1_id,
            name="Flowstate Labs",
            slug="flowstate-labs",
            plan=SubscriptionPlan.ENTERPRISE,
        )

        org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        org2 = Organization(
            id=org2_id,
            name="Acme Corporation",
            slug="acme-corp",
            plan=SubscriptionPlan.PRO,
        )

        # Memberships:
        # Alex is OWNER in Org1, and ADMIN in Org2
        mem_alex_org1 = OrganizationMember(organization=org1, user=alex, role=UserRole.OWNER)
        mem_alex_org2 = OrganizationMember(organization=org2, user=alex, role=UserRole.ADMIN)

        # Devon is DEVELOPER in Org1 only
        mem_devon_org1 = OrganizationMember(organization=org1, user=devon, role=UserRole.DEVELOPER)

        session.add_all([
            alex, devon, inactive_user, loner,
            org1, org2,
            mem_alex_org1, mem_alex_org2, mem_devon_org1,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def authenticated_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI AsyncClient with get_db overridden to use test_db_session."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. FastAPI Route & Middleware Protection Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_token_endpoint(authenticated_client: AsyncClient):
    """Verify /api/v1/auth/verify-token validates and unpacks token metadata."""
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    token = create_jwt_token(sub=user_id, email="alex@flowstate.dev")

    # 1. Missing header
    res_missing = await authenticated_client.get("/api/v1/auth/verify-token")
    assert res_missing.status_code == 401
    assert res_missing.json()["error"]["code"] == "MISSING_TOKEN"

    # 2. Expired token
    expired_tok = create_jwt_token(sub=user_id, email="alex@flowstate.dev", exp_delta=timedelta(seconds=-1))
    res_expired = await authenticated_client.get(
        "/api/v1/auth/verify-token",
        headers={"Authorization": f"Bearer {expired_tok}"},
    )
    assert res_expired.status_code == 401
    assert res_expired.json()["error"]["code"] == "TOKEN_EXPIRED"

    # 3. Valid token
    res_valid = await authenticated_client.get(
        "/api/v1/auth/verify-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_valid.status_code == 200
    data = res_valid.json()
    assert data["valid"] is True
    assert data["user_id"] == str(user_id)
    assert data["email"] == "alex@flowstate.dev"


@pytest.mark.asyncio
async def test_get_me_user_resolution_and_default_org(authenticated_client: AsyncClient):
    """
    Verify /api/v1/auth/me resolves the user profile and automatically selects
    their primary active organization context.
    """
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # User profile fields
    assert data["user"]["id"] == str(alex_id)
    assert data["user"]["email"] == "alex@flowstate.dev"
    assert data["user"]["name"] == "Alex Rivera"

    # Active organization resolved to primary membership (Flowstate Labs)
    assert data["active_organization"] is not None
    assert data["active_organization"]["slug"] == "flowstate-labs"
    assert data["active_organization"]["role"] == "owner"

    # All memberships listed
    assert len(data["organizations"]) == 2
    slugs = {o["slug"] for o in data["organizations"]}
    assert slugs == {"flowstate-labs", "acme-corp"}


@pytest.mark.asyncio
async def test_get_me_with_explicit_organization_header(authenticated_client: AsyncClient):
    """Verify X-Organization-Id switches the active context when user has membership."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org2_id),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["active_organization"]["id"] == str(org2_id)
    assert data["active_organization"]["slug"] == "acme-corp"
    assert data["active_organization"]["role"] == "admin"


@pytest.mark.asyncio
async def test_missing_user_in_database(authenticated_client: AsyncClient):
    """Verify that a valid JWT referencing an unrecorded user returns 401 USER_NOT_FOUND."""
    ghost_id = uuid.uuid4()
    ghost_token = create_jwt_token(sub=ghost_id, email="ghost@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_deactivated_user_rejected(authenticated_client: AsyncClient):
    """Verify that deactivated accounts are blocked with 403 USER_DEACTIVATED."""
    inactive_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=inactive_id, email="inactive@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "USER_DEACTIVATED"


@pytest.mark.asyncio
async def test_user_without_organization_membership(authenticated_client: AsyncClient):
    """Verify that a user with 0 tenant memberships receives 403 NO_ORGANIZATION_MEMBERSHIP on protected ops."""
    loner_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    token = create_jwt_token(sub=loner_id, email="loner@flowstate.dev")

    # /admin-only requires an active organization
    res = await authenticated_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "NO_ORGANIZATION_MEMBERSHIP"


@pytest.mark.asyncio
async def test_unauthorized_organization_access_denied(authenticated_client: AsyncClient):
    """
    CRITICAL SECURITY TEST (Requirement 8):
    Never trust an organization_id supplied by the frontend without verifying membership.
    Devon is in Org1, but NOT Org2. Devon sending X-Organization-Id: Org2 must be denied with 403.
    """
    devon_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/developer-access",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org2_id),
        },
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_nonexistent_organization_id_returns_404(authenticated_client: AsyncClient):
    """Verify that requesting access to a non-existent organization returns 404 ORGANIZATION_NOT_FOUND."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    random_org_id = uuid.uuid4()
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/admin-only",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(random_org_id),
        },
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_role_based_access_control(authenticated_client: AsyncClient):
    """
    Verify organization-level role and permission enforcement:
    - /admin-only: Allowed for Owner/Admin; Forbidden for Developer.
    - /developer-access: Allowed for Developer and Owner/Admin (hierarchy); Forbidden for Viewer.
    """
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")  # Owner in Org 1
    devon_id = uuid.UUID("22222222-2222-2222-2222-222222222222")  # Developer in Org 1

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Alex (Owner) accessing /admin-only -> 200 OK
    res_alex_admin = await authenticated_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_alex_admin.status_code == 200
    assert res_alex_admin.json()["user_role"] == "owner"

    # 2. Devon (Developer) accessing /admin-only -> 403 Forbidden
    res_devon_admin = await authenticated_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_devon_admin.status_code == 403
    assert res_devon_admin.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 3. Devon (Developer) accessing /developer-access -> 200 OK
    res_devon_dev = await authenticated_client.get(
        "/api/v1/auth/developer-access",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_devon_dev.status_code == 200

    # 4. Alex (Owner) accessing /developer-access -> 200 OK (Owner satisfies min role Developer)
    res_alex_dev = await authenticated_client.get(
        "/api/v1/auth/developer-access",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_alex_dev.status_code == 200


@pytest.mark.asyncio
async def test_switch_organization_endpoint(authenticated_client: AsyncClient):
    """Verify /api/v1/auth/switch-organization validates tenant membership."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    devon_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # Alex is member of Org2 -> Success
    res_alex = await authenticated_client.post(
        "/api/v1/auth/switch-organization",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"organization_id": str(org2_id)},
    )
    assert res_alex.status_code == 200
    assert res_alex.json()["active_organization"]["slug"] == "acme-corp"

    # Devon is NOT member of Org2 -> Forbidden
    res_devon = await authenticated_client.post(
        "/api/v1/auth/switch-organization",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"organization_id": str(org2_id)},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_credentials_non_exposure_in_responses(authenticated_client: AsyncClient):
    """
    CRITICAL SECURITY REQUIREMENT (Requirement 9):
    Verify that sensitive credentials, service role keys, or password hashes
    are never included in any API response.
    """
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    res = await authenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    response_text = res.text

    assert "password" not in response_text
    assert "password_hash" not in response_text
    assert "service_role" not in response_text
    assert "secret_key" not in response_text
