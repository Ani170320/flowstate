import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.connection import close_database_connections
from app.routes.activities import router as activities_router
from app.routes.ai import router as ai_router
from app.routes.attachments import router as attachments_router
from app.routes.auth import router as auth_router
from app.routes.calendar import router as calendar_router
from app.routes.comments import router as comments_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.labels import router as labels_router
from app.routes.notifications import router as notifications_router
from app.routes.organizations import router as organizations_router
from app.routes.projects import router as projects_router
from app.routes.tasks import router as tasks_router
from app.routes.teams import router as teams_router

# Configure logging format and level
logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("flowstate.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown events.
    Handles resource allocation, pool initialization, and graceful cleanup.
    """
    logger.info(
        "Starting %s v%s [Environment: %s, Debug: %s]",
        settings.APP_NAME,
        settings.VERSION,
        settings.APP_ENV,
        settings.APP_DEBUG,
    )
    yield
    logger.info("Shutting down %s API...", settings.APP_NAME)
    await close_database_connections()
    logger.info("Graceful shutdown complete.")


# Initialize FastAPI instance
app = FastAPI(
    title="FLOWSTATE API",
    description="Scalable backend foundation for FLOWSTATE project management & collaboration SaaS.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Centralized Exception Handling
register_exception_handlers(app)

# Cross-Origin Resource Sharing (CORS) Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register API Routers under /api/v1
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(organizations_router, prefix=settings.API_V1_PREFIX)
app.include_router(teams_router, prefix=settings.API_V1_PREFIX)
app.include_router(projects_router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks_router, prefix=settings.API_V1_PREFIX)
app.include_router(labels_router, prefix=settings.API_V1_PREFIX)
app.include_router(comments_router, prefix=settings.API_V1_PREFIX)
app.include_router(attachments_router, prefix=settings.API_V1_PREFIX)
app.include_router(activities_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(calendar_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG,
    )
