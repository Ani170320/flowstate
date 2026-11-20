import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Base,
    User,
    Organization,
    OrganizationMember,
    WorkspaceSettings,
    Team,
    TeamMember,
    Project,
    ProjectMember,
    Task,
    Subtask,
    Label,
    task_labels,
    Comment,
    Attachment,
    Activity,
    Notification,
    UserRole,
    SubscriptionPlan,
    ProjectStatus,
    PriorityLevel,
    TaskStatus,
    NotificationType,
)


def test_metadata_contains_all_16_tables():
    """Verify that Base.metadata contains all 16 required FLOWSTATE tables."""
    expected_tables = {
        "users",
        "organizations",
        "organization_members",
        "workspace_settings",
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
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), f"Missing tables: {expected_tables - registered_tables}"


def test_project_and_compound_isolation_constraints():
    """Verify Project compound unique constraint and last_task_number counter."""
    table = Project.__table__
    assert table.name == "projects"
    assert "last_task_number" in table.c
    assert table.c.last_task_number.server_default.arg == "100"

    # Compound unique constraint for cross-tenant isolation
    uq_names = {uq.name for uq in table.constraints if hasattr(uq, "name") and uq.name}
    assert "uq_projects_id_org" in uq_names
    assert "uq_projects_org_key" in uq_names


def test_task_compound_foreign_key_and_constraints():
    """Verify Task enforces compound foreign key (project_id, organization_id) to Project."""
    table = Task.__table__
    assert table.name == "tasks"

    # Verify compound FK
    fk_constraints = [c for c in table.foreign_key_constraints if c.name == "fk_tasks_project_org"]
    assert len(fk_constraints) == 1
    fk = fk_constraints[0]
    col_names = [col.name for col in fk.columns]
    target_names = [el.target_fullname for el in fk.elements]
    assert col_names == ["project_id", "organization_id"]
    assert target_names == ["projects.id", "projects.organization_id"]
    assert fk.ondelete == "CASCADE"

    # Verify task numbering uniqueness per project
    uq_names = {uq.name for uq in table.constraints if hasattr(uq, "name") and uq.name}
    assert "uq_tasks_proj_number" in uq_names
    assert "uq_tasks_id_org" in uq_names


def test_attachment_check_constraints():
    """Verify attachments check constraint requiring at least one target."""
    table = Attachment.__table__
    assert table.name == "attachments"

    chk_names = {chk.name for chk in table.constraints if hasattr(chk, "name") and chk.name}
    assert "chk_attachment_target" in chk_names
    assert "chk_attachment_positive_size" in chk_names


