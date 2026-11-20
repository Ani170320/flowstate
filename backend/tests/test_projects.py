import uuid
from datetime import date, timedelta
from decimal import Decimal
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
    PriorityLevel,
    Project,
    ProjectMember,
    ProjectStatus,
    SubscriptionPlan,
    Team,
    User,
    UserRole,
    WorkspaceSettings,
)


@pytest_asyncio.fixture(loop_scope="function")
async def project_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database seeded for Project API tests."""
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

        # Team
        team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        team1 = Team(id=team1_id, organization_id=org1.id, name="Engineering", lead_id=morgan.id)

        # Base Project
        proj1_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        proj1 = Project(
            id=proj1_id,
            organization_id=org1.id,
            team_id=team1.id,
            key="FLW",
            name="Flowstate Core Platform",
            description="High-concurrency backend services",
            status=ProjectStatus.IN_PROGRESS,
            priority=PriorityLevel.HIGH,
            manager_id=morgan.id,
            progress=25,
            budget=Decimal("50000.00"),
            spent=Decimal("12000.00"),
            last_task_number=100,
        )

        pm_morgan = ProjectMember(project_id=proj1.id, user_id=morgan.id)
        pm_devon = ProjectMember(project_id=proj1.id, user_id=devon.id)

        session.add_all([
            alex, sarah, morgan, devon, outsider,
            org1, settings,
            mem_alex, mem_sarah, mem_morgan, mem_devon,
            team1, proj1, pm_morgan, pm_devon,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def project_client(project_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield project_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project(project_client: AsyncClient):
    """Verify project creation, key auto-generation, key collision guard, and RBAC."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Developer cannot create project -> 403 Forbidden
    res_devon = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"name": "Devon Project"},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 2. Manager creates project with custom key -> 201 Created
    today = date.today()
    res_morgan = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={
            "name": "Mobile iOS App",
            "key": "IOS",
            "description": "Native Swift application",
            "team_id": str(team1_id),
            "manager_id": str(morgan_id),
            "status": "planning",
            "priority": "urgent",
            "color": "#10B981",
            "start_date": today.isoformat(),
            "due_date": (today + timedelta(days=90)).isoformat(),
            "budget": 75000.00,
            "member_ids": [str(devon_id)],
        },
    )
    assert res_morgan.status_code == 201
    data = res_morgan.json()
    assert data["name"] == "Mobile iOS App"
    assert data["key"] == "IOS"
    assert data["last_task_number"] == 100
    assert data["members_count"] == 2

    # 3. Duplicate key in same org is rejected -> 400 Bad Request
    res_dup = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"name": "Another iOS App", "key": "IOS"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "PROJECT_KEY_COLLISION"

    # 4. Auto-generated key when omitted
    res_auto = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"name": "Design Tokens"},
    )
    assert res_auto.status_code == 201
    assert len(res_auto.json()["key"]) >= 3

    # 5. Invalid manager (non-org user) -> 400 Bad Request
    res_inv_mgr = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={"name": "Security Audit", "manager_id": str(outsider_id)},
    )
    assert res_inv_mgr.status_code == 400
    assert res_inv_mgr.json()["error"]["code"] == "INVALID_PROJECT_MANAGER"

    # 6. Invalid date range (due date < start date) -> 422
    res_invalid_dates = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={
            "name": "Time Machine",
            "start_date": today.isoformat(),
            "due_date": (today - timedelta(days=5)).isoformat(),
        },
    )
    assert res_invalid_dates.status_code == 422


@pytest.mark.asyncio
async def test_list_and_filter_projects(project_client: AsyncClient):
    """Verify listing and filtering projects by team, status, priority."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    team1_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")
    outsider_token = create_jwt_token(sub=outsider_id, email="outsider@flowstate.dev")

    # 1. Member lists projects -> 200 OK
    res_list = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data) >= 1
    assert data[0]["key"] == "FLW"

    # 2. Filter by status 'in_progress' -> 200 OK
    res_filter_status = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects?status=in_progress",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_filter_status.status_code == 200
    assert all(p["status"] == "in_progress" for p in res_filter_status.json())

    # 3. Filter by team_id -> 200 OK
    res_filter_team = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects?team_id={team1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_filter_team.status_code == 200
    assert len(res_filter_team.json()) >= 1

    # 4. Outsider access denied -> 403 Forbidden
    res_outsider = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert res_outsider.status_code == 403


@pytest.mark.asyncio
async def test_get_and_update_project(project_client: AsyncClient):
    """Verify retrieving project details and updating progress, priority, budget."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    proj1_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Get project details -> 200 OK with members
    res_get = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["name"] == "Flowstate Core Platform"
    assert data["manager"]["email"] == "morgan@flowstate.dev"
    assert len(data["members"]) == 2

    # 2. Developer updating project -> 403 Forbidden
    res_devon = await project_client.patch(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"name": "Devon Hacked Project"},
    )
    assert res_devon.status_code == 403
    assert res_devon.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 3. Project Manager (Morgan) updates progress, budget, status -> 200 OK
    res_mgr = await project_client.patch(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {morgan_token}"},
        json={
            "progress": 65,
            "status": "in_review",
            "spent": 25000.00,
        },
    )
    assert res_mgr.status_code == 200
    updated = res_mgr.json()
    assert updated["progress"] == 65
    assert updated["status"] == "in_review"
    assert float(updated["spent"]) == 25000.00


@pytest.mark.asyncio
async def test_delete_project_permissions(project_client: AsyncClient):
    """Verify project deletion rules: Admin/Owner allowed; Manager denied."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    proj1_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    morgan_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")

    # 1. Manager attempting to delete project -> 403 Forbidden
    res_morgan = await project_client.delete(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {morgan_token}"},
    )
    assert res_morgan.status_code == 403

    # 2. Admin deletes project -> 200 OK
    res_admin = await project_client.delete(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "success"

    # 3. Confirm project is gone
    res_get = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_project_members_lifecycle(project_client: AsyncClient):
    """Verify assigning and removing project members, duplicate protection, and self-leave."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    proj1_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    sarah_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    outsider_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    sarah_token = create_jwt_token(sub=sarah_id, email="sarah@flowstate.dev")
    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Admin assigns Sarah (org member) to project -> 201 Created
    res_add = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"email": "sarah@flowstate.dev"},
    )
    assert res_add.status_code == 201
    assert res_add.json()["user_id"] == str(sarah_id)

    # 2. Duplicate assignment is rejected -> 400 Bad Request
    res_dup = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"user_id": str(sarah_id)},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "MEMBER_ALREADY_IN_PROJECT"

    # 3. Non-org user assignment is rejected -> 400 Bad Request
    res_not_org = await project_client.post(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
        json={"user_id": str(outsider_id)},
    )
    assert res_not_org.status_code == 400
    assert res_not_org.json()["error"]["code"] == "USER_NOT_ORGANIZATION_MEMBER"

    # 4. Devon voluntarily leaves project -> 200 OK
    res_leave = await project_client.delete(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}/members/{devon_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_leave.status_code == 200

    # 5. Confirm Devon is no longer in project members list
    res_members = await project_client.get(
        f"/api/v1/organizations/{org1_id}/projects/{proj1_id}/members",
        headers={"Authorization": f"Bearer {sarah_token}"},
    )
    member_user_ids = [m["user_id"] for m in res_members.json()]
    assert str(devon_id) not in member_user_ids
