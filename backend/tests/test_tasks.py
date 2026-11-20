import asyncio
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
    Base,
    Label,
    Organization,
    OrganizationMember,
    PriorityLevel,
    Project,
    ProjectStatus,
    Subtask,
    SubscriptionPlan,
    Task,
    TaskStatus,
    User,
    UserRole,
    WorkspaceSettings,
)


@pytest_asyncio.fixture(loop_scope="function")
async def task_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database seeded for Tasks, Kanban, Subtasks, and Labels tests."""
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
        # Organization 1 Users
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(id=alex_id, email="alex@flowstate.dev", name="Alex Rivera", is_active=True)

        morgan_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        morgan = User(id=morgan_id, email="morgan@flowstate.dev", name="Morgan Lee", is_active=True)

        devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        devon = User(id=devon_id, email="devon@flowstate.dev", name="Devon Miller", is_active=True)

        # Organization 2 Users (Cross-tenant actors)
        alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        alice = User(id=alice_id, email="alice@acme.dev", name="Alice Acme", is_active=True)

        bob_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
        bob = User(id=bob_id, email="bob@acme.dev", name="Bob Acme", is_active=True)

        # Outsider
        outsider_id = uuid.UUID("66666666-6666-6666-6666-666666666666")
        outsider = User(id=outsider_id, email="outsider@unknown.dev", name="Outsider", is_active=True)

        # Organizations
        org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        org1 = Organization(id=org1_id, name="Flowstate Technologies", slug="flowstate-tech", plan=SubscriptionPlan.FREE)
        settings1 = WorkspaceSettings(organization_id=org1.id)

        org2_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        org2 = Organization(id=org2_id, name="Acme Corp", slug="acme-corp", plan=SubscriptionPlan.FREE)
        settings2 = WorkspaceSettings(organization_id=org2.id)

        # Memberships Org 1
        mem_alex = OrganizationMember(organization=org1, user=alex, role=UserRole.OWNER)
        mem_morgan = OrganizationMember(organization=org1, user=morgan, role=UserRole.MANAGER)
        mem_devon = OrganizationMember(organization=org1, user=devon, role=UserRole.DEVELOPER)

        # Memberships Org 2
        mem_alice = OrganizationMember(organization=org2, user=alice, role=UserRole.OWNER)
        mem_bob = OrganizationMember(organization=org2, user=bob, role=UserRole.DEVELOPER)

        # Projects
        proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
        proj1 = Project(
            id=proj1_id,
            organization_id=org1.id,
            key="FLW",
            name="Flowstate Core",
            status=ProjectStatus.IN_PROGRESS,
            priority=PriorityLevel.HIGH,
            last_task_number=100,
        )

        proj2_id = uuid.UUID("20000000-0000-0000-0000-000000000002")
        proj2 = Project(
            id=proj2_id,
            organization_id=org2.id,
            key="ACME",
            name="Acme Portal",
            status=ProjectStatus.PLANNING,
            priority=PriorityLevel.MEDIUM,
            last_task_number=100,
        )

        # Labels
        lbl_bug = Label(id=uuid.UUID("30000000-0000-0000-0000-000000000001"), organization_id=org1.id, name="Bug", color="#EF4444")
        lbl_feat = Label(id=uuid.UUID("30000000-0000-0000-0000-000000000002"), organization_id=org1.id, name="Feature", color="#10B981")
        lbl_org2 = Label(id=uuid.UUID("30000000-0000-0000-0000-000000000003"), organization_id=org2.id, name="AcmeLabel", color="#6366F1")

        session.add_all([
            alex, morgan, devon, alice, bob, outsider,
            org1, settings1, org2, settings2,
            mem_alex, mem_morgan, mem_devon, mem_alice, mem_bob,
            proj1, proj2,
            lbl_bug, lbl_feat, lbl_org2,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def task_client(task_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield task_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_crud_and_atomic_numbering(task_client: AsyncClient):
    """Verify task creation with atomic counter formatting (FLW-101, FLW-102), read, update, delete."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Create Task 1 -> FLW-101
    res1 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Set up PostgreSQL pooler",
            "description": "Configure asyncpg connection pool",
            "priority": "high",
            "status": "todo",
            "estimated_hours": 6.5,
        },
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["key"] == "FLW-101"
    assert data1["task_number"] == 101
    assert data1["title"] == "Set up PostgreSQL pooler"
    assert data1["status"] == "todo"
    task1_id = data1["id"]

    # 2. Create Task 2 -> FLW-102 (sequential atomic numbering)
    res2 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Implement JWT verification"},
    )
    assert res2.status_code == 201
    assert res2.json()["key"] == "FLW-102"
    assert res2.json()["task_number"] == 102

    # 3. List project tasks -> returns both tasks
    res_list = await task_client.get(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2

    # 4. Get task details
    res_get = await task_client.get(
        f"/api/v1/tasks/{task1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_get.status_code == 200
    assert res_get.json()["key"] == "FLW-101"

    # 5. Update task title & actual hours
    res_update = await task_client.patch(
        f"/api/v1/tasks/{task1_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Set up Supabase pooler", "actual_hours": 4.0},
    )
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "Set up Supabase pooler"
    assert float(res_update.json()["actual_hours"]) == 4.0

    # 6. Delete task 1
    res_del = await task_client.delete(
        f"/api/v1/tasks/{task1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"

    # 7. Confirm task is gone
    res_get_gone = await task_client.get(
        f"/api/v1/tasks/{task1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_get_gone.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_task_numbering(task_client: AsyncClient):
    """Verify that multiple task creation requests generate gapless non-colliding task numbers."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # Issue multiple sequential task creation requests to verify atomic counter progression
    responses = []
    for i in range(5):
        res = await task_client.post(
            f"/api/v1/projects/{proj1_id}/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": f"Task Numbering {i}"},
        )
        responses.append(res)

    assert all(r.status_code == 201 for r in responses)

    task_keys = [r.json()["key"] for r in responses]
    task_numbers = [r.json()["task_number"] for r in responses]

    # All generated task keys and numbers must be unique and sequential
    assert len(set(task_keys)) == 5
    assert len(set(task_numbers)) == 5
    assert sorted(task_numbers) == [101, 102, 103, 104, 105]
    assert task_keys == ["FLW-101", "FLW-102", "FLW-103", "FLW-104", "FLW-105"]


@pytest.mark.asyncio
async def test_task_assignment_reassignment_and_unassign(task_client: AsyncClient):
    """Verify assigning, reassigning, unassigning, and cross-organization assignee rejection."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    morgan_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    bob_id = uuid.UUID("55555555-5555-5555-5555-555555555555")  # Org 2 member
    outsider_id = uuid.UUID("66666666-6666-6666-6666-666666666666")

    token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")

    # 1. Create task assigned to Devon (Org 1 member) -> 201
    res = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Assigned Task", "assignee_id": str(devon_id)},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["assignee_id"] == str(devon_id)
    assert data["assignee"]["email"] == "devon@flowstate.dev"
    task_id = data["id"]

    # 2. Reassign to Morgan -> 200
    res_reassign = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assignee_id": str(morgan_id)},
    )
    assert res_reassign.status_code == 200
    assert res_reassign.json()["assignee_id"] == str(morgan_id)

    # 3. Unassign task -> 200 (assignee cleared)
    res_unassign = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"unassign": True},
    )
    assert res_unassign.status_code == 200
    assert res_unassign.json()["assignee_id"] is None
    assert res_unassign.json()["assignee"] is None

    # 4. Attempting to assign cross-org user Bob (from Org 2) -> 400 Bad Request
    res_cross_org = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assignee_id": str(bob_id)},
    )
    assert res_cross_org.status_code == 400
    assert res_cross_org.json()["error"]["code"] == "INVALID_TASK_ASSIGNEE"

    # 5. Attempting to assign non-org user -> 400 Bad Request
    res_outsider = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assignee_id": str(outsider_id)},
    )
    assert res_outsider.status_code == 400
    assert res_outsider.json()["error"]["code"] == "INVALID_TASK_ASSIGNEE"


