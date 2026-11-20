import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_jwt_token
from app.dependencies.database import get_db
from app.main import app
from app.models import (
    Base,
    Organization,
    OrganizationMember,
    SubscriptionPlan,
    Team,
    TeamMember,
    User,
    UserRole,
    WorkspaceSettings,
)


@pytest_asyncio.fixture(loop_scope="function")
async def team_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database seeded for Team API tests."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

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
        # Users
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(id=alex_id, email="alex@flowstate.dev", name="Alex Rivera", is_active=True)

        sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        sarah = User(id=sarah_id, email="sarah@flowstate.dev", name="Sarah Chen", is_active=True)

        morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        morgan = User(id=morgan_id, email="morgan@flowstate.dev", name="Morgan Lee", is_active=True)

        devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        devon = User(id=devon_id, email="devon@flowstate.dev", name="Devon Miller", is_active=True)

        outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
        outsider = User(id=outsider_id, email="outsider@flowstate.dev", name="Outsider User", is_active=True)

        # Organization
        org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        org1 = Organization(id=org1_id, name="Flowstate Technologies", slug="flowstate-tech", plan=SubscriptionPlan.FREE)

        settings = WorkspaceSettings(organization_id=org1.id)

        # Memberships
        mem_alex = OrganizationMember(organization=org1, user=alex, role=UserRole.OWNER)
        mem_sarah = OrganizationMember(organization=org1, user=sarah, role=UserRole.ADMIN)
        mem_morgan = OrganizationMember(organization=org1, user=morgan, role=UserRole.MANAGER)
        mem_devon = OrganizationMember(organization=org1, user=devon, role=UserRole.DEVELOPER)

        # Initial Team
        team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        team1 = Team(id=team1_id, organization_id=org1.id, name="Core Engineering", description="Platform architecture", lead_id=morgan.id)
        tm_morgan = TeamMember(team_id=team1.id, user_id=morgan.id)
        tm_devon = TeamMember(team_id=team1.id, user_id=devon.id)

        session.add_all([
            alex, sarah, morgan, devon, outsider,
            org1, settings,
            mem_alex, mem_sarah, mem_morgan, mem_devon,
            team1, tm_morgan, tm_devon,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def team_client(team_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield team_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_team(team_client: AsyncClient):
    """Verify team creation, duplicate name protection, and RBAC enforcement."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Developer cannot create team -> 403 Forbidden
    res_devon = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"name": "Devon Rogue Team"},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 2. Manager creates team -> 201 Created
    res_morgan = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={
            "name": "Design Systems",
            "description": "Component libraries and design tokens",
            "lead_id": str(morgan_id),
            "member_ids": [str(devon_id)],
        },
    )
    assert res_morgan.status_code == 201
    data = res_morgan.json()
    assert data["name"] == "Design Systems"
    assert data["lead_id"] == str(morgan_id)
    assert data["members_count"] == 2

    # 3. Duplicate name in same org is rejected -> 400 Bad Request
    res_dup = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"name": "Design Systems"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "TEAM_NAME_COLLISION"

    # 4. Non-organization member as lead is rejected -> 400 Bad Request
    res_invalid_lead = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"name": "Security Ops", "lead_id": str(outsider_id)},
    )
    assert res_invalid_lead.status_code == 400
    assert res_invalid_lead.json()["error"]["code"] == "INVALID_TEAM_LEAD"


@pytest.mark.asyncio
async def test_list_and_get_teams(team_client: AsyncClient):
    """Verify listing and retrieving team details with member authorization."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")
    outsider_token = create_jwt_token(sub=outsider_id, email="outsider@flowstate.dev")

    # 1. Organization member lists teams -> 200 OK
    res_list = await team_client.get(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Core Engineering"
    assert data[0]["members_count"] == 2

    # 2. Member gets team details -> 200 OK with nested members
    res_get = await team_client.get(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["name"] == "Core Engineering"
    assert len(detail["members"]) == 2

    # 3. Outsider access is forbidden -> 403 Forbidden
    res_outsider = await team_client.get(
        f"/api/v1/organizations/{org1_id}/teams",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert res_outsider.status_code == 403


@pytest.mark.asyncio
async def test_update_team_permissions(team_client: AsyncClient):
    """Verify team update permissions: Manager/Lead allowed; Developer denied."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Developer updating team -> 403 Forbidden
    res_devon = await team_client.patch(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"name": "Devon Engineering"},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 2. Team Lead (Morgan) updates description -> 200 OK
    res_lead = await team_client.patch(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"description": "Updated platform architecture description"},
    )
    assert res_lead.status_code == 200
    assert res_lead.json()["description"] == "Updated platform architecture description"


@pytest.mark.asyncio
async def test_delete_team_permissions(team_client: AsyncClient):
    """Verify team deletion rules: Admin/Owner allowed; Manager denied."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")

    # 1. Manager attempting to delete team -> 403 Forbidden
    res_morgan = await team_client.delete(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {morgan_token}"},
    )
    assert res_morgan.status_code == 403

    # 2. Admin deleting team -> 200 OK
    res_admin = await team_client.delete(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"

    # 3. Verify team is gone
    res_get = await team_client.get(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_team_members_enrollment_and_removal(team_client: AsyncClient):
    """Verify adding/removing members, duplicate protection, and self-leave."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Admin adds Sarah (org member) to team -> 201 Created
    res_add = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"email": "sarah@flowstate.dev"},
    )
    assert res_add.status_code == 201
    assert res_add.json()["user_id"] == str(sarah_id)

    # 2. Duplicate addition is rejected -> 400 Bad Request
    res_dup = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"user_id": str(sarah_id)},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "MEMBER_ALREADY_IN_TEAM"

    # 3. Adding user who is not an org member is rejected -> 400 Bad Request
    res_not_org = await team_client.post(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"user_id": str(outsider_id)},
    )
    assert res_not_org.status_code == 400
    assert res_not_org.json()["error"]["code"] == "USER_NOT_ORGANIZATION_MEMBER"

    # 4. Devon voluntarily leaves team -> 200 OK
    res_leave = await team_client.delete(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}/members/{devon_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_leave.status_code == 200

    # 5. Confirm Devon is no longer in team members list
    res_members = await team_client.get(
        f"/api/v1/organizations/{org1_id}/teams/{team1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    member_user_ids = [m["user_id"] for m in res_members.json()]
    assert str(devon_id) not in member_user_ids
