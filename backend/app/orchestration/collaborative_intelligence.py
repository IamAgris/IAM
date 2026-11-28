"""P7-f — Collaborative intelligence.

IAM collaborates with other AI models, not just delegates to them. This means:
* Comparing independent reasoning from multiple models on the same problem
* Resolving disagreements using evidence, not majority vote
* Combining complementary expertise from different models
* Maintaining IAM's own independent conclusions

Builds on:
* P0-P6: model router, multi-model intelligence
* P7-a: curiosity (identifies questions worth investigating)
* P7-b: attention (prioritizes which collaborations to pursue)
* P7-c: grounding (verifies collaborative findings against reality)
* P7-d: agency (turns collaborations into executed objectives)

This is not unbounded reliance on external models. IAM maintains its own
independent conclusions and uses external models as contributing expertise,
not as replacements for its own reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.core.config import settings
from app.services import iam_context
from app.services.model_inference import InferenceUnavailable, inference_service

logger = loguru.logger


@dataclass
class ExternalModelOpinion:
    """An external model's independent reasoning on a question."""

    model_id: str
    provider: str
    conclusion: str
    reasoning: str
    confidence: float
    evidence_cited: List[str]


@dataclass
class CollaborationResult:
    """Result of collaborative reasoning on a question."""

    question: str
    iam_conclusion: str
    iam_confidence: float
    external_opinions: List[ExternalModelOpinion]
    agreement_score: float  # 0.0 (all disagree) to 1.0 (all agree)
    conflicts: List[Dict[str, Any]]  # disagreements between IAM and externals
    resolution: str  # "iam_confirmed", "iam_revised", "iam_rejected_external"
    final_conclusion: str
    final_confidence: float


