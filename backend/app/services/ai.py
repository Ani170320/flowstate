import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.task import Task
from app.models.project import Project
from app.models.organization import OrganizationMember
from app.models.user import User
from app.models.enums import TaskStatus, PriorityLevel
from app.schemas.ai import (
    SubtaskItem,
    SubtaskGenerationResponse,
    AssigneeSuggestionResponse,
    AIChatResponse,
    SprintRetroResponse,
)

logger = logging.getLogger("flowstate.services.ai")


class AIService:
    @staticmethod
    async def _call_gemini(prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        if not settings.GEMINI_API_KEY:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
        except Exception as exc:
            logger.warning("Gemini API call failed: %s", exc)
        return None

    @staticmethod
    async def _call_openai(prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        if not settings.OPENAI_API_KEY:
            return None
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("OpenAI API call failed: %s", exc)
        return None

    @classmethod
    async def generate_subtasks(
        cls, title: str, description: Optional[str] = None, labels: Optional[List[str]] = None
    ) -> SubtaskGenerationResponse:
        system_instruction = (
            "You are a Principal Software Architect and Agile Engineering Coach. "
            "Given a feature title or task requirement, decompose it into a clean, actionable engineering ticket. "
            "Return valid JSON matching this structure: "
            '{"suggested_title": str, "description": str, "estimated_hours": int, "priority": "low"|"medium"|"high"|"urgent", "subtasks": [{"title": str}], "labels": [str]}'
        )
        prompt = f"Decompose this engineering task:\nTitle: {title}\nExtra Context: {description or 'None'}\nLabels: {labels or []}"

        llm_output = await cls._call_gemini(prompt, system_instruction)
        if not llm_output:
            llm_output = await cls._call_openai(prompt, system_instruction)

        if llm_output:
            try:
                cleaned = llm_output.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())
                subtasks = [SubtaskItem(title=s.get("title", "")) for s in data.get("subtasks", []) if s.get("title")]
                return SubtaskGenerationResponse(
                    suggested_title=data.get("suggested_title", title),
                    description=data.get("description", description or f"Implementation details for {title}"),
                    estimated_hours=int(data.get("estimated_hours", 8)),
                    priority=data.get("priority", "medium"),
                    subtasks=subtasks,
                    labels=data.get("labels", labels or ["Feature", "Backend"]),
                )
            except Exception as e:
                logger.warning("Failed to parse LLM JSON: %s", e)

        # Context-aware deterministic fallback breakdown
        t_lower = title.lower()
        subtasks = [
            SubtaskItem(title="Design schema & data contracts"),
            SubtaskItem(title="Implement core API endpoints and middleware"),
            SubtaskItem(title="Integrate frontend UI and state management"),
            SubtaskItem(title="Write comprehensive unit and integration tests"),
            SubtaskItem(title="Add telemetry, error boundaries, and documentation"),
        ]

        priority = "medium"
        hours = 8
        labels_out = list(labels or [])
        if any(w in t_lower for w in ["auth", "security", "jwt", "login", "oauth"]):
            subtasks = [
                SubtaskItem(title="Define user token lifecycle and refresh strategies"),
                SubtaskItem(title="Implement password hashing and auth routes"),
                SubtaskItem(title="Set up secure HTTP-only cookies and local session caching"),
                SubtaskItem(title="Write multi-role permission validation tests"),
                SubtaskItem(title="Audit rate limiting and brute-force protection"),
            ]
            priority = "high"
            hours = 12
            labels_out.extend(["Security", "Backend", "Auth"])
        elif any(w in t_lower for w in ["database", "schema", "postgres", "migration", "sql"]):
            subtasks = [
                SubtaskItem(title="Draft Alembic migration script and table definitions"),
                SubtaskItem(title="Add foreign keys, indexes, and unique constraints"),
                SubtaskItem(title="Verify backward-compatible data upgrade/downgrade"),
                SubtaskItem(title="Profile query execution plan with EXPLAIN ANALYZE"),
            ]
            priority = "high"
            hours = 6
            labels_out.extend(["Database", "Performance"])
        elif any(w in t_lower for w in ["ui", "modal", "dashboard", "component", "frontend", "calendar", "board"]):
            subtasks = [
                SubtaskItem(title="Draft responsive UI mockup and layout container"),
                SubtaskItem(title="Connect component to workspace state and context"),
                SubtaskItem(title="Handle optimistic UI updates, loading spinners, and error alerts"),
                SubtaskItem(title="Verify dark-mode styling and keyboard navigation accessibility"),
            ]
            hours = 6
            labels_out.extend(["Frontend", "UI/UX"])

        return SubtaskGenerationResponse(
            suggested_title=title.title() if len(title) > 3 else title,
            description=description or f"Complete implementation and production rollout for {title}. Enforces multi-tenant data isolation and error handling.",
            estimated_hours=hours,
            priority=priority,
            subtasks=subtasks,
            labels=list(set(labels_out or ["Feature"])),
        )

    @classmethod
    async def suggest_assignee(
        cls,
        task_title: str,
        task_description: Optional[str],
        org_id: uuid.UUID,
        db: AsyncSession,
    ) -> AssigneeSuggestionResponse:
        # Fetch members of the active organization
        stmt = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == org_id)
        )
        members = (await db.execute(stmt)).scalars().all()
        if not members:
            return AssigneeSuggestionResponse(
                recommended_user_id=None,
                reasoning="No members currently available in this workspace.",
                suggested_hours=8,
            )

        # Get task workloads per user
        active_tasks_stmt = (
            select(Task.assignee_id, func.count(Task.id))
            .where(Task.organization_id == org_id, Task.status != TaskStatus.DONE)
            .group_by(Task.assignee_id)
        )
        counts = dict((await db.execute(active_tasks_stmt)).all())

        best_member = None
        min_load = 99999
        title_lower = task_title.lower()

        for m in members:
            u = m.user
            if not u:
                continue
            load = counts.get(u.id, 0)
            bonus = 0
            # Role / department matching heuristics
            if any(k in title_lower for k in ["api", "backend", "db", "auth", "postgres"]) and "eng" in (u.department or "").lower():
                bonus -= 2
            if any(k in title_lower for k in ["ui", "design", "css", "layout", "modal"]) and ("frontend" in (u.title or "").lower() or "design" in (u.department or "").lower()):
                bonus -= 2
            effective_score = load + bonus
            if effective_score < min_load:
                min_load = effective_score
                best_member = u

        if not best_member and members:
            best_member = members[0].user

        est_hours = 8
        if any(w in title_lower for w in ["refactor", "migration", "redesign", "full-stack"]):
            est_hours = 16
        elif any(w in title_lower for w in ["fix", "typo", "button", "copy", "icon"]):
            est_hours = 3

        return AssigneeSuggestionResponse(
            recommended_user_id=str(best_member.id) if best_member else None,
            recommended_user_name=best_member.name if best_member else "Team Member",
            confidence=0.92,
            reasoning=f"Recommended {best_member.name if best_member else 'user'} based on current capacity ({counts.get(best_member.id if best_member else None, 0)} active tasks) and engineering role.",
            suggested_hours=est_hours,
        )

    @classmethod
    async def chat_with_workspace(
        cls,
        messages: List[Dict[str, str]],
        org_id: uuid.UUID,
        db: AsyncSession,
    ) -> AIChatResponse:
        # Fetch current workspace state for RAG context
        p_stmt = select(Project).where(Project.organization_id == org_id)
        projects = (await db.execute(p_stmt)).scalars().all()

        t_stmt = (
            select(Task)
            .options(selectinload(Task.assignee))
            .where(Task.organization_id == org_id)
            .order_by(Task.updated_at.desc())
            .limit(50)
        )
        tasks = (await db.execute(t_stmt)).scalars().all()

        total_tasks = len(tasks)
        done_tasks = [t for t in tasks if t.status == TaskStatus.DONE]
        in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        urgent_tasks = [t for t in tasks if t.priority == PriorityLevel.URGENT and t.status != TaskStatus.DONE]
        overdue_tasks = [
            t for t in tasks
            if t.status != TaskStatus.DONE and t.due_date and t.due_date < datetime.now(timezone.utc).date()
        ]

        context_summary = (
            f"Active Workspace Context:\n"
            f"- Projects ({len(projects)}): {', '.join([p.name + ' (' + p.key + ')' for p in projects])}\n"
            f"- Total Tasks: {total_tasks} ({len(done_tasks)} completed, {len(in_progress_tasks)} in progress)\n"
            f"- Critical / Urgent Tasks: {len(urgent_tasks)} ({', '.join([t.title for t in urgent_tasks[:3]]) or 'None'})\n"
            f"- Overdue Tasks: {len(overdue_tasks)} ({', '.join([t.title for t in overdue_tasks[:3]]) or 'None'})\n"
        )

        user_prompt = messages[-1]["content"] if messages else "Summary"

        llm_reply = await cls._call_gemini(
            f"{context_summary}\n\nUser Question: {user_prompt}",
            system_instruction="You are FLOWSTATE AI Copilot, an expert Engineering Operations Intelligence assistant. Answer questions concisely, factually based on the workspace context, using Markdown with bullet points.",
        )
        if not llm_reply:
            llm_reply = await cls._call_openai(
                f"{context_summary}\n\nUser Question: {user_prompt}",
                system_instruction="You are FLOWSTATE AI Copilot, an expert Engineering Operations Intelligence assistant. Answer questions concisely, factually based on the workspace context, using Markdown with bullet points.",
            )

        if llm_reply:
            return AIChatResponse(reply=llm_reply)

        # Contextual Fallback Response Engine
        q = user_prompt.lower()
        if any(w in q for w in ["blocker", "urgent", "critical", "danger"]):
            if urgent_tasks or overdue_tasks:
                items = []
                for t in urgent_tasks:
                    items.append(f"- **[URGENT] {t.key or 'TASK'}:** {t.title} (Status: `{t.status.value}`, Assignee: {t.assignee.name if t.assignee else 'Unassigned'})")
                for t in overdue_tasks:
                    if t not in urgent_tasks:
                        items.append(f"- **[OVERDUE] {t.key or 'TASK'}:** {t.title} (Due: `{t.due_date}`, Assignee: {t.assignee.name if t.assignee else 'Unassigned'})")
                reply = f"### ⚠️ Current Workspace Blockers\n\nFound **{len(urgent_tasks)} urgent** and **{len(overdue_tasks)} overdue** items requiring engineering attention:\n\n" + "\n".join(items)
            else:
                reply = "### ✅ Zero Critical Blockers\n\nThere are currently **0 urgent blockers** and **0 overdue tasks** in this workspace. Delivery is on schedule!"
        elif any(w in q for w in ["project", "initiative", "roadmap"]):
            proj_items = [f"- **{p.name} (`{p.key}`):** {p.status.value.replace('_', ' ').title()} • Progress: `{p.progress}%` • Due: `{p.due_date or 'No deadline'}`" for p in projects]
            reply = f"### 📁 Active Projects Overview ({len(projects)})\n\n" + ("\n".join(proj_items) if proj_items else "No projects created yet.")
        elif any(w in q for w in ["summary", "status", "health", "overview"]):
            rate = Math_round = round((len(done_tasks) / total_tasks * 100)) if total_tasks > 0 else 0
            reply = (
                f"### 🚀 Workspace Executive Brief\n\n"
                f"- **Overall Completion Rate:** `{rate}%` ({len(done_tasks)} of {total_tasks} tickets merged)\n"
                f"- **In Flight:** `{len(in_progress_tasks)} tasks` currently in active development\n"
                f"- **Active Projects:** `{len(projects)} initiatives` tracking delivery\n"
                f"- **Risk Profile:** `{len(urgent_tasks)} urgent` tickets, `{len(overdue_tasks)} overdue` milestones\n\n"
                f"The team is progressing with steady throughput. You can export a full audit report from the **Analytics** page."
            )
        else:
            reply = (
                f"### 🤖 FLOWSTATE AI Intelligence\n\n"
                f"I am monitoring your workspace in real-time. Here is your current snapshot:\n"
                f"- **{len(projects)}** active projects\n"
                f"- **{total_tasks}** total engineering tickets\n"
                f"- **{len(in_progress_tasks)}** in active sprint progress\n\n"
                f"Try asking:\n"
                f"- *\"What are our urgent blockers?\"*\n"
                f"- *\"Show project progress summary\"*\n"
                f"- *\"Which tasks are in review?\"*"
            )

        return AIChatResponse(reply=reply)

    @classmethod
    async def generate_sprint_retro(
        cls,
        org_id: uuid.UUID,
        db: AsyncSession,
        timeframe_days: int = 14,
    ) -> SprintRetroResponse:
        cutoff = datetime.now(timezone.utc) - timedelta(days=timeframe_days)
        t_stmt = select(Task).where(Task.organization_id == org_id)
        tasks = (await db.execute(t_stmt)).scalars().all()

        completed = [t for t in tasks if t.status == TaskStatus.DONE]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        overdue = [t for t in tasks if t.status != TaskStatus.DONE and t.due_date and t.due_date < datetime.now(timezone.utc).date()]

        total = len(tasks)
        rate = round((len(completed) / total) * 100) if total > 0 else 0

        highlights = [
            f"Closed and merged {len(completed)} engineering tickets across active projects.",
            f"Achieved a {rate}% overall sprint delivery rate.",
            f"Successfully maintained multi-tab synchronization and real-time operations.",
        ]
        bottlenecks = [
            f"{len(overdue)} tickets slipped past scheduled delivery dates.",
            f"{len(in_progress)} tickets carried over into the next cycle.",
        ]
        recommendations = [
            "Decompose large tickets (>12h) into granular subtasks during sprint planning.",
            "Establish automated PR review SLA of under 24 hours to reduce cycle time.",
            "Prioritize unblocking critical dependencies before starting backlog items.",
        ]

        markdown = (
            f"# 🏁 Sprint Retrospective Report ({timeframe_days} Days)\n\n"
            f"**Generated:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n"
            f"**Scope:** Organization Workspace\n\n"
            f"## 📊 Executive Delivery Metrics\n"
            f"- **Completion Rate:** `{rate}%` ({len(completed)} / {total} tasks)\n"
            f"- **Active In-Progress:** `{len(in_progress)} tickets`\n"
            f"- **Overdue / Missed Cutoffs:** `{len(overdue)} tickets`\n\n"
            f"## 🏆 Key Achievements & Delivered Value\n" + "\n".join([f"- {h}" for h in highlights]) + "\n\n"
            f"## ⚠️ Friction Points & Bottlenecks\n" + "\n".join([f"- {b}" for b in bottlenecks]) + "\n\n"
            f"## 💡 Actionable Recommendations for Next Cycle\n" + "\n".join([f"- {r}" for r in recommendations]) + "\n"
        )

        return SprintRetroResponse(
            markdown_report=markdown,
            summary=f"Delivered {len(completed)} tasks with {rate}% sprint completion rate.",
            highlights=highlights,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )
