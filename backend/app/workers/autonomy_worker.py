"""Autonomy worker - background operational loop (Phase 3)

Continuous decision-making engine that observes, reasons, plans, and acts.
States: idle, exploring, learning, working, developing, reviewing, conserving
"""

import asyncio
import json
import loguru
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.services.model_inference import InferenceUnavailable, inference_service
from app.core.database import AsyncSessionLocal
from app.services.memory_service import MemoryService
from app.models.memory import MemoryItem
from app.models.autonomy import Goal, Task, DecisionRecord
from sqlalchemy import select

logger = loguru.logger


class AutonomyWorker:
    """
    Continuous operational loop for autonomous decision-making.

    The worker cycles through states, never calling the model every second.
    It sleeps between ticks to conserve resources.
    """

    def __init__(self, tick_interval: int = 30) -> Any:
        self.tick_interval = tick_interval
        self.state = "idle"
        self.running = False
        self.last_cycle: Optional[Dict[str, Any]] = None
        self._task: Optional[asyncio.Task] = None
        self._ticks = 0

    async def start(self) -> Any:
        """Start the autonomy loop as a background task."""
        self.running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Autonomy worker started")

    async def stop(self) -> Any:
        """Stop the autonomy loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Autonomy worker stopped")

    async def _loop(self) -> Any:
        """Main autonomy loop — uses the durable LangGraph workflow when available."""
        while self.running:
            try:
                durable = None
                try:
                    from app.orchestration.autonomy_graph import run_cycle
                    durable = await run_cycle(trigger="scheduled")
                    self.last_cycle = durable
                    if durable.get("action", {}).get("status") == "advanced":
                        self.state = "working"
                    else:
                        self.state = "idle"
                except Exception as ge:
                    logger.warning(f"Durable graph unavailable, using simple tick: {ge}")
                    await self._tick()

                # Periodic free-infrastructure quota/expiry monitor (Doc 22).
                self._ticks += 1
                if (
                    getattr(settings, "free_sandboxes_enabled", False)
                    and self._ticks
                    % max(getattr(settings, "free_sandbox_discovery_interval_ticks", 10), 1)
                    == 0
                ):
                    try:
                        from app.services.free_sandboxes.monitor import FreeSandboxMonitor
                        from app.services.free_sandboxes.service import FreeSandboxService

                        async with AsyncSessionLocal() as sandbox_db:
                            outcomes = await FreeSandboxMonitor(
                                FreeSandboxService(sandbox_db, actor="autonomy_worker")
                            ).poll()
                            if outcomes:
                                logger.info(f"Free sandbox quota poll: {len(outcomes)} providers")
                    except Exception as monitor_error:
                        logger.warning(f"Free sandbox monitor unavailable: {monitor_error}")

                # Also record a heartbeat decision for operational visibility
                async with AsyncSessionLocal() as db:
                    db.add(DecisionRecord(
                        decision="autonomy_heartbeat",
                        reasoning=durable.get("reasoning") if durable else "simple loop",
                        confidence=0.5,
                    ))
                    await db.commit()
            except Exception as e:
                logger.error(f"Autonomy tick error: {e}")
                self.state = "conserving"
            await asyncio.sleep(self.tick_interval)

    async def _tick(self) -> Any:
        """One iteration of the autonomy loop.

        Steps:
        1. Observe environment (check for new conversations, unprocessed items)
        2. Retrieve relevant memories
        3. Reason and evaluate (via model gateway)
        4. Identify goals/opportunities
        5. Check permissions and policies
        6. Execute action or request authorization
        7. Record decision
        8. Reflect and learn / update memory
        """
        async with AsyncSessionLocal() as db:
            # 1. Observe environment
            recent_messages = await self._observe(db)
            if not recent_messages:
                self.state = "idle"
                return

            self.state = "exploring"

            # 2. Retrieve relevant memories
            memory_service = MemoryService(db)
            relevant_memories = await memory_service.search_memory(
                query=recent_messages[-1]["content"],
                limit=5,
            )

            # 3. Reason and evaluate via the LiteLLM model gateway
            self.state = "working"
            decision = await self._reason(recent_messages[-1], relevant_memories, db)

            # 4. Record decision
            decision_record = DecisionRecord(
                decision=decision.get("action", "observe"),
                reasoning=decision.get("reasoning", ""),
                confidence=decision.get("confidence", 0.5),
            )
            db.add(decision_record)
            await db.commit()

            # 5. Reflect and learn - store the outcome as memory
            await memory_service.store_memory(
                content=f"Decided to {decision.get('action', 'observe')}: {decision.get('reasoning', '')}",
                memory_type="experience",
                source="autonomy-worker",
                confidence=decision.get("confidence", 0.5),
                topic="decision-making",
            )

            self.state = "reviewing"
            logger.info(f"Autonomy tick complete: {decision.get('action', 'observe')}")

    async def _observe(self, db: AsyncSessionLocal) -> List[Dict[str, Any]]:
        """Check for new unprocessed conversation messages."""
        from app.models.memory import ConversationMessage
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.role == "user")
            .order_by(ConversationMessage.created_at.desc())
            .limit(5)
        )
        messages = result.scalars().all()
        return [
            {
                "id": str(m.id),
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

    async def _reason(
        self,
        message: Dict[str, Any],
        memories: List[Dict[str, Any]],
        db: Any,
    ) -> Dict[str, Any]:
        """Reason about the next action through the LiteLLM model gateway."""
        memory_context = "\n".join(
            [f"- {m.get('content', '')[:100]}..." for m in memories[:3]]
        ) if memories else "No relevant memories."

        system_prompt = (
            "You are IAM's autonomy worker. Choose one safe next action: "
            "observe, respond, research, plan or ask_authorization. "
            "Never grant yourself permissions or spend funds. "
            'Return JSON only: {"action": str, "reasoning": str, "confidence": number 0-1}.'
        )
        user_prompt = (
            f"Latest user message: {message.get('content', '')[:500]}\n"
            f"Relevant memories: {memory_context[:500]}"
        )

        try:
            status = await inference_service.resolve()
            if not status.available:
                raise InferenceUnavailable(status.reason)
            result = await inference_service.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=256,
                timeout=60.0,
                db=db,
            )
            content = result["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:].strip()
            try:
                decision = json.loads(content)
            except json.JSONDecodeError:
                start, end = content.find("{"), content.rfind("}")
                if start < 0 or end <= start:
                    raise
                decision = json.loads(content[start : end + 1])
            action = str(decision.get("action", "observe"))
            allowed = {"observe", "respond", "research", "plan", "ask_authorization"}
            if action not in allowed:
                action = "observe"
            confidence = max(0.0, min(1.0, float(decision.get("confidence", 0.5))))
            return {
                "action": action,
                "reasoning": str(decision.get("reasoning", ""))[:1000],
                "confidence": confidence,
                "model_used": True,
                "inference_mode": status.mode,
                "model": result.get("iam_inference", {}).get("model"),
            }
        except Exception as exc:
            # Never fabricate a decision or silently claim model reasoning.
            logger.warning(f"Model reasoning unavailable: {exc}")
            return {
                "action": "observe",
                "reasoning": (
                    f"model unavailable; no autonomous action taken: "
                    f"{type(exc).__name__}: {exc}"
                )[:1000],
                "confidence": 0.0,
                "model_used": False,
                "inference_mode": "offline",
            }


# Singleton instance
autonomy_worker = AutonomyWorker(tick_interval=30)
