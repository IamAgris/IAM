"""ARQ worker for Creator email delivery retries (OD-08).

Run as a separate process:

    arq app.workers.arq_creator_email.WorkerSettings

The FastAPI in-process loop is used when CREATOR_EMAIL_WORKER_BACKEND=loop.
"""

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import get_session_factory
from app.services.creatorapproval_service import CreatorApprovalService


async def retry_creator_email(ctx) -> dict:
    """Retry all non-dead-lettered Creator email deliveries."""
    async with get_session_factory()() as db:
        results = await CreatorApprovalService(db).retry_failed_deliveries()
    return {"processed": len(results)}


class WorkerSettings:
    functions = [retry_creator_email]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 60
    max_jobs = 10
    health_check_interval = 300