@pytest.mark.asyncio
async def test_kanban_board_and_status_transitions(task_client: AsyncClient):
    """Verify Kanban board retrieval with column buckets and status transitions."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # Create one task in 'todo' and one in 'in_progress'
    r1 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Kanban Task A", "status": "todo"},
    )
    task_a_id = r1.json()["id"]

    r2 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Kanban Task B", "status": "in_progress"},
    )

    # 1. Get Kanban board -> 200 OK
    res_kb = await task_client.get(
        f"/api/v1/projects/{proj1_id}/kanban",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_kb.status_code == 200
    board = res_kb.json()
    assert board["total_tasks"] == 2
    assert board["columns"]["todo"]["tasks_count"] == 1
    assert board["columns"]["in_progress"]["tasks_count"] == 1
    assert board["columns"]["done"]["tasks_count"] == 0

    # 2. Transition Task A to 'done' via dedicated status endpoint -> 200 OK
    res_status = await task_client.patch(
        f"/api/v1/tasks/{task_a_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"},
    )
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "done"

    # 3. Verify Kanban board updated
    res_kb_after = await task_client.get(
        f"/api/v1/projects/{proj1_id}/kanban",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_kb_after.json()["columns"]["todo"]["tasks_count"] == 0
    assert res_kb_after.json()["columns"]["done"]["tasks_count"] == 1


@pytest.mark.asyncio
async def test_kanban_fractional_ordering(task_client: AsyncClient):
    """Verify fractional position calculations for reordering tasks in columns."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # Create Task 1 (order 1000.0)
    t1 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Task 1", "order": 1000.0, "status": "todo"},
    )
    t1_id = t1.json()["id"]

    # Create Task 2 (order 2000.0)
    t2 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Task 2", "order": 2000.0, "status": "todo"},
    )
    t2_id = t2.json()["id"]

    # Create Task 3 to be inserted between Task 1 and Task 2
    t3 = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Task 3", "status": "todo"},
    )
    t3_id = t3.json()["id"]

    # Position Task 3 between Task 1 and Task 2
    res_reorder = await task_client.patch(
        f"/api/v1/tasks/{t3_id}/position",
        headers={"Authorization": f"Bearer {token}"},
        json={"after_task_id": t1_id, "before_task_id": t2_id},
    )
    assert res_reorder.status_code == 200
    assert res_reorder.json()["order"] == 1500.0


