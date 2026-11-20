from typing import Optional
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Schema for basic application liveness health check."""

    status: str = Field(..., description="Overall health status of the application", examples=["healthy"])
    application: str = Field(..., description="Application name", examples=["FLOWSTATE"])
    version: str = Field(..., description="API semantic version", examples=["1.0.0"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "application": "FLOWSTATE",
                "version": "1.0.0",
            }
        }
    }


class ReadinessResponse(BaseModel):
    """Schema for application readiness probe (checks dependencies like database)."""

    status: str = Field(..., description="Readiness status ('ready', 'not_ready')", examples=["not_ready"])
    database: str = Field(..., description="Database connection state ('connected', 'disconnected', 'unconfigured')", examples=["unconfigured"])
    details: Optional[str] = Field(None, description="Descriptive status details", examples=["Database URL is not configured."])

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "not_ready",
                "database": "unconfigured",
                "details": "Database URL is not configured. Backend foundation is operational.",
            }
        }
    }