def test_full_hierarchy_orm_lifecycle():
    """
    Creates an end-to-end multi-tenant workspace hierarchy across all 16 tables:
    Org -> WorkspaceSettings, Team, Project -> Members, Tasks, Subtasks, Labels,
    Comments, Attachments, Activities, Notifications.
    Tests relationships, navigation, and cascading deletions.
    """
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS auth")

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # 1. Users
    user_owner_id = uuid.uuid4()
    user_dev_id = uuid.uuid4()
    owner = User(
        id=user_owner_id,
        email="alex@flowstate.dev",
        name="Alex Rivera",
        department="Engineering",
        title="VP of Eng",
    )
    dev = User(
        id=user_dev_id,
        email="devon@flowstate.dev",
        name="Devon Miller",
        department="Frontend",
        title="Senior Developer",
    )
    session.add_all([owner, dev])
    session.flush()

    # 2. Organization & Workspace Settings
    org = Organization(
        name="Flowstate Technologies",
        slug="flowstate-tech",
        plan=SubscriptionPlan.ENTERPRISE,
    )
    session.add(org)
    session.flush()

    settings = WorkspaceSettings(
        organization_id=org.id,
        currency="USD",
        timezone="America/New_York",
        accent_color="#6366F1",
    )
    session.add(settings)

    # 3. Organization Members
    mem_owner = OrganizationMember(organization=org, user=owner, role=UserRole.OWNER)
    mem_dev = OrganizationMember(organization=org, user=dev, role=UserRole.DEVELOPER)
    session.add_all([mem_owner, mem_dev])

    # 4. Team & Team Member
    team = Team(
        organization=org,
        name="Core Platform",
        description="Core infrastructure and platform APIs",
        lead=owner,
    )
    session.add(team)
    session.flush()

    t_member = TeamMember(team=team, user=dev)
    session.add(t_member)

    # 5. Project & Project Member
    project = Project(
        organization=org,
        team=team,
        manager=owner,
        name="Task Engine 2.0",
        key="FLW",
        description="Next-gen real-time task engine",
        status=ProjectStatus.IN_PROGRESS,
        priority=PriorityLevel.HIGH,
        last_task_number=100,
    )
    session.add(project)
    session.flush()

    p_member = ProjectMember(project=project, user=dev)
    session.add(p_member)

    # 6. Labels
    label_bug = Label(organization=org, name="Bug", color="#EF4444")
    label_perf = Label(organization=org, name="Performance", color="#10B981")
    session.add_all([label_bug, label_perf])
    session.flush()

    # 7. Task with Atomic Number
    project.last_task_number += 1
    task = Task(
        organization=org,
        project=project,
        assignee=dev,
        creator=owner,
        task_number=project.last_task_number,
        key=f"{project.key}-{project.last_task_number}",
        title="Optimize Kanban state sync",
        description="Reduce latency of optimistic WebSocket updates",
        status=TaskStatus.IN_PROGRESS,
        priority=PriorityLevel.URGENT,
        order=1000.0,
    )
    task.labels.append(label_perf)
    session.add(task)
    session.flush()

    # 8. Subtask
    subtask = Subtask(
        task=task,
        title="Profile asyncpg connection pool",
        order=1,
        completed=True,
    )
    session.add(subtask)

    # 9. Comment
    comment = Comment(
        task=task,
        author=dev,
        content="Benchmarked asyncpg vs psycopg3, asyncpg achieved 2.4x throughput under load.",
    )
    session.add(comment)
    session.flush()

    # 10. Attachment
    attachment = Attachment(
        organization=org,
        task=task,
        uploader=dev,
        name="benchmark_results.json",
        storage_path="/storage/attachments/flw-101/benchmark_results.json",
        file_size=42800,
        mime_type="application/json",
    )
    session.add(attachment)

    # 11. Activity
    activity = Activity(
        organization=org,
        project=project,
        user=dev,
        action="task_status_changed",
        target_type="task",
        target_id=task.id,
        target_title=task.title,
        details={"from": "TODO", "to": "IN_PROGRESS"},
    )
    session.add(activity)

    # 12. Notification
    notification = Notification(
        user=owner,
        sender=dev,
        type=NotificationType.ASSIGNMENT,
        title="Task Status Updated",
        message="Devon Miller moved FLW-101 to IN_PROGRESS",
        link=f"/projects/{project.key}/tasks/{task.task_number}",
        is_read=False,
    )
    session.add(notification)
    session.commit()

    # Verify all records saved and navigable via ORM
    refreshed_task = session.scalar(select(Task).where(Task.id == task.id))
    assert refreshed_task is not None
    assert refreshed_task.task_number == 101
    assert refreshed_task.project.key == "FLW"
    assert refreshed_task.organization.slug == "flowstate-tech"
    assert len(refreshed_task.subtasks) == 1
    assert refreshed_task.subtasks[0].title == "Profile asyncpg connection pool"
    assert len(refreshed_task.labels) == 1
    assert refreshed_task.labels[0].name == "Performance"
    assert len(refreshed_task.comments) == 1
    assert refreshed_task.comments[0].author.name == "Devon Miller"
    assert len(refreshed_task.attachments) == 1
    assert refreshed_task.attachments[0].name == "benchmark_results.json"

    # Test Project Cascade Deletion
    session.delete(project)
    session.commit()

    # Project deletion must cascade and remove tasks, subtasks, comments, attachments
    assert session.scalar(select(Task).where(Task.id == task.id)) is None
    assert session.scalar(select(Subtask).where(Subtask.id == subtask.id)) is None
    assert session.scalar(select(Comment).where(Comment.id == comment.id)) is None
    assert session.scalar(select(Attachment).where(Attachment.id == attachment.id)) is None

    # Organization and users must remain intact
    assert session.scalar(select(Organization).where(Organization.id == org.id)) is not None
    assert session.scalar(select(User).where(User.id == dev.id)) is not None

    # Test Organization Cascade Deletion
    refreshed_org = session.scalar(select(Organization).where(Organization.id == org.id))
    session.delete(refreshed_org)
    session.commit()

    assert session.scalar(select(WorkspaceSettings).where(WorkspaceSettings.organization_id == org.id)) is None
    assert session.scalar(select(Team).where(Team.id == team.id)) is None
    assert len(session.scalars(select(OrganizationMember).where(OrganizationMember.organization_id == org.id)).all()) == 0

    session.close()
