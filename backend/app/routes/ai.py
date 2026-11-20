import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies.auth import get_active_organization, ActiveOrganizationContext
from app.services.ai import AIService
from app.schemas.ai import (
    SubtaskGenerationRequest,
    SubtaskGenerationResponse,
    AssigneeSuggestionRequest,
    AssigneeSuggestionResponse,
    AIChatRequest,
    AIChatResponse,
    SprintRetroRequest,
    SprintRetroResponse,
)

logger = logging.getLogger("flowstate.routes.ai")

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


@router.post(
    "/subtasks",
    response_model=SubtaskGenerationResponse,
    summary="AI Task Breakdown & Subtasks Generator",
    description="Decomposes a high-level task title/PRD into structured subtasks, estimate, and priority.",
)
async def generate_subtasks(
    payload: SubtaskGenerationRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
) -> SubtaskGenerationResponse:
    return await AIService.generate_subtasks(
        title=payload.title,
        description=payload.description,
        labels=payload.labels,
    )


@router.post(
    "/suggest-assignee",
    response_model=AssigneeSuggestionResponse,
    summary="AI Assignee & Effort Recommendation",
    description="Recommends the best team member based on active workloads and department skills.",
)
async def suggest_assignee(
    payload: AssigneeSuggestionRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> AssigneeSuggestionResponse:
    return await AIService.suggest_assignee(
        task_title=payload.task_title,
        task_description=payload.task_description,
        org_id=ctx.organization_id,
        db=db,
    )


@router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="AI Workspace Copilot Chat",
    description="Answers natural language questions about projects, tasks, bottlenecks, and workloads.",
)
async def chat_with_copilot(
    payload: AIChatRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    return await AIService.chat_with_workspace(
        messages=messages,
        org_id=ctx.organization_id,
        db=db,
    )


@router.post(
    "/retrospective",
    response_model=SprintRetroResponse,
    summary="AI Sprint Retrospective Generator",
    description="Synthesizes sprint metrics, achievements, bottlenecks, and action items into an executive report.",
)
async def generate_sprint_retro(
    payload: SprintRetroRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> SprintRetroResponse:
    return await AIService.generate_sprint_retro(
        org_id=ctx.organization_id,
        db=db,
        timeframe_days=payload.timeframe_days,
    )
