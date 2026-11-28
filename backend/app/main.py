"""Project AURA - Main FastAPI Application Entry Point"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Any
import loguru

from app.core.config import settings
from app.core.database import engine, Base
from app.api.deps import get_db_session
from app.api.middleware import (
    AuthMiddleware,
    ConversationOwnerMiddleware,
    IPLCIContextMiddleware,
)
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.middleware.observability import ObservabilityMiddleware
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
    modelcredentials,
    modeldiscovery,
    skillforge,
    cybersecurity,
    creatorapproval,
    auth,
    skillruntime,
    browser,
    browser_intelligence,
    browser_security,
    browser_knowledge,
    browser_agents,
    browser_lifecycle,
    tor,
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
    iplci,
    creator_communication,
    user_email,
    geo,
    freesandboxes,
    humanpresence,
    assistantlab,
    events,
    ops,
    emergency,
    workspaces,
    whitehat,
    irwm,
    provider_compat,
    modelindependence,
    financial_adapters,
    financial_intelligence,
    digitalassets,
    socialpresence,
    assistance,
    computer_use,
    mobile,
    websitecredentials,
    mfa,
    web_knowledge,
    web_account,
    digital_reputation,
    web_consent,
    digital_security,
    autonomous_web_task,
    browser_infrastructure,
    ai_communication,
    hbi,
    iics,
    live_information,
    technology_registry,
    freenodes,
    web3,
    web3_extended,
)
from app.workers.autonomy_worker import autonomy_worker
from app.workers.creator_email_worker import creator_email_worker


logger = loguru.logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan: startup and shutdown."""
    logger.info("Starting Project AURA backend...")

    from app.core.secrets import enforce_secret_policy
    from app.services.p2p_transport import transport

    enforce_secret_policy()
    from app.core.observability import configure_tracing

    trace_state = configure_tracing()
    if trace_state.get("enabled"):
        logger.info("OTLP tracing enabled")
    transport.configure(
        settings.iam_node_id,
        settings.iam_p2p_secret,
        state_path=settings.p2p_state_path or None,
    )
    logger.info(f"P2P node identity configured: {settings.iam_node_id}")

    # Development convenience only: production schema comes from Alembic.
    if settings.create_all_enabled:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized from ORM metadata (development).")
    else:
        logger.info("Production mode: schema managed by Alembic migrations.")

    # Initialize IAM identity, constitution and default policies (idempotent)
    from app.core.database import AsyncSessionLocal
    from app.services.bootstrap_service import BootstrapService
    async with AsyncSessionLocal() as session:
        await BootstrapService(session).initialize_all()
        from app.services.iics import register_iics_tools
        from app.services.iam_tool_manifest import register_core_tools

        await register_iics_tools(session)
        await register_core_tools(session)
    logger.info("IAM identity, policies, IICS tools and core IAM tools initialized.")

    # Restore durable emergency state before starting any autonomous work.
    from app.services.emergency_shutdown import emergency

    await emergency.load()
    if emergency.is_halted():
        logger.warning("Emergency stop active at startup — autonomous work stays halted")
    else:
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

# Correlation id first so CORS and auth responses carry X-Request-ID.
app.add_middleware(RequestContextMiddleware)

# Spans and request/error counters exported through /metrics.
app.add_middleware(ObservabilityMiddleware)

# Server-issued owner token scopes public conversations without client changes.
app.add_middleware(ConversationOwnerMiddleware)

# IPLCI governance context propagates from request headers to all downstream calls.
app.add_middleware(IPLCIContextMiddleware)

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
app.include_router(live_information.router)
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
app.include_router(modelcredentials.router)
app.include_router(modeldiscovery.router)
app.include_router(skillforge.router)
app.include_router(cybersecurity.router)
app.include_router(creatorapproval.router)
app.include_router(auth.router)
app.include_router(skillruntime.router)
app.include_router(browser.router)
app.include_router(browser_intelligence.router)
app.include_router(browser_security.router)
app.include_router(browser_knowledge.router)
app.include_router(browser_agents.router)
app.include_router(browser_lifecycle.router)
app.include_router(tor.router)
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
app.include_router(iplci.router)
app.include_router(creator_communication.router)
app.include_router(user_email.router)
app.include_router(geo.router)
app.include_router(freesandboxes.router)
app.include_router(humanpresence.router)
app.include_router(assistantlab.router)
app.include_router(events.router)
app.include_router(workspaces.router)
app.include_router(whitehat.router)
app.include_router(irwm.router)
app.include_router(provider_compat.router)
app.include_router(modelindependence.router)
app.include_router(financial_adapters.blockchain_router)
app.include_router(financial_adapters.banking_router)
app.include_router(financial_adapters.trading_router)
app.include_router(financial_intelligence.prediction_markets_router)
app.include_router(financial_intelligence.gaming_intelligence_router)
app.include_router(financial_intelligence.investment_intelligence_router)
app.include_router(financial_intelligence.provider_registry_router)
app.include_router(digitalassets.router)
app.include_router(socialpresence.router)
app.include_router(assistance.router)
app.include_router(computer_use.router)
app.include_router(mobile.router)
app.include_router(websitecredentials.router)
app.include_router(mfa.router)
app.include_router(ai_communication.router)
app.include_router(web_knowledge.router)
app.include_router(web_account.router)
app.include_router(digital_reputation.router)
app.include_router(web_consent.router)
app.include_router(digital_security.router)
app.include_router(autonomous_web_task.router)
app.include_router(browser_infrastructure.router)
app.include_router(hbi.router)
app.include_router(iics.router)
app.include_router(technology_registry.router)
app.include_router(freenodes.router)
app.include_router(web3.web3_router)
app.include_router(web3.nodes_router)
app.include_router(web3_extended.router)

# Operational endpoints from docs/IAM_API_CONTRACTS.md section 11 (no /api/v1 prefix)
app.include_router(ops.router)
app.include_router(emergency.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> Any:
    from app.core.error_response import error_response

    logger.error(f"Unhandled exception: {exc}")
    return error_response(
        request=request,
        status_code=500,
        detail="Internal server error",
        code="internal_error",
        error=str(exc) if settings.app_debug else None,
    )


# Health check
@app.get("/health")
async def health_check() -> Any:
    return {"status": "healthy", "service": "aura-backend", "version": "0.1.0"}


# Root
@app.get("/")
async def root() -> Any:
    return {
        "name": "Project AURA",
        "description": "Autonomous Unified Reasoning Architecture",
        "version": "0.1.0",
        "status": "operational",
    }
