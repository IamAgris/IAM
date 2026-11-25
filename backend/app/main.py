"""Project AURA - Main FastAPI Application Entry Point"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import loguru

from app.core.config import settings
from app.core.database import engine, Base
from app.api.deps import get_db_session
from app.api.middleware import AuthMiddleware
from app.api.routes import (
    identity,
    conversations,
    memory,
    autonomy,
    models,
    knowledge,
    languages,
    skills,
    goals,
    tasks,
    decisions,
    tools,
    scheduling,
    research,
    voice,
    vision,
    external_presence,
    lifemanagement,
    worldmodel,
    resilience,
    capabilities,
    governance,
    reflection,
    globalaccess,
    ownerauth,
    ainetwork,
    p2p,
    aegis,
    creator_keys,
    internetaccess,
    modelrouter,
    skillforge,
    cybersecurity,
    creatorapproval,
    auth,
    skillruntime,
    deployment,
    bootstrap,
    suggestions,
    development,
    economy,
    nodes,
    storage,
    uwaie,
    integrity,
    publicrecords,
    tone,
    legal,
    creator_communication,
    geo,
    freesandboxes,
    humanpresence,
    assistantlab,
)
from app.workers.autonomy_worker import autonomy_worker
from app.workers.creator_email_worker import creator_email_worker


logger = loguru.logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("Starting Project AURA backend...")

    from app.core.secrets import enforce_secret_policy

    enforce_secret_policy()

    # Create database tables (in production, use Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized.")

    # Initialize IAM identity, constitution and default policies (idempotent)
    from app.core.database import AsyncSessionLocal
    from app.services.bootstrap_service import BootstrapService
    async with AsyncSessionLocal() as session:
        await BootstrapService(session).initialize_all()
    logger.info("IAM identity and policies initialized.")

    # Start autonomy worker
    await autonomy_worker.start()
    logger.info("Autonomy worker started.")

    await creator_email_worker.start()

    yield

    # Shutdown
    logger.info("Shutting down Project AURA backend...")
    await creator_email_worker.stop()
    await autonomy_worker.stop()
    await engine.dispose()


app = FastAPI(
    title="Project AURA API",
    description="Autonomous Unified Reasoning Architecture - Independent AI System",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication and rate limiting (CORS stays outermost for preflight requests)
app.add_middleware(AuthMiddleware)

# API routes
app.include_router(identity.router)
app.include_router(conversations.router)
app.include_router(memory.router)
app.include_router(autonomy.router)
app.include_router(models.router)
app.include_router(knowledge.router)
app.include_router(languages.router)
app.include_router(skills.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(decisions.router)
app.include_router(tools.router)
app.include_router(scheduling.router)
app.include_router(research.router)
app.include_router(voice.router)
app.include_router(vision.router)
app.include_router(external_presence.router)
app.include_router(lifemanagement.router)
app.include_router(worldmodel.router)
app.include_router(resilience.router)
app.include_router(capabilities.router)
app.include_router(governance.router)
app.include_router(reflection.router)
app.include_router(globalaccess.router)
app.include_router(ownerauth.router)
app.include_router(ainetwork.router)
app.include_router(p2p.router)
app.include_router(aegis.router)
app.include_router(creator_keys.router)
app.include_router(internetaccess.router)
app.include_router(modelrouter.router)
app.include_router(skillforge.router)
app.include_router(cybersecurity.router)
app.include_router(creatorapproval.router)
app.include_router(auth.router)
app.include_router(skillruntime.router)
app.include_router(deployment.router)
app.include_router(bootstrap.router)
app.include_router(suggestions.router)
app.include_router(development.router)
app.include_router(economy.router)
app.include_router(nodes.router)
app.include_router(storage.router)
app.include_router(uwaie.router)
app.include_router(integrity.router)
app.include_router(publicrecords.router)
app.include_router(tone.router)
app.include_router(legal.router)
app.include_router(creator_communication.router)
app.include_router(geo.router)
app.include_router(freesandboxes.router)
app.include_router(humanpresence.router)
app.include_router(assistantlab.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.app_debug else None},
    )


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aura-backend", "version": "0.1.0"}


# Root
@app.get("/")
async def root():
    return {
        "name": "Project AURA",
        "description": "Autonomous Unified Reasoning Architecture",
        "version": "0.1.0",
        "status": "operational",
    }
