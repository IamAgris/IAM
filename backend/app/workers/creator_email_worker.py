"""Background retry worker for Creator approval email delivery.

This is a lightweight async loop rather than ARQ (OD-08) so it has no extra
dependency. It only calls CreatorApprovalService.retry_failed_deliveries(), which
re-verifies configuration and never creates authority.
"""

import asyncio

import loguru

from app.core.config import settings
from app.core.database import get_session_factory
from app.services.creatorapproval_service import CreatorApprovalService

logger = loguru.logger


class CreatorEmailWorker:
    def __init__(self, interval: int | None = None):
        self.interval = interval or settings.creator_email_retry_interval_seconds
        self.state = "stopped"
        self._task: asyncio.Task | None = None

    async def _cycle(self) -> None:
        async with get_session_factory()() as db:
            results = await CreatorApprovalService(db).retry_failed_deliveries()
        if results:
            logger.info("Creator email retry cycle processed {} entries", len(results))

    async def _loop(self) -> None:
        while True:
            try:
                await self._cycle()
            except Exception as exc:
                logger.warning("Creator email retry cycle failed: {}", type(exc).__name__)
            await asyncio.sleep(self.interval)

    async def start(self) -> None:
        if not settings.creator_email_worker_enabled:
            logger.info("Creator email worker disabled")
            return
        if self._task and not self._task.done():
            return
        self.state = "running"
        self._task = asyncio.create_task(self._loop())
        logger.info("Creator email worker started (interval {}s)", self.interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self.state = "stopped"
        logger.info("Creator email worker stopped")


creator_email_worker = CreatorEmailWorker()