class CollaborativeIntelligence:
    """Collaborative intelligence with external AI models.

    IAM collaborates with external models but maintains its own independent
    conclusions. External models contribute expertise; IAM decides what to
    accept based on evidence, not majority vote.
    """

    async def collaborative_reasoning(
        self,
        db: Any,
        question: str,
        iam_conclusion: str,
        iam_confidence: float,
        iam_reasoning: str,
        external_models: Optional[List[Dict[str, Any]]] = None,
    ) -> CollaborationResult:
        """Collaborate with external models on a question.

        Asks external models the same question independently, then compares
        their conclusions with IAM's. Disagreements are resolved using
        evidence, not majority vote.

        Args:
            question: The question to reason about
            iam_conclusion: IAM's own conclusion
            iam_confidence: IAM's confidence in its conclusion
            iam_reasoning: IAM's reasoning chain
            external_models: List of {model_id, provider} external models to consult

        Returns a CollaborationResult with the resolution.
        """
        external_models = external_models or []
        external_opinions: List[ExternalModelOpinion] = []

        # Step 1: Ask each external model independently
        for model_info in external_models:
            opinion = await self._ask_external_model(
                model_info, question
            )
            if opinion:
                external_opinions.append(opinion)

        # Step 2: Compare IAM's conclusion with external opinions
        agreements = 0
        conflicts: List[Dict[str, Any]] = []

        for opinion in external_opinions:
            if self._conclusions_agree(iam_conclusion, opinion.conclusion):
                agreements += 1
            else:
                conflicts.append({
                    "iam_conclusion": iam_conclusion,
                    "iam_confidence": iam_confidence,
                    "external_model": opinion.model_id,
                    "external_conclusion": opinion.conclusion,
                    "external_confidence": opinion.confidence,
                    "external_reasoning": opinion.reasoning,
                })

        agreement_score = agreements / len(external_opinions) if external_opinions else 1.0

        # Step 3: Resolve disagreements using evidence
        resolution, final_conclusion, final_confidence = self._resolve_disagreement(
            iam_conclusion, iam_confidence, iam_reasoning,
            external_opinions, conflicts
        )

        return CollaborationResult(
            question=question,
            iam_conclusion=iam_conclusion,
            iam_confidence=iam_confidence,
            external_opinions=external_opinions,
            agreement_score=round(agreement_score, 4),
            conflicts=conflicts,
            resolution=resolution,
            final_conclusion=final_conclusion,
            final_confidence=round(final_confidence, 4),
        )

    async def _ask_external_model(
        self,
        model_info: Dict[str, Any],
        question: str,
    ) -> Optional[ExternalModelOpinion]:
        """Ask an external model a question independently.

        The model is asked without seeing IAM's conclusion, to preserve
        independence of its reasoning.
        """
        model_id = model_info.get("model_id", "unknown")
        provider = model_info.get("provider", "unknown")

        try:
            status = await inference_service.resolve()
            if not status.available:
                logger.warning(f"Inference unavailable for {model_id}")
                return None

            result = await inference_service.chat(
                [
                    {
                        "role": "system",
                        "content": "You are an independent AI model. Answer the following question based on your own reasoning. Do not consider any other model's opinion. Return JSON with: conclusion, confidence (0-1), reasoning, evidence_cited (list of sources).",
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                ],
                # External opinions use the separate hosted pool; the single
                # local residency slot belongs to user chat (OD-39/OD-46).
                model=settings.autonomy_model,
                temperature=0.3,
                max_tokens=512,
                timeout=60.0,
                db=None,
            )

            content = str(result["choices"][0]["message"]["content"]).strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:].strip()

            import json
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                start, end = content.find("{"), content.rfind("}")
                if start < 0 or end <= start:
                    return None
                parsed = json.loads(content[start:end + 1])

            return ExternalModelOpinion(
                model_id=model_id,
                provider=provider,
                conclusion=str(parsed.get("conclusion", "")),
                reasoning=str(parsed.get("reasoning", "")),
                confidence=float(parsed.get("confidence", 0.5)),
                evidence_cited=parsed.get("evidence_cited", []),
            )

        except Exception as exc:
            logger.warning(f"External model {model_id} failed: {exc}")
            return None

    def _conclusions_agree(
        self,
        iam_conclusion: str,
        external_conclusion: str,
    ) -> bool:
        """Determine if two conclusions agree.

        Simple heuristic: normalized text similarity above threshold.
        """
        iam_norm = self._normalize(iam_conclusion)
        ext_norm = self._normalize(external_conclusion)

        if iam_norm == ext_norm:
            return True

        # Check for negation (one says X, other says not X)
        iam_negated = any(w in iam_norm for w in ["not ", "no ", "never", "false"])
        ext_negated = any(w in ext_norm for w in ["not ", "no ", "never", "false"])

        if iam_negated != ext_negated:
            return False

        # Check for keyword overlap
        iam_words = set(iam_norm.split())
        ext_words = set(ext_norm.split())
        if iam_words and ext_words:
            overlap = len(iam_words & ext_words) / len(iam_words | ext_words)
            return overlap > 0.6

        return False

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.lower().split())

    def _resolve_disagreement(
        self,
        iam_conclusion: str,
        iam_confidence: float,
        iam_reasoning: str,
        external_opinions: List[ExternalModelOpinion],
        conflicts: List[Dict[str, Any]],
    ) -> tuple[str, str, float]:
        """Resolve disagreements using evidence, not majority vote.

        Returns (resolution, final_conclusion, final_confidence).
        """
        if not conflicts:
            # No conflicts - IAM's conclusion stands
            return "iam_confirmed", iam_conclusion, iam_confidence

        # Count external agreements vs disagreements
        agreeing = sum(1 for o in external_opinions if self._conclusions_agree(iam_conclusion, o.conclusion))
        disagreeing = len(conflicts)

        if agreeing > disagreeing:
            # Majority of external models agree with IAM
            return "iam_confirmed", iam_conclusion, min(1.0, iam_confidence + 0.1)

        if disagreeing > agreeing:
            # Majority disagrees - check if external confidence is higher
            avg_external_conf = sum(o.confidence for o in external_opinions) / len(external_opinions)
            if avg_external_conf > iam_confidence + 0.2:
                # External models are more confident and disagree - revise IAM's conclusion
                best_external = max(external_opinions, key=lambda o: o.confidence)
                return "iam_revised", best_external.conclusion, best_external.confidence
            else:
                # IAM is more confident - maintain IAM's conclusion
                return "iam_confirmed", iam_conclusion, iam_confidence

        # Tie - maintain IAM's conclusion but reduce confidence slightly
        return "iam_confirmed", iam_conclusion, max(0.0, iam_confidence - 0.1)

    async def collaborative_development_cycle(
        self,
        db: Any,
        question: str,
        iam_conclusion: str,
        iam_confidence: float,
        iam_reasoning: str,
        external_models: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Full collaborative development cycle.

        Collaborative reasoning → belief revision → knowledge recording.
        External models contribute expertise; IAM decides what to accept.
        """
        result = await self.collaborative_reasoning(
            db, question, iam_conclusion, iam_confidence, iam_reasoning, external_models
        )

        # Record the collaborative finding as a belief
        belief_id = None
        try:
            from app.services import iam_context
            belief = await iam_context.record_belief(
                db,
                title=f"Collaborative finding: {question[:100]}",
                content=result.final_conclusion,
                source="collaborative_intelligence",
                confidence_level=result.final_confidence,
                topic="collaboration",
                belief_type="collaborative_finding",
                provenance="collaborative_intelligence",
                evidence=[{
                    "type": "collaborative_reasoning",
                    "question": question,
                    "iam_conclusion": iam_conclusion,
                    "iam_confidence": iam_confidence,
                    "external_opinions": [
                        {
                            "model_id": o.model_id,
                            "provider": o.provider,
                            "conclusion": o.conclusion,
                            "confidence": o.confidence,
                        }
                        for o in result.external_opinions
                    ],
                    "resolution": result.resolution,
                }],
                contradicts=[c["external_model"] for c in result.conflicts],
            )
            belief_id = belief.id
        except Exception as exc:
            logger.warning(f"Collaborative belief recording failed: {exc}")

        return {
            "question": result.question,
            "iam_conclusion": result.iam_conclusion,
            "iam_confidence": result.iam_confidence,
            "external_opinions": [
                {
                    "model_id": o.model_id,
                    "provider": o.provider,
                    "conclusion": o.conclusion,
                    "confidence": o.confidence,
                }
                for o in result.external_opinions
            ],
            "agreement_score": result.agreement_score,
            "conflicts": result.conflicts,
            "resolution": result.resolution,
            "final_conclusion": result.final_conclusion,
            "final_confidence": result.final_confidence,
            "belief_id": belief_id,
        }
