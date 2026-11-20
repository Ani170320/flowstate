import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
)
from app.dependencies.database import get_db
from app.models.collaboration import Attachment
from app.models.enums import UserRole
from app.models.task import Task
from app.schemas.auth import UserProfileResponse
from app.schemas.collaboration import (
    AttachmentListResponse,
    AttachmentResponse,
)
from app.services.activity import record_activity
from app.services.storage import StorageService

logger = logging.getLogger("flowstate.routes.attachments")

router = APIRouter(tags=["Attachments"])


def can_manage_attachment(ctx: ActiveOrganizationContext, attachment: Attachment) -> bool:
    """Allows deletion if caller is the uploader, or organization Manager, Admin, or Owner."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    if attachment.uploaded_by is not None and attachment.uploaded_by == ctx.user_id:
        return True
    return False


def serialize_attachment(attachment: Attachment) -> AttachmentResponse:
    """Converts Attachment ORM model into AttachmentResponse with download URL."""
    download_url = StorageService.get_public_url(
        attachment.storage_bucket, attachment.storage_path
    )
    return AttachmentResponse(
        id=attachment.id,
        organization_id=attachment.organization_id,
        project_id=attachment.project_id,
        task_id=attachment.task_id,
        comment_id=attachment.comment_id,
        name=attachment.name,
        storage_bucket=attachment.storage_bucket,
        storage_path=attachment.storage_path,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        uploaded_by=attachment.uploaded_by,
        uploader=UserProfileResponse.model_validate(attachment.uploader) if attachment.uploader else None,
        created_at=attachment.created_at,
        download_url=download_url,
    )


# ---------------------------------------------------------------------------
# Attachments Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Task Attachment",
    description="Uploads a file to Supabase Storage and records metadata linked to a task.",
)
async def upload_attachment(
    task_id: uuid.UUID,
    file: UploadFile = File(..., description="Multipart file payload"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> AttachmentResponse:
    # 1. Verify task belongs to caller's tenant organization
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.organization_id == ctx.organization_id)
    )
    if not task:
        raise NotFoundException(
            f"Task '{task_id}' not found in active organization.",
            code="TASK_NOT_FOUND",
        )

    # 2. Read content and validate size/MIME type
    content = await file.read()
    file_size = len(content)
    filename = file.filename or "attachment"
    mime_type = file.content_type or "application/octet-stream"

    StorageService.validate_file(filename, file_size, mime_type)

    # 3. Derive organization-scoped storage path
    storage_bucket = settings.STORAGE_BUCKET
    storage_path = StorageService.generate_storage_path(
        ctx.organization_id, task.id, filename
    )

    # 4. Upload binary to Storage provider FIRST
    try:
        await StorageService.upload_file(
            bucket=storage_bucket,
            path=storage_path,
            content=content,
            content_type=mime_type,
        )
    except Exception as exc:
        logger.error("Storage upload failed: %s", exc)
        raise BadRequestException(
            "File upload to storage provider failed.",
            code="STORAGE_UPLOAD_FAILED",
        )

    # 5. Persist metadata record in PostgreSQL (with automatic rollback of storage on DB error)
    attachment_id = uuid.uuid4()
    safe_name = StorageService.sanitize_filename(filename)

    attachment = Attachment(
        id=attachment_id,
        organization_id=ctx.organization_id,
        project_id=task.project_id,
        task_id=task.id,
        comment_id=None,
        name=safe_name,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        file_size=file_size,
        mime_type=mime_type,
        uploaded_by=ctx.user_id,
    )
    db.add(attachment)

    try:
        # 6. Log audit activity
        await record_activity(
            db=db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="attachment_uploaded",
            target_type="task",
            target_id=task.id,
            target_title=attachment.name,
            project_id=task.project_id,
            details={
                "attachment_id": str(attachment.id),
                "task_id": str(task.id),
                "task_key": task.key,
                "file_size": file_size,
                "mime_type": mime_type,
            },
        )
        await db.commit()
    except Exception as exc:
        logger.error("Database commit failed for attachment. Cleaning storage: %s", exc)
        await StorageService.delete_file(storage_bucket, storage_path)
        raise

    # 7. Reload with relationships
    stmt = (
        select(Attachment)
        .options(selectinload(Attachment.uploader))
        .where(Attachment.id == attachment.id)
    )
    persisted = (await db.execute(stmt)).scalar_one()
    return serialize_attachment(persisted)


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentListResponse,
    summary="List Task Attachments",
    description="Retrieves metadata and download URLs for all files attached to a task.",
)
async def list_attachments(
    task_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> AttachmentListResponse:
    task_exists = await db.scalar(
        select(Task.id).where(Task.id == task_id, Task.organization_id == ctx.organization_id)
    )
    if not task_exists:
        raise NotFoundException(
            f"Task '{task_id}' not found in active organization.",
            code="TASK_NOT_FOUND",
        )

    stmt = (
        select(Attachment)
        .options(selectinload(Attachment.uploader))
        .where(Attachment.task_id == task_id, Attachment.organization_id == ctx.organization_id)
        .order_by(Attachment.created_at.desc())
    )
    attachments = (await db.execute(stmt)).scalars().all()

    return AttachmentListResponse(
        items=[serialize_attachment(a) for a in attachments],
        total=len(attachments),
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Attachment",
    description="Deletes attachment metadata from PostgreSQL and cleans up binary file from Supabase Storage.",
)
async def delete_attachment(
    attachment_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    attachment = await db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.organization_id == ctx.organization_id,
        )
    )
    if not attachment:
        raise NotFoundException(
            f"Attachment '{attachment_id}' not found in active organization.",
            code="ATTACHMENT_NOT_FOUND",
        )

    if not can_manage_attachment(ctx, attachment):
        raise ForbiddenException(
            "Access denied: You do not have permission to delete this attachment.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    bucket = attachment.storage_bucket
    path = attachment.storage_path
    filename = attachment.name

    # 1. Delete metadata row in PostgreSQL
    await db.delete(attachment)
    await db.commit()

    # 2. Delete binary from Supabase Storage (prevents orphaned storage object)
    await StorageService.delete_file(bucket, path)

    return {
        "status": "success",
        "message": f"Attachment '{filename}' successfully deleted from database and storage.",
        "attachment_id": str(attachment_id),
    }
