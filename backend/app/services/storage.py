import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import BadRequestException

logger = logging.getLogger("flowstate.services.storage")

# In-memory storage cache for testing / local development when live Supabase Storage is not connected
_mock_storage_objects: Dict[str, bytes] = {}


class StorageService:
    """
    Manages file uploads, deletions, validation, and URL generation for Supabase Storage.
    Supports seamless fallback to local mock storage during testing.
    """

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strips dangerous characters, path traversals, and normalizes file name."""
        base_name = os.path.basename(filename)
        cleaned = re.sub(r"[^\w\.\-_]", "_", base_name)
        return cleaned or "attachment"

    @classmethod
    def validate_file(cls, filename: str, file_size: int, mime_type: str) -> None:
        """Validates file presence, size limits, and allowed MIME types."""
        if file_size <= 0:
            raise BadRequestException(
                "File is empty. Uploaded files must have a size greater than 0 bytes.",
                code="EMPTY_FILE",
            )
        if file_size > settings.STORAGE_MAX_FILE_SIZE_BYTES:
            max_mb = settings.STORAGE_MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise BadRequestException(
                f"File size exceeds the maximum limit of {max_mb} MB.",
                code="FILE_SIZE_EXCEEDED",
            )
        if mime_type.lower() not in [m.lower() for m in settings.STORAGE_ALLOWED_MIME_TYPES]:
            raise BadRequestException(
                f"MIME type '{mime_type}' is not supported.",
                code="UNSUPPORTED_FILE_TYPE",
            )

    @classmethod
    def generate_storage_path(
        cls,
        org_id: uuid.UUID,
        task_id: uuid.UUID,
        filename: str,
    ) -> str:
        """
        Derives an organization-scoped deterministic storage path:
        `org_{org_id}/tasks/{task_id}/{unique_prefix}_{safe_filename}`
        """
        safe_name = cls.sanitize_filename(filename)
        unique_token = uuid.uuid4().hex[:12]
        return f"org_{org_id}/tasks/{task_id}/{unique_token}_{safe_name}"

    @classmethod
    async def upload_file(
        cls,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """
        Uploads binary content to Supabase Storage.
        Falls back to in-memory mock storage if Supabase credentials are not configured.
        """
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{path}"
            headers = {
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, content=content, headers=headers)
                    if response.status_code not in (200, 201):
                        logger.error(
                            "Supabase Storage upload failed with status %s: %s",
                            response.status_code,
                            response.text,
                        )
                        raise BadRequestException(
                            "Failed to upload file to storage provider.",
                            code="STORAGE_UPLOAD_ERROR",
                        )
            except httpx.RequestError as exc:
                logger.error("Storage upload network failure: %s", exc)
                raise BadRequestException(
                    "Network failure communicating with storage provider.",
                    code="STORAGE_NETWORK_ERROR",
                )
        else:
            # Fallback mock store for offline dev/test runs
            key = f"{bucket}/{path}"
            _mock_storage_objects[key] = content
            logger.info("Saved file into mock storage: %s (%d bytes)", key, len(content))

        return path

    @classmethod
    async def delete_file(cls, bucket: str, path: str) -> bool:
        """
        Removes object from Supabase Storage.
        Deletes from in-memory mock store if live Supabase is not active.
        """
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}"
            headers = {
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.request(
                        "DELETE",
                        url,
                        headers=headers,
                        json={"prefixes": [path]},
                    )
                    if response.status_code not in (200, 204):
                        logger.warning(
                            "Failed to delete storage object %s: %s",
                            path,
                            response.text,
                        )
                        return False
                    return True
            except httpx.RequestError as exc:
                logger.warning("Storage deletion network error for %s: %s", path, exc)
                return False
        else:
            key = f"{bucket}/{path}"
            _mock_storage_objects.pop(key, None)
            return True

    @classmethod
    def get_public_url(cls, bucket: str, path: str) -> str:
        """Generates publicly accessible download URL or local resource reference."""
        if settings.SUPABASE_URL:
            return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"
        return f"/api/v1/storage/{bucket}/{path}"
