import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.dependencies.database import get_db
from app.models.enums import PriorityLevel, ProjectStatus, SubscriptionPlan, TaskStatus, UserRole
from app.models.organization import Organization, OrganizationMember, WorkspaceSettings
from app.models.project import Project, ProjectMember
from app.models.task import Label, Task
from app.models.team import Team, TeamMember
from sqlalchemy import text, select

DEMO_USERS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "alex@flowstate.dev",
        "name": "Alex Rivera",
        "title": "Lead Product Manager",
        "department": "Product",
        "role": UserRole.OWNER,
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "email": "jordan@flowstate.dev",
        "name": "Jordan Vance",
        "title": "Principal Architect",
        "department": "Engineering",
        "role": UserRole.ADMIN,
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "email": "elena@flowstate.dev",
        "name": "Elena Rostova",
        "title": "Senior Backend Engineer",
        "department": "Platform",
        "role": UserRole.DEVELOPER,
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "email": "marcus@flowstate.dev",
        "name": "Marcus Chen",
        "title": "Product Designer",
        "department": "Design",
        "role": UserRole.DESIGNER,
    },
]

async def seed():
    async for db in get_db():
        print("1. Seeding auth.users...")
        for u in DEMO_USERS:
            await db.execute(text(f"""
                INSERT INTO auth.users (id, email, raw_user_meta_data, created_at, updated_at, aud, role)
                VALUES (
                    '{u["id"]}',
                    '{u["email"]}',
                    '{{"full_name": "{u["name"]}", "name": "{u["name"]}"}}',
                    NOW(),
                    NOW(),
                    'authenticated',
                    'authenticated'
                )
                ON CONFLICT (id) DO NOTHING;
            """))
            await db.execute(text(f"""
                UPDATE public.users
                SET title = '{u["title"]}', department = '{u["department"]}'
                WHERE id = '{u["id"]}';
            """))
        await db.commit()

        org_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        print("2. Seeding default organization 'Flowstate Labs'...")
        org = await db.scalar(select(Organization).where(Organization.id == org_id))
        if not org:
            org = Organization(
                id=org_id,
                name="Flowstate Labs",
                slug="flowstate-labs",
                plan=SubscriptionPlan.FREE,
            )
            db.add(org)
            await db.flush()

            settings = WorkspaceSettings(
                organization_id=org_id,
                currency="USD",
                timezone="America/San_Francisco",
                working_days=[1, 2, 3, 4, 5],
                notifications_email=True,
                notifications_desktop=True,
                theme="dark",
                accent_color="#8B7CFF",
            )
            db.add(settings)

        print("3. Seeding organization memberships...")
        for u in DEMO_USERS:
            uid = uuid.UUID(u["id"])
            mem = await db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == uid,
                )
            )
            if not mem:
                mem = OrganizationMember(
                    organization_id=org_id,
                    user_id=uid,
                    role=u["role"],
                )
                db.add(mem)
        await db.flush()

        print("4. Seeding default team...")
        team_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
        team = await db.scalar(select(Team).where(Team.id == team_id))
        if not team:
            team = Team(
                id=team_id,
                organization_id=org_id,
                name="Core Engineering",
                description="Frontend, Backend, and Infrastructure platform teams.",
                lead_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            )
            db.add(team)
            await db.flush()

            for u in DEMO_USERS:
                db.add(TeamMember(team_id=team_id, user_id=uuid.UUID(u["id"])))

        print("5. Seeding demo projects...")
        proj1_id = uuid.UUID("99999999-1111-2222-3333-444444444441")
        proj1 = await db.scalar(select(Project).where(Project.id == proj1_id))
        if not proj1:
            proj1 = Project(
                id=proj1_id,
                organization_id=org_id,
                team_id=team_id,
                manager_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                key="FLW",
                name="Platform Modernization",
                description="Migrating legacy monolithic workflows to FastAPI and Next.js Turbopack with Postgres.",
                status=ProjectStatus.IN_PROGRESS,
                priority=PriorityLevel.URGENT,
                color="#8B7CFF",
                start_date=date(2026, 11, 1),
                due_date=date(2026, 12, 15),
                budget=45000,
                spent=12500,
                last_task_number=103,
            )
            db.add(proj1)
            await db.flush()

            for u in DEMO_USERS:
                db.add(ProjectMember(project_id=proj1_id, user_id=uuid.UUID(u["id"])))

            print("6. Seeding demo tasks...")
            t1 = Task(
                id=uuid.UUID("88888888-1111-2222-3333-444444444441"),
                organization_id=org_id,
                project_id=proj1_id,
                task_number=101,
                key="FLW-101",
                title="Integrate FastAPI Supabase JWT Auth Bridge",
                description="Verify Supabase access tokens, resolve active tenant organization, and guard RBAC.",
                status=TaskStatus.DONE,
                priority=PriorityLevel.HIGH,
                assignee_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
                creator_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                due_date=date(2026, 11, 20),
                estimated_hours=16,
                actual_hours=14,
                order=1000.0,
            )
            t2 = Task(
                id=uuid.UUID("88888888-1111-2222-3333-444444444442"),
                organization_id=org_id,
                project_id=proj1_id,
                task_number=102,
                key="FLW-102",
                title="Connect Next.js Workspace Context to Live Backend APIs",
                description="Wire API client, tasks, projects, teams, calendar and dashboard endpoints.",
                status=TaskStatus.IN_PROGRESS,
                priority=PriorityLevel.URGENT,
                assignee_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                creator_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                due_date=date(2026, 11, 25),
                estimated_hours=24,
                actual_hours=18,
                order=2000.0,
            )
            t3 = Task(
                id=uuid.UUID("88888888-1111-2222-3333-444444444443"),
                organization_id=org_id,
                project_id=proj1_id,
                task_number=103,
                key="FLW-103",
                title="Design interactive analytics dashboard with Recharts",
                description="Render velocity, team workload distribution, and milestone countdowns.",
                status=TaskStatus.TODO,
                priority=PriorityLevel.MEDIUM,
                assignee_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
                creator_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                due_date=date(2026, 11, 30),
                estimated_hours=12,
                actual_hours=0,
                order=3000.0,
            )
            db.add_all([t1, t2, t3])

        await db.commit()
        print("Seeding completed successfully!")
        break

if __name__ == "__main__":
    asyncio.run(seed())
