import uuid
from datetime import date, timedelta
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
    Activity,
    Base,
    Organization,
    OrganizationMember,
    PriorityLevel,
    Project,
    ProjectStatus,
    SubscriptionPlan,
    Task,
    TaskStatus,
    Team,
    TeamMember,
    User,
    UserRole,
    WorkspaceSettings,
)


@pytest_asyncio.fixture(loop_scope="function")
async def dashboard_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database seeded for Calendar, Dashboard, and Analytics tests."""
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

    today = date.today()

    async with session_factory() as session:
        # Users
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(id=alex_id, email="alex@flowstate.dev", name="Alex Rivera", is_active=True)

        morgan_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        morgan = User(id=morgan_id, email="morgan@flowstate.dev", name="Morgan Lee", is_active=True)

        devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        devon = User(id=devon_id, email="devon@flowstate.dev", name="Devon Miller", is_active=True)

        alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        alice = User(id=alice_id, email="alice@acme.dev", name="Alice Acme", is_active=True)

        # Organizations
        org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        org1 = Organization(id=org1_id, name="Flowstate Technologies", slug="flowstate-tech", plan=SubscriptionPlan.FREE)
        settings1 = WorkspaceSettings(organization_id=org1.id)

        org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        org2 = Organization(id=org2_id, name="Acme Corp", slug="acme-corp", plan=SubscriptionPlan.FREE)
        settings2 = WorkspaceSettings(organization_id=org2.id)

        # Memberships
        mem_alex = OrganizationMember(organization=org1, user=alex, role=UserRole.OWNER)
        mem_morgan = OrganizationMember(organization=org1, user=morgan, role=UserRole.MANAGER)
        mem_devon = OrganizationMember(organization=org1, user=devon, role=UserRole.DEVELOPER)
        mem_alice = OrganizationMember(organization=org2, user=alice, role=UserRole.OWNER)

        # Teams
        team1_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
        team1 = Team(id=team1_id, organization_id=org1.id, name="Backend Team", lead_id=morgan.id)
        tm_morgan = TeamMember(team_id=team1.id, user_id=morgan.id)
        tm_devon = TeamMember(team_id=team1.id, user_id=devon.id)

        # Projects
        proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
        proj1 = Project(
            id=proj1_id,
            organization_id=org1.id,
            team_id=team1.id,
            key="FLW",
            name="Flowstate Core",
            status=ProjectStatus.IN_PROGRESS,
            priority=PriorityLevel.HIGH,
            color="#6366F1",
            start_date=today - timedelta(days=10),
            due_date=today + timedelta(days=20),
            progress=40,
            budget=50000,
            spent=15000,
            last_task_number=103,
        )

        proj2_id = uuid.UUID("10000000-0000-0000-0000-000000000002")
        proj2 = Project(
            id=proj2_id,
            organization_id=org1.id,
            key="LEG",
            name="Legacy Migration",
            status=ProjectStatus.COMPLETED,
            priority=PriorityLevel.MEDIUM,
            color="#10B981",
            start_date=today - timedelta(days=30),
            due_date=today - timedelta(days=5),
            progress=100,
            budget=20000,
            spent=19500,
            last_task_number=50,
        )

        # Tasks for Project 1
        # Task 1: Completed task assigned to Devon
        t1 = Task(
            id=uuid.UUID("50000000-0000-0000-0000-000000000001"),
            organization_id=org1.id,
            project_id=proj1.id,
            task_number=101,
            key="FLW-101",
            title="Database Architecture Setup",
            status=TaskStatus.DONE,
            priority=PriorityLevel.HIGH,
            assignee_id=devon.id,
            creator_id=alex.id,
            start_date=today - timedelta(days=8),
            due_date=today - timedelta(days=2),
            estimated_hours=10.0,
            actual_hours=8.5,
            order=1000.0,
        )

        # Task 2: In-Progress & Overdue task assigned to Devon
        t2 = Task(
            id=uuid.UUID("50000000-0000-0000-0000-000000000002"),
            organization_id=org1.id,
            project_id=proj1.id,
            task_number=102,
            key="FLW-102",
            title="Overdue API Documentation",
            status=TaskStatus.IN_PROGRESS,
            priority=PriorityLevel.URGENT,
            assignee_id=devon.id,
            creator_id=morgan.id,
            start_date=today - timedelta(days=5),
            due_date=today - timedelta(days=1),  # Yesterday (overdue!)
            estimated_hours=6.0,
            actual_hours=4.0,
            order=2000.0,
        )

        # Task 3: Upcoming deadline task assigned to Morgan
        t3 = Task(
            id=uuid.UUID("50000000-0000-0000-0000-000000000003"),
            organization_id=org1.id,
            project_id=proj1.id,
            task_number=103,
            key="FLW-103",
            title="Release 1.0 Milestone Review",
            status=TaskStatus.TODO,
            priority=PriorityLevel.MEDIUM,
            assignee_id=morgan.id,
            creator_id=alex.id,
            start_date=today,
            due_date=today + timedelta(days=3),  # Upcoming in 3 days!
            estimated_hours=4.0,
            actual_hours=0.0,
            order=3000.0,
        )

        # Activity entry
        act1 = Activity(
            id=uuid.uuid4(),
            organization_id=org1.id,
            user_id=devon.id,
            action="task_created",
            target_type="task",
            target_id=t1.id,
            target_title=t1.title,
            project_id=proj1.id,
            details={"task_key": "FLW-101"},
        )

        session.add_all([
            alex, morgan, devon, alice,
            org1, settings1, org2, settings2,
            mem_alex, mem_morgan, mem_devon, mem_alice,
            team1, tm_morgan, tm_devon,
            proj1, proj2,
            t1, t2, t3,
            act1,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def dash_client(dashboard_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield dashboard_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calendar_views_and_filters(dash_client: AsyncClient):
    """Verify month, week, and day calendar queries, daily bucket aggregations, and entity filters."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Month View -> 200 OK
    res_month = await dash_client.get(
        "/api/v1/calendar?view=month",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_month.status_code == 200
    month_data = res_month.json()
    assert month_data["view"] == "month"
    assert month_data["total_events"] >= 3
    assert month_data["overdue_tasks_count"] == 1  # FLW-102 is overdue
    assert len(month_data["days"]) >= 28

    # 2. Week View -> 200 OK
    res_week = await dash_client.get(
        "/api/v1/calendar?view=week",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_week.status_code == 200
    assert res_week.json()["view"] == "week"
    assert len(res_week.json()["days"]) == 7

    # 3. Filter by assignee Devon -> returns Devon's tasks
    res_filter = await dash_client.get(
        f"/api/v1/calendar?view=month&assignee_id={devon_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_filter.status_code == 200
    devon_events = [e for e in res_filter.json()["events"] if e["entity_type"] == "task"]
    assert all(e["assignee"]["id"] == str(devon_id) for e in devon_events)


@pytest.mark.asyncio
async def test_calendar_events_and_upcoming(dash_client: AsyncClient):
    """Verify flat events list and upcoming deadlines countdown."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Flat events list
    res_events = await dash_client.get(
        "/api/v1/calendar/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_events.status_code == 200
    events = res_events.json()
    assert len(events) >= 3
    entity_types = {e["entity_type"] for e in events}
    assert "task" in entity_types
    assert "project" in entity_types

    # 2. Upcoming deadlines (horizon = 14 days)
    res_upcoming = await dash_client.get(
        "/api/v1/calendar/upcoming?days=14",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_upcoming.status_code == 200
    upcoming = res_upcoming.json()
    assert len(upcoming) >= 1
    # FLW-103 is due in 3 days
    flw103 = next((item for item in upcoming if item["key"] == "FLW-103"), None)
    assert flw103 is not None
    assert flw103["days_remaining"] == 3
    assert flw103["is_overdue"] is False


@pytest.mark.asyncio
async def test_dashboard_overview_kpis(dash_client: AsyncClient):
    """Verify workspace-wide KPI counters calculated via SQL aggregation."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    res = await dash_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total_projects"] == 2
    assert data["active_projects"] == 1       # Flowstate Core
    assert data["completed_projects"] == 1    # Legacy Migration
    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 1       # FLW-101
    assert data["in_progress_tasks"] == 1     # FLW-102
    assert data["overdue_tasks"] == 1         # FLW-102
    assert data["upcoming_deadlines"] == 1    # FLW-103
    assert data["total_team_members"] == 3    # Alex, Morgan, Devon

    # Personal tasks for Devon (FLW-101 and FLW-102)
    my_tasks = data["my_tasks_summary"]
    assert my_tasks["total"] == 2
    assert my_tasks["completed"] == 1
    assert my_tasks["in_progress"] == 1
    assert my_tasks["overdue"] == 1


@pytest.mark.asyncio
async def test_dashboard_task_and_project_stats(dash_client: AsyncClient):
    """Verify detailed task distributions and project progress aggregations."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Task Stats
    res_tasks = await dash_client.get(
        "/api/v1/dashboard/task-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_tasks.status_code == 200
    t_stats = res_tasks.json()
    assert t_stats["total_tasks"] == 3
    assert t_stats["completed_tasks"] == 1
    assert t_stats["completion_rate"] == 33.33
    assert t_stats["tasks_by_status"]["done"] == 1
    assert t_stats["tasks_by_status"]["in_progress"] == 1
    assert t_stats["tasks_by_status"]["todo"] == 1
    assert t_stats["total_estimated_hours"] == 20.0  # 10 + 6 + 4
    assert t_stats["total_actual_hours"] == 12.5     # 8.5 + 4.0 + 0

    # 2. Project Stats
    res_proj = await dash_client.get(
        "/api/v1/dashboard/project-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_proj.status_code == 200
    p_stats = res_proj.json()
    assert p_stats["total_projects"] == 2
    flw_proj = next(p for p in p_stats["projects"] if p["key"] == "FLW")
    assert flw_proj["total_tasks"] == 3
    assert flw_proj["completed_tasks"] == 1
    assert flw_proj["overdue_tasks"] == 1
    assert flw_proj["calculated_progress"] == 33  # 1/3 rounded


@pytest.mark.asyncio
async def test_dashboard_team_stats_and_workload(dash_client: AsyncClient):
    """Verify workload distribution percentages across organization members."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    res = await dash_client.get(
        "/api/v1/dashboard/team-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    team_stats = res.json()
    assert team_stats["total_members"] == 3
    assert team_stats["active_tasks_count"] == 2  # FLW-102 and FLW-103

    members = team_stats["members"]
    devon_m = next(m for m in members if m["user_id"] == str(devon_id))
    assert devon_m["assigned_tasks_count"] == 2
    assert devon_m["completed_tasks_count"] == 1
    assert devon_m["pending_tasks_count"] == 1
    assert devon_m["overdue_tasks_count"] == 1
    assert devon_m["workload_percentage"] == 50.0  # 1 pending out of 2 active tasks = 50%


@pytest.mark.asyncio
async def test_project_and_team_analytics_deep_dives(dash_client: AsyncClient):
    """Verify single project and single team deep-dive analytics."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    team1_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Project Analytics
    res_p_ana = await dash_client.get(
        f"/api/v1/projects/{proj1_id}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_p_ana.status_code == 200
    p_ana = res_p_ana.json()
    assert p_ana["project_key"] == "FLW"
    assert p_ana["total_tasks"] == 3
    assert p_ana["completed_tasks"] == 1
    assert p_ana["pending_tasks"] == 2
    assert p_ana["overdue_tasks_count"] == 1
    assert p_ana["completion_percentage"] == 33.33
    assert p_ana["days_remaining"] == 20
    assert p_ana["is_overdue"] is False

    # 2. Team Analytics
    res_t_ana = await dash_client.get(
        f"/api/v1/teams/{team1_id}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_t_ana.status_code == 200
    t_ana = res_t_ana.json()
    assert t_ana["team_name"] == "Backend Team"
    assert t_ana["member_count"] == 2
    assert len(t_ana["members"]) == 2


@pytest.mark.asyncio
async def test_dashboard_recent_activity(dash_client: AsyncClient):
    """Verify workspace recent activity feed retrieval."""
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    res = await dash_client.get(
        "/api/v1/dashboard/recent-activity?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    acts = res.json()
    assert acts["total"] >= 1
    assert len(acts["items"]) >= 1
    assert acts["items"][0]["action"] == "task_created"


@pytest.mark.asyncio
async def test_security_cross_tenant_analytics(dash_client: AsyncClient):
    """Verify cross-tenant security: Org 2 cannot read Org 1 project or team analytics."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    team1_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
    alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444")  # Org 2 Owner
    alice_token = create_jwt_token(sub=alice_id, email="alice@acme.dev")

    # 1. Cross-tenant project analytics -> 404
    res1 = await dash_client.get(
        f"/api/v1/projects/{proj1_id}/analytics",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res1.status_code == 404

    # 2. Cross-tenant team analytics -> 404
    res2 = await dash_client.get(
        f"/api/v1/teams/{team1_id}/analytics",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res2.status_code == 404

    # 3. Unauthenticated overview -> 401
    res3 = await dash_client.get("/api/v1/dashboard/overview")
    assert res3.status_code == 401
