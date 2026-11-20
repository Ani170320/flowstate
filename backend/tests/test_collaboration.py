import io
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
    Label,
    Organization,
    OrganizationMember,
    PriorityLevel,
    Project,
    ProjectStatus,
    SubscriptionPlan,
    Task,
    TaskStatus,
    User,
    UserRole,
    WorkspaceSettings,
)
from app.models.enums import NotificationType


@pytest_asyncio.fixture(loop_scope="function")
async def collab_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database seeded for Phase 5 Collaboration tests."""
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
        # Org 1 Users
        alex_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        alex = User(id=alex_id, email="alex@flowstate.dev", name="Alex Rivera", is_active=True)

        morgan_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        morgan = User(id=morgan_id, email="morgan@flowstate.dev", name="Morgan Lee", is_active=True)

        devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        devon = User(id=devon_id, email="devon@flowstate.dev", name="Devon Miller", is_active=True)

        sam_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
        sam = User(id=sam_id, email="sam@flowstate.dev", name="Sam Taylor", is_active=True)

        # Org 2 Users
        alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        alice = User(id=alice_id, email="alice@acme.dev", name="Alice Acme", is_active=True)

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
        mem_sam = OrganizationMember(organization=org1, user=sam, role=UserRole.DEVELOPER)

        # Memberships Org 2
        mem_alice = OrganizationMember(organization=org2, user=alice, role=UserRole.OWNER)

        # Project 1
        proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
        proj1 = Project(
            id=proj1_id,
            organization_id=org1.id,
            key="FLW",
            name="Flowstate Core",
            status=ProjectStatus.IN_PROGRESS,
            priority=PriorityLevel.HIGH,
            last_task_number=101,
        )

        # Task 1
        task1_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
        task1 = Task(
            id=task1_id,
            organization_id=org1.id,
            project_id=proj1.id,
            task_number=101,
            key="FLW-101",
            title="Implement Collaboration APIs",
            description="Build Comments, Attachments, Activities, and Notifications",
            status=TaskStatus.IN_PROGRESS,
            priority=PriorityLevel.HIGH,
            assignee_id=devon.id,
            creator_id=alex.id,
            order=1000.0,
        )

        session.add_all([
            alex, morgan, devon, sam, alice,
            org1, settings1, org2, settings2,
            mem_alex, mem_morgan, mem_devon, mem_sam, mem_alice,
            proj1, task1,
        ])
        await session.commit()

        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def collab_client(collab_test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield collab_test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_comments_crud_and_permissions(collab_client: AsyncClient):
    """Verify posting comments, author editing, role-based deletions, and list pagination."""
    task1_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")  # Task assignee
    sam_id = uuid.UUID("77777777-7777-7777-7777-777777777777")    # Fellow developer
    morgan_id = uuid.UUID("22222222-2222-2222-2222-222222222222") # Manager

    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")
    sam_token = create_jwt_token(sub=sam_id, email="sam@flowstate.dev")
    morgan_token = create_jwt_token(sub=morgan_id, email="morgan@flowstate.dev")

    # 1. Devon posts a comment -> 201 Created
    res1 = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/comments",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"content": "Initial PR for collaboration schemas is ready."},
    )
    assert res1.status_code == 201
    comment1 = res1.json()
    assert comment1["content"] == "Initial PR for collaboration schemas is ready."
    assert comment1["author"]["email"] == "devon@flowstate.dev"
    c1_id = comment1["id"]

    # 2. Sam lists comments -> 200 OK (total 1)
    res_list = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/comments?limit=10&offset=0",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total"] == 1
    assert len(data_list["items"]) == 1

    # 3. Author (Devon) edits comment -> 200 OK
    res_edit = await collab_client.patch(
        f"/api/v1/comments/{c1_id}",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"content": "Updated: PR has been reviewed and tested."},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["content"] == "Updated: PR has been reviewed and tested."

    # 4. Sam (non-author developer) attempts to edit Devon's comment -> 403 Forbidden
    res_unauth_edit = await collab_client.patch(
        f"/api/v1/comments/{c1_id}",
        headers={"Authorization": f"Bearer {sam_token}"},
        json={"content": "Malicious edit attempt"},
    )
    assert res_unauth_edit.status_code == 403

    # 5. Sam attempts to delete Devon's comment -> 403 Forbidden
    res_unauth_del = await collab_client.delete(
        f"/api/v1/comments/{c1_id}",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_unauth_del.status_code == 403

    # 6. Manager (Morgan) deletes comment -> 200 OK
    res_mgr_del = await collab_client.delete(
        f"/api/v1/comments/{c1_id}",
        headers={"Authorization": f"Bearer {morgan_token}"},
    )
    assert res_mgr_del.status_code == 200

    # 7. Confirm list is empty
    res_list_after = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/comments",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_list_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_attachments_upload_and_storage_lifecycle(collab_client: AsyncClient):
    """Verify file uploads, validation of empty/invalid files, listing, and storage deletion."""
    task1_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    sam_id = uuid.UUID("77777777-7777-7777-7777-777777777777")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")
    sam_token = create_jwt_token(sub=sam_id, email="sam@flowstate.dev")

    # 1. Valid PDF upload -> 201 Created
    pdf_content = b"%PDF-1.4 Mock Binary PDF Content"
    res_upload = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("architecture.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert res_upload.status_code == 201
    att_data = res_upload.json()
    assert att_data["name"] == "architecture.pdf"
    assert att_data["mime_type"] == "application/pdf"
    assert att_data["file_size"] == len(pdf_content)
    assert "org_" in att_data["storage_path"]
    assert att_data["download_url"] is not None
    att_id = att_data["id"]

    # 2. Reject empty file (0 bytes) -> 400 Bad Request
    res_empty = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert res_empty.status_code == 400
    assert res_empty.json()["error"]["code"] == "EMPTY_FILE"

    # 3. Reject unsupported MIME type -> 400 Bad Request
    res_bad_mime = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("virus.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-dosexec")},
    )
    assert res_bad_mime.status_code == 400
    assert res_bad_mime.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    # 4. List task attachments -> 200 OK (1 item)
    res_list = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1
    assert res_list.json()["items"][0]["id"] == att_id

    # 5. Non-uploader regular member cannot delete -> 403 Forbidden
    res_unauth_del = await collab_client.delete(
        f"/api/v1/attachments/{att_id}",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_unauth_del.status_code == 403

    # 6. Uploader deletes attachment -> 200 OK
    res_del = await collab_client.delete(
        f"/api/v1/attachments/{att_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"

    # 7. List confirms attachment was deleted
    res_list_after = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_activities_timeline_and_scoping(collab_client: AsyncClient):
    """Verify append-only activity tracking across organizations, projects, and tasks."""
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    task1_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")

    # 1. Post comment to generate comment_created activity
    await collab_client.post(
        f"/api/v1/tasks/{task1_id}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Activity audit log testing comment."},
    )

    # 2. Transition task status to generate task_status_changed activity
    await collab_client.patch(
        f"/api/v1/tasks/{task1_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_review"},
    )

    # 3. Query Organization activities
    res_org_act = await collab_client.get(
        f"/api/v1/organizations/{org1_id}/activities",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_org_act.status_code == 200
    org_acts = res_org_act.json()
    assert org_acts["total"] >= 2
    actions = [a["action"] for a in org_acts["items"]]
    assert "comment_created" in actions
    assert "task_status_changed" in actions

    # 4. Query Project activities
    res_proj_act = await collab_client.get(
        f"/api/v1/projects/{proj1_id}/activities",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_proj_act.status_code == 200
    assert res_proj_act.json()["total"] >= 2

    # 5. Query Task activities
    res_task_act = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/activities",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_task_act.status_code == 200
    task_acts = res_task_act.json()
    assert task_acts["total"] >= 2
    task_actions = [a["action"] for a in task_acts["items"]]
    assert "comment_created" in task_actions
    assert "task_status_changed" in task_actions

    # 6. Pagination check
    res_paginated = await collab_client.get(
        f"/api/v1/tasks/{task1_id}/activities?limit=1&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_paginated.status_code == 200
    assert len(res_paginated.json()["items"]) == 1
    assert res_paginated.json()["total"] >= 2


@pytest.mark.asyncio
async def test_notifications_lifecycle_and_unread_counts(collab_client: AsyncClient):
    """Verify notifications generation on assignment and comments, read status toggling, and bulk reads."""
    proj1_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    devon_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    sam_id = uuid.UUID("77777777-7777-7777-7777-777777777777")

    devon_token = create_jwt_token(sub=devon_id, email="devon@flowstate.dev")
    sam_token = create_jwt_token(sub=sam_id, email="sam@flowstate.dev")

    # 1. Devon checks inbox -> 0 unread
    res_devon_init = await collab_client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_devon_init.json()["unread_count"] == 0

    # 2. Devon creates a task and assigns it to Sam -> triggers assignment notification for Sam
    res_create = await collab_client.post(
        f"/api/v1/projects/{proj1_id}/tasks",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={
            "title": "Sam's Collaboration Task",
            "assignee_id": str(sam_id),
        },
    )
    assert res_create.status_code == 201
    new_task_id = res_create.json()["id"]

    # 3. Sam polls unread count -> 1
    res_sam_count = await collab_client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_sam_count.json()["unread_count"] == 1

    # 4. Sam views notifications list
    res_sam_list = await collab_client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_sam_list.status_code == 200
    items = res_sam_list.json()["items"]
    assert len(items) == 1
    notif = items[0]
    assert notif["type"] == NotificationType.ASSIGNMENT.value
    assert "Assigned to" in notif["title"]
    notif_id = notif["id"]

    # 5. Devon (the actor) still has 0 notifications (no self-alerts)
    res_devon_after = await collab_client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {devon_token}"},
    )
    assert res_devon_after.json()["unread_count"] == 0

    # 6. Sam marks notification as read
    res_mark = await collab_client.patch(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_mark.status_code == 200
    assert res_mark.json()["is_read"] is True

    # 7. Unread count drops to 0
    res_sam_zero = await collab_client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_sam_zero.json()["unread_count"] == 0

    # 8. Devon comments on Sam's task -> triggers comment notification for Sam
    await collab_client.post(
        f"/api/v1/tasks/{new_task_id}/comments",
        headers={"Authorization": f"Bearer {devon_token}"},
        json={"content": "Please start on this task today."},
    )
    res_sam_new_count = await collab_client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_sam_new_count.json()["unread_count"] == 1

    # 9. Bulk read: mark all notifications as read
    res_bulk = await collab_client.patch(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_bulk.status_code == 200
    assert res_bulk.json()["updated_count"] >= 1

    # 10. Delete notification
    res_del_notif = await collab_client.delete(
        f"/api/v1/notifications/{notif_id}",
        headers={"Authorization": f"Bearer {sam_token}"},
    )
    assert res_del_notif.status_code == 200


@pytest.mark.asyncio
async def test_security_cross_tenant_and_unauthorized(collab_client: AsyncClient):
    """Verify tenant isolation and authentication boundaries for collaboration endpoints."""
    task1_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
    org1_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    alice_id = uuid.UUID("44444444-4444-4444-4444-444444444444") # Org 2 Owner
    alice_token = create_jwt_token(sub=alice_id, email="alice@acme.dev")

    # 1. Unauthenticated comment post -> 401 Unauthorized
    res_unauth = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/comments",
        json={"content": "Unauthenticated comment"},
    )
    assert res_unauth.status_code == 401

    # 2. Org 2 user posts comment on Org 1 task -> 404 Task Not Found
    res_cross_comment = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/comments",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"content": "Cross-tenant intrusion attempt"},
    )
    assert res_cross_comment.status_code == 404

    # 3. Org 2 user uploads attachment to Org 1 task -> 404 Task Not Found
    res_cross_att = await collab_client.post(
        f"/api/v1/tasks/{task1_id}/attachments",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("exploit.pdf", io.BytesIO(b"%PDF-1.4 binary"), "application/pdf")},
    )
    assert res_cross_att.status_code == 404

    # 4. Org 2 user attempts to view Org 1 activities -> 403 Forbidden
    res_cross_act = await collab_client.get(
        f"/api/v1/organizations/{org1_id}/activities",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_cross_act.status_code == 403
