import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings as app_settings
from app.core.security import create_jwt_token
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


@pytest_asyncio.fixture(loop_scope="function")
async def org_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory SQLite database seeded for organization API testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    @event.listens_for(test_engine.sync_engine, "connect")
    def attach_auth_schema(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        # User 1: Alex (Owner)
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(id=alex_id, email="alex@flowstate.dev", name="Alex Rivera", is_active=True)

        # User 2: Sarah (Admin)
        sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        sarah = User(id=sarah_id, email="sarah@flowstate.dev", name="Sarah Chen", is_active=True)

        # User 3: Devon (Developer)
        devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        devon = User(id=devon_id, email="devon@flowstate.dev", name="Devon Miller", is_active=True)

        # User 4: Outsider (Non-member)
        outsider_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        outsider = User(id=outsider_id, email="outsider@flowstate.dev", name="Outsider User", is_active=True)

        # Base Organization
        org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        org1 = Organization(id=org1_id, name="Flowstate Technologies", slug="flowstate-tech", plan=SubscriptionPlan.PRO)

        # Default workspace settings
        settings = WorkspaceSettings(
            organization_id=org1.id,
            currency="USD",
            timezone="America/New_York",
            working_days=[1, 2, 3, 4, 5],
            accent_color="#6366F1",
            theme="dark",
        )

        # Memberships
        mem_alex = OrganizationMember(organization=org1, user=alex, role=UserRole.OWNER)
        mem_sarah = OrganizationMember(organization=org1, user=sarah, role=UserRole.ADMIN)
        mem_devon = OrganizationMember(organization=org1, user=devon, role=UserRole.DEVELOPER)

        session.add_all([alex, sarah, devon, outsider, org1, settings, mem_alex, mem_sarah, mem_devon])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def org_client(org_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield org_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_organization(org_client: AsyncClient):
    """Verify organization creation, slug generation, default settings, and Owner assignment."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    res = await org_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Ventures",
            "slug": "acme-ventures",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Acme Ventures"
    assert data["slug"] == "acme-ventures"
    assert data["plan"] == "free"
    assert data["current_user_role"] == "owner"
    assert data["members_count"] == 1
    assert data["settings"]["currency"] == "USD"
    assert data["settings"]["timezone"] == "UTC"

    # Duplicate slug must be rejected
    res_dup = await org_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Duplicate Ventures", "slug": "acme-ventures"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "SLUG_COLLISION"


@pytest.mark.asyncio
async def test_list_and_get_organizations(org_client: AsyncClient):
    """Verify listing and retrieving organization details with membership protection."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    outsider_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    outsider_token = create_jwt_token(sub=outsider_id, email="outsider@flowstate.dev")

    # 1. Alex lists organizations -> includes Flowstate Technologies
    res_list = await org_client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data) == 1
    assert data[0]["name"] == "Flowstate Technologies"
    assert data[0]["current_user_role"] == "owner"
    assert data[0]["members_count"] == 3

    # 2. Alex gets details -> 200 OK
    res_get = await org_client.get(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_get.status_code == 200
    assert res_get.json()["slug"] == "flowstate-tech"

    # 3. Outsider gets details -> 403 Forbidden
    res_forbidden = await org_client.get(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_update_organization(org_client: AsyncClient):
    """Verify organization updating permissions (Owner/Admin allowed; Developer denied)."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Developer updating name -> 403 Forbidden
    res_devon = await org_client.patch(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"name": "Devon Hacked Tech"},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 2. Admin updating name -> 200 OK
    res_sarah = await org_client.patch(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"name": "Flowstate Labs Global"},
    )
    assert res_sarah.status_code == 200
    assert res_sarah.json()["name"] == "Flowstate Labs Global"

    # 3. Plan update via standard PATCH is rejected (managed exclusively by billing processes)
    res_sarah_plan = await org_client.patch(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"plan": "enterprise"},
    )
    assert res_sarah_plan.status_code == 403
    assert res_sarah_plan.json()["error"]["code"] == "PLAN_UPDATE_RESTRICTED"

    # Even Owner cannot directly update plan via standard PATCH
    res_alex_plan = await org_client.patch(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"plan": "enterprise"},
    )
    assert res_alex_plan.status_code == 403
    assert res_alex_plan.json()["error"]["code"] == "PLAN_UPDATE_RESTRICTED"


@pytest.mark.asyncio
async def test_add_and_list_members(org_client: AsyncClient):
    """Verify adding members, duplicate guards, and role assignment boundaries."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    outsider_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")

    # 1. Admin adds Outsider as Developer by email -> 201 Created
    res_add = await org_client.post(
        f"/api/v1/organizations/{org1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"email": "outsider@flowstate.dev", "role": "developer"},
    )
    assert res_add.status_code == 201
    assert res_add.json()["role"] == "developer"
    assert res_add.json()["user_id"] == str(outsider_id)

    # 2. Duplicate membership attempt -> 400 Bad Request
    res_dup = await org_client.post(
        f"/api/v1/organizations/{org1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"user_id": str(outsider_id), "role": "designer"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"

    # 3. Admin attempting to add an Owner -> 403 Forbidden
    res_owner_denied = await org_client.post(
        f"/api/v1/organizations/{org1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"email": "nonexistent@flowstate.dev", "role": "owner"},
    )
    assert res_owner_denied.status_code == 403
    assert res_owner_denied.json()["error"]["code"] == "CANNOT_ASSIGN_OWNER_ROLE"

    # 4. List members -> now contains 4 members
    res_list = await org_client.get(
        f"/api/v1/organizations/{org1_id}/members",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) == 4


@pytest.mark.asyncio
async def test_update_member_role_and_sole_owner_guard(org_client: AsyncClient):
    """Verify role update hierarchy and sole Owner demotion prevention."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")

    # 1. Admin updates Developer to Manager -> 200 OK
    res_up = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/members/{devon_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"role": "manager"},
    )
    assert res_up.status_code == 200
    assert res_up.json()["role"] == "manager"

    # 2. Admin attempting to demote the Owner -> 403 Forbidden
    res_admin_demotes_owner = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/members/{alex_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"role": "developer"},
    )
    assert res_admin_demotes_owner.status_code == 403
    assert res_admin_demotes_owner.json()["error"]["code"] == "CANNOT_MODIFY_OWNER"

    # 3. Sole Owner attempting to demote themselves -> 400 Bad Request
    res_self_demote = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/members/{alex_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"role": "admin"},
    )
    assert res_self_demote.status_code == 400
    assert res_self_demote.json()["error"]["code"] == "SOLE_OWNER_DEMOTION_FORBIDDEN"

    # 4. Owner promotes Sarah to Owner -> 200 OK
    res_promote_sarah = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/members/{sarah_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"role": "owner"},
    )
    assert res_promote_sarah.status_code == 200
    assert res_promote_sarah.json()["role"] == "owner"

    # 5. Now that there are two Owners, Alex can demote himself to Admin -> 200 OK
    res_alex_demotes_now = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/members/{alex_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"role": "admin"},
    )
    assert res_alex_demotes_now.status_code == 200
    assert res_alex_demotes_now.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_remove_member_rules(org_client: AsyncClient):
    """Verify removal permissions: self-leave, admin expelling, and sole-owner guard."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Sole owner attempting to leave -> 400 Bad Request
    res_owner_leave = await org_client.delete(
        f"/api/v1/organizations/{org1_id}/members/{alex_id}",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    assert res_owner_leave.status_code == 400
    assert res_owner_leave.json()["error"]["code"] == "SOLE_OWNER_LEAVE_FORBIDDEN"

    # 2. Admin attempting to remove the Owner -> 403 Forbidden
    res_admin_removes_owner = await org_client.delete(
        f"/api/v1/organizations/{org1_id}/members/{alex_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    assert res_admin_removes_owner.status_code == 403
    assert res_admin_removes_owner.json()["error"]["code"] == "CANNOT_REMOVE_PRIVILEGED_MEMBER"

    # 3. Developer leaves the organization voluntarily -> 200 OK
    res_devon_leave = await org_client.delete(
        f"/api/v1/organizations/{org1_id}/members/{devon_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_devon_leave.status_code == 200

    # 4. Confirm Devon is no longer a member
    res_list = await org_client.get(
        f"/api/v1/organizations/{org1_id}/members",
        headers={"Authorization": f"Bearer {alex_token}"},
    )
    member_ids = [m["user_id"] for m in res_list.json()]
    assert str(devon_id) not in member_ids


@pytest.mark.asyncio
async def test_workspace_settings_endpoints(org_client: AsyncClient):
    """Verify getting and updating workspace settings with validation and role protection."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    alex_token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Devon (Developer) reads settings -> 200 OK
    res_get = await org_client.get(
        f"/api/v1/organizations/{org1_id}/settings",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_get.status_code == 200
    assert res_get.json()["currency"] == "USD"
    assert res_get.json()["accent_color"] == "#6366F1"

    # 2. Devon attempts to update settings -> 403 Forbidden
    res_devon_patch = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/settings",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"currency": "EUR"},
    )
    assert res_devon_patch.status_code == 403
    assert res_devon_patch.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 3. Owner updates settings -> 200 OK
    res_alex_patch = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/settings",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={
            "currency": "EUR",
            "timezone": "Europe/Berlin",
            "working_days": [1, 2, 3, 4],
            "notifications_email": False,
            "notifications_desktop": False,
            "accent_color": "#10B981",
            "theme": "system",
        },
    )
    assert res_alex_patch.status_code == 200
    data = res_alex_patch.json()
    assert data["currency"] == "EUR"
    assert data["timezone"] == "Europe/Berlin"
    assert data["working_days"] == [1, 2, 3, 4]
    assert data["notifications_email"] is False
    assert data["notifications_desktop"] is False
    assert data["accent_color"] == "#10B981"
    assert data["theme"] == "system"

    # 4. Invalid working days validation (must be between 1 and 7) -> 422
    res_invalid_days = await org_client.patch(
        f"/api/v1/organizations/{org1_id}/settings",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"working_days": [0, 8]},
    )
    assert res_invalid_days.status_code == 422


@pytest.mark.asyncio
async def test_unauthorized_paid_plan_assignment_and_billing(org_client: AsyncClient):
    """Verify that clients cannot self-assign paid plans and only trusted billing can upgrade."""
    alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    token = create_jwt_token(sub=alex_id, email="alex@flowstate.dev")

    # 1. Attempting to create organization with 'pro' plan is rejected
    res_pro = await org_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Hacker Pro Org", "plan": "pro"},
    )
    assert res_pro.status_code == 400
    assert res_pro.json()["error"]["code"] == "UNAUTHORIZED_PAID_PLAN_ASSIGNMENT"

    # 2. Attempting to create organization with 'enterprise' plan is rejected
    res_ent = await org_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Hacker Ent Org", "plan": "enterprise"},
    )
    assert res_ent.status_code == 400
    assert res_ent.json()["error"]["code"] == "UNAUTHORIZED_PAID_PLAN_ASSIGNMENT"

    # 3. Creating organization with default / free succeeds with 'free' plan
    res_free = await org_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Legit Free Org", "plan": "free"},
    )
    assert res_free.status_code == 201
    assert res_free.json()["plan"] == "free"

    # 4. Standard PATCH attempting plan upgrade is rejected even for Owner
    res_patch_plan = await org_client.patch(
        f"/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan": "enterprise"},
    )
    assert res_patch_plan.status_code == 403
    assert res_patch_plan.json()["error"]["code"] == "PLAN_UPDATE_RESTRICTED"

    # 5. Billing webhook without secret is rejected
    res_bill_no_secret = await org_client.post(
        f"/api/v1/organizations/{org1_id}/billing/plan",
        json={"plan": "enterprise"},
    )
    assert res_bill_no_secret.status_code == 403
    assert res_bill_no_secret.json()["error"]["code"] == "INVALID_BILLING_CREDENTIALS"

    # 6. Billing webhook with valid secret succeeds in updating subscription
    billing_secret = app_settings.SUPABASE_SERVICE_ROLE_KEY or app_settings.SECRET_KEY
    res_bill_success = await org_client.post(
        f"/api/v1/organizations/{org1_id}/billing/plan",
        headers={"X-Billing-Secret": billing_secret},
        json={"plan": "enterprise"},
    )
    assert res_bill_success.status_code == 200
    assert res_bill_success.json()["plan"] == "enterprise"
