from fastapi import APIRouter, status

from app.core.config import settings
from app.database.connection import check_database_connection
from app.schemas.health import HealthCheckResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Liveness probe returning application operational status and version.",
)
async def health_check() -> HealthCheckResponse:
    """
    Returns application liveness status:
    - status: 'healthy'
    - application: 'FLOWSTATE'
    - version: '1.0.0'
    """
    return HealthCheckResponse(
        status="healthy",
        application=settings.APP_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Readiness Probe",
    description="Readiness probe evaluating downstream dependencies including Supabase PostgreSQL.",
)
async def readiness_check() -> ReadinessResponse:
    """
    Evaluates whether the service is ready to accept traffic.
    Checks the database connection without pretending it is connected if unconfigured.
    """
    is_connected, db_status, details = await check_database_connection()
    readiness_status = "ready" if is_connected else "not_ready"

    return ReadinessResponse(
        status=readiness_status,
        database=db_status,
        details=details,
    )
