"""Validation for P0.2 shared epistemic state (temporary, will be removed)."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.memory import KnowledgeItem
from app.services import iam_context


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(KnowledgeItem.__table__.create)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        # Record two beliefs
        b1 = await iam_context.record_belief(
            db,
            title="Bitcoin is digital gold",
            content="BTC is a store of value",
            source="research:wikipedia",
            confidence_level=0.8,
            topic="crypto",
            belief_type="factual",
            provenance="research",
            evidence=[{"source": "wikipedia", "url": "https://en.wikipedia.org/wiki/Bitcoin", "confidence": 0.9}],
        )
        assert b1.verification_status == "unverified"
        assert b1.confidence_level == 0.8
        assert len(b1.evidence) == 1
        print("Created belief 1:", b1.id[:8], b1.verification_status)

        # Re-record same title+source -> should revise, not duplicate
        b2 = await iam_context.record_belief(
            db,
            title="Bitcoin is digital gold",
            content="BTC is a store of value",
            source="research:wikipedia",
            confidence_level=0.9,
            topic="crypto",
            belief_type="factual",
            provenance="research",
        )
        assert b2.id == b1.id, "should revise existing belief"
        assert b2.confidence_level == 0.9
        print("Revised same belief (same id):", b2.id[:8])

        # Record a contradicting belief
        b3 = await iam_context.record_belief(
            db,
            title="Bitcoin is not digital gold",
            content="BTC is speculative",
            source="research:blog",
            confidence_level=0.6,
            topic="crypto",
            belief_type="opinion",
            provenance="research",
        )
        print("Created belief 3:", b3.id[:8])

        # Link them as contradicts
        link = await iam_context.link_beliefs(
            db,
            source_belief_id=b1.id,
            target_belief_id=b3.id,
            relationship_type="contradicts",
            strength=0.9,
        )
        assert link["relationship_type"] == "contradicts"
        assert link["strength"] == 0.9
        print("Link created:", link["relationship_type"])

        # Read belief state
        beliefs = await iam_context.get_belief_state(db, topic="crypto")
        assert len(beliefs) == 2
        b1_rec = next(b for b in beliefs if b.id == b1.id)
        b3_rec = next(b for b in beliefs if b.id == b3.id)
        assert b3_rec.id in b1_rec.contradicts
        assert b1_rec.id in b3_rec.contradicts  # contradictions are symmetric
        print("Belief state count:", len(beliefs))
        for b in beliefs:
            print(f"  {b.id[:8]} status={b.verification_status} conf={b.confidence_level} deps={b.dependencies} contradicts={b.contradicts}")

        # Detect contradictions (explicit link)
        contras = await iam_context.detect_contradictions(db, topic="crypto")
        assert len(contras) >= 1
        print("Contradictions found:", len(contras))
        for c in contras:
            print(f"  {c['belief_a'].id[:8]} vs {c['belief_b'].id[:8]} reason={c['reason']}")

        # Revise belief 1 to verified -> should create status conflict too
        ok = await iam_context.revise_belief(db, b1.id, verification_status="verified", confidence_level=0.9)
        assert ok is True
        contras2 = await iam_context.detect_contradictions(db, topic="crypto")
        assert len(contras2) >= 1
        print("Contradictions after revision:", len(contras2))

        # Get belief state filtered by verification_status
        verified = await iam_context.get_belief_state(db, topic="crypto", verification_status="verified")
        assert len(verified) == 1
        assert verified[0].id == b1.id
        print("Verified beliefs count:", len(verified))

        # Test revise non-existent belief returns False
        ok2 = await iam_context.revise_belief(db, "00000000-0000-0000-0000-000000000000", verification_status="verified")
        assert ok2 is False
        print("Revise non-existent returns False: OK")

        # Test link to non-existent belief raises
        try:
            await iam_context.link_beliefs(
                db,
                source_belief_id=b1.id,
                target_belief_id="00000000-0000-0000-0000-0000-000000000000",
                relationship_type="contradicts",
            )
            assert False, "should have raised"
        except ValueError:
            print("Link to non-existent raises ValueError: OK")

    print("ALL P0.2 VALIDATIONS PASSED")


asyncio.run(main())
