import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
    require_min_org_role,
)
from app.dependencies.database import get_db
from app.models.enums import UserRole
from app.models.task import Label
from app.schemas.task import (
    LabelCreateRequest,
    LabelResponse,
    LabelUpdateRequest,
)

logger = logging.getLogger("flowstate.routes.labels")

router = APIRouter(tags=["Labels"])


# ---------------------------------------------------------------------------
# Label CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/organizations/{organization_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Label (Org Path)",
)
@router.post(
    "/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Label",
    description="Creates a categorization label for the active organization.",
)
async def create_label(
    payload: LabelCreateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> LabelResponse:
    org_id = ctx.organization_id
    clean_name = payload.name.strip()

    # 1. Uniqueness check within organization (uq_labels_org_name)
    existing = await db.scalar(
        select(Label.id).where(
            Label.organization_id == org_id,
            func.lower(Label.name) == clean_name.lower(),
        )
    )
    if existing:
        raise BadRequestException(
            f"Label '{clean_name}' already exists in this organization.",
            code="LABEL_NAME_COLLISION",
        )

    label = Label(
        organization_id=org_id,
        name=clean_name,
        color=payload.color.strip(),
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)

    return LabelResponse(
        id=label.id,
        organization_id=label.organization_id,
        name=label.name,
        color=label.color,
        created_at=label.created_at,
    )


@router.get(
    "/organizations/{organization_id}/labels",
    response_model=List[LabelResponse],
    summary="List Labels (Org Path)",
)
@router.get(
    "/labels",
    response_model=List[LabelResponse],
    summary="List Labels",
    description="Lists all labels available in the active organization.",
)
async def list_labels(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[LabelResponse]:
    stmt = (
        select(Label)
        .where(Label.organization_id == ctx.organization_id)
        .order_by(Label.name.asc())
    )
    labels = (await db.execute(stmt)).scalars().all()

    return [
        LabelResponse(
            id=lbl.id,
            organization_id=lbl.organization_id,
            name=lbl.name,
            color=lbl.color,
            created_at=lbl.created_at,
        )
        for lbl in labels
    ]


@router.patch(
    "/labels/{label_id}",
    response_model=LabelResponse,
    summary="Update Label",
    description="Updates label name or color. Requires DEVELOPER or higher.",
)
async def update_label(
    label_id: uuid.UUID,
    payload: LabelUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.DESIGNER)),
    db: AsyncSession = Depends(get_db),
) -> LabelResponse:
    label = await db.scalar(
        select(Label).where(Label.id == label_id, Label.organization_id == ctx.organization_id)
    )
    if not label:
        raise NotFoundException(f"Label '{label_id}' not found in this organization.", code="LABEL_NOT_FOUND")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if clean_name.lower() != label.name.lower():
            existing = await db.scalar(
                select(Label.id).where(
                    Label.organization_id == ctx.organization_id,
                    func.lower(Label.name) == clean_name.lower(),
                    Label.id != label.id,
                )
            )
            if existing:
                raise BadRequestException(f"Label '{clean_name}' already exists.", code="LABEL_NAME_COLLISION")
            label.name = clean_name

    if payload.color is not None:
        label.color = payload.color.strip()

    await db.commit()
    await db.refresh(label)

    return LabelResponse(
        id=label.id,
        organization_id=label.organization_id,
        name=label.name,
        color=label.color,
        created_at=label.created_at,
    )


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Label",
    description="Deletes a label from the organization. Requires MANAGER, ADMIN, or OWNER role.",
)
async def delete_label(
    label_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    label = await db.scalar(
        select(Label).where(Label.id == label_id, Label.organization_id == ctx.organization_id)
    )
    if not label:
        raise NotFoundException(f"Label '{label_id}' not found in this organization.", code="LABEL_NOT_FOUND")

    label_name = label.name
    await db.delete(label)
    await db.commit()

    return {
        "status": "success",
        "message": f"Label '{label_name}' was successfully deleted.",
        "label_id": str(label_id),
    }