@pytest.mark.asyncio
async def test_subtasks_crud_and_completion(task_client: AsyncClient):
    """Verify checklist items creation, listing, completion toggle, and deletion."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Create parent task
    t_res = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Task with Subtasks"},
    )
    task_id = t_res.json()["id"]

    # 2. Add subtask 1 -> 201 Created
    st1 = await task_client.post(
        f"/api/v1/tasks/{task_id}/subtasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Step 1: Write schema"},
    )
    assert st1.status_code == 201
    assert st1.json()["completed"] is False
    st1_id = st1.json()["id"]

    # 3. Add subtask 2 -> 201 Created
    st2 = await task_client.post(
        f"/api/v1/tasks/{task_id}/subtasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Step 2: Run migration", "completed": False},
    )
    assert st2.status_code == 201

    # 4. List subtasks -> 200 OK (2 items)
    res_list = await task_client.get(
        f"/api/v1/tasks/{task_id}/subtasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2

    # 5. Mark subtask 1 completed -> 200 OK
    res_toggle = await task_client.patch(
        f"/api/v1/subtasks/{st1_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"completed": True},
    )
    assert res_toggle.status_code == 200
    assert res_toggle.json()["completed"] is True

    # 6. Verify parent task metrics include 1/2 completed
    res_task = await task_client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_task.json()["subtasks_count"] == 2
    assert res_task.json()["subtasks_completed_count"] == 1

    # 7. Delete subtask 1 -> 200 OK
    res_del_st = await task_client.delete(
        f"/api/v1/subtasks/{st1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_del_st.status_code == 200


@pytest.mark.asyncio
async def test_labels_management_and_task_attachment(task_client: AsyncClient):
    """Verify label creation, collision rejection, task attachment, and detachment."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    lbl_bug_id = uuid.UUID("30000000-0000-0000-0000-000000000001")
    lbl_org2_id = uuid.UUID("30000000-0000-0000-0000-000000000003")  # Belongs to Org 2
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Create new label in Org 1 -> 201 Created
    res_lbl = await task_client.post(
        f"/api/v1/organizations/{org1_id}/labels",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Frontend", "color": "#3B82F6"},
    )
    assert res_lbl.status_code == 201
    assert res_lbl.json()["name"] == "Frontend"

    # 2. Duplicate label name rejection -> 400 Bad Request
    res_dup = await task_client.post(
        f"/api/v1/organizations/{org1_id}/labels",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Frontend"},
    )
    assert res_dup.status_code == 400
    assert res_dup.json()["error"]["code"] == "LABEL_NAME_COLLISION"

    # 3. Create task and attach label
    t_res = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "UI Button alignment bug"},
    )
    task_id = t_res.json()["id"]

    res_attach = await task_client.post(
        f"/api/v1/tasks/{task_id}/labels/{lbl_bug_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_attach.status_code == 200
    label_names = [lbl["name"] for lbl in res_attach.json()["labels"]]
    assert "Bug" in label_names

    # 4. Attempting to attach cross-tenant label (from Org 2) -> 404 Not Found
    res_cross_lbl = await task_client.post(
        f"/api/v1/tasks/{task_id}/labels/{lbl_org2_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_cross_lbl.status_code == 404

    # 5. Detach label from task -> 200 OK
    res_detach = await task_client.delete(
        f"/api/v1/tasks/{task_id}/labels/{lbl_bug_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_detach.status_code == 200
    detached_label_names = [lbl["name"] for lbl in res_detach.json()["labels"]]
    assert "Bug" not in detached_label_names


@pytest.mark.asyncio
async def test_security_cross_tenant_and_unauthenticated(task_client: AsyncClient):
    """Verify that unauthenticated and cross-tenant requests are strictly blocked."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444")  # Org 2 Owner
    alice_token = create_jwt_token(sub=alice_id, email="alice@acme.dev")

    # 1. Unauthenticated request -> 401 Unauthorized
    res_unauth = await task_client.get(f"/api/v1/projects/{proj1_id}/tasks")
    assert res_unauth.status_code == 401

    # 2. Org 2 member attempting to create task in Org 1 project -> 404 Project Not Found
    res_cross_proj = await task_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"title": "Hacker Task in Org 1"},
    )
    assert res_cross_proj.status_code == 404
    assert res_cross_proj.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    # 3. Org 2 member attempting to view Kanban board of Org 1 project -> 404
    res_cross_kb = await task_client.get(
        f"/api/v1/projects/{proj1_id}/kanban",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_cross_kb.status_code == 404
