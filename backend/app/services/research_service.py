"""Research service - orchestrates search, browse, extract, and memory storage"""

import loguru
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.services.memory_service import MemoryService
from app.services.browser_service import browser_service
from app.services.search_service import search_service
from app.models.memory import MemoryItem, KnowledgeItem, KnowledgeSource
from sqlalchemy import select

logger = loguru.logger


class ResearchService:
    """
    Research workflow: search → browse → extract → verify → store.
    
    Every result is treated as untrusted until verified through
    multiple-source evaluation. Source provenance is always preserved.
    """

    def __init__(self):
        self.max_sources_per_query = 5
        self.min_credibility_for_knowledge = 0.6

    async def research_topic(
        self,
        query: str,
        store_as_memory: bool = True,
        store_as_knowledge: bool = False,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Full research workflow for a topic.
        
        Steps:
        1. Search for relevant sources
        2. Browse top results
        3. Extract content and metadata
        4. Evaluate source credibility
        5. Store findings in memory (and optionally as knowledge)
        
        Returns comprehensive research record with source provenance.
        """
        research_record = {
            "query": query,
            "started_at": datetime.utcnow().isoformat(),
            "sources": [],
            "findings": [],
            "summary": None,
            "credibility_score": 0.0,
        }

        async with AsyncSessionLocal() as db:
            memory_service = MemoryService(db)

            # Step 1: Search
            search_results = await search_service.search(query, max_results=max_results)
            raw_results = search_results.get("results", [])

            # If using DuckDuckGo via browser, do browser search
            if not raw_results and search_results.get("provider") == "duckduckgo":
                raw_results = await browser_service.search_duckduckgo(query, max_results)

            # Step 2-4: Browse top sources, extract, evaluate
            for idx, result in enumerate(raw_results[: self.max_sources_per_query]):
                url = result.get("url", "")
                if not url:
                    continue

                try:
                    page_data = await browser_service.fetch_page(
                        url,
                        extract_text=True,
                        extract_links=False,
                        extract_metadata=True,
                    )

                    if not page_data.get("success"):
                        continue

                    # Evaluate credibility (simple heuristic based on metadata)
                    credibility = self._evaluate_credibility(page_data, result)

                    source_record = {
                        "index": idx,
                        "url": url,
                        "title": page_data.get("title") or result.get("title", ""),
                        "snippet": result.get("description", "") or result.get("snippet", ""),
                        "credibility_score": credibility,
                        "fetched_at": page_data.get("fetched_at"),
                        "metadata": page_data.get("metadata", {}),
                    }
                    research_record["sources"].append(source_record)

                    # Step 5: Store in memory
                    if store_as_memory and page_data.get("text"):
                        content = page_data["text"][:4000]  # Truncate for storage
                        await memory_service.store_memory(
                            content=content,
                            memory_type="fact",
                            source=url,
                            confidence_level=credibility,
                            topic=query,
                            metadata_={
                                "title": source_record["title"],
                                "research_query": query,
                                "source_index": idx,
                                "credibility_score": credibility,
                            },
                        )

                        research_record["findings"].append({
                            "source": url,
                            "title": source_record["title"],
                            "content_preview": content[:300],
                            "credibility_score": credibility,
                        })

                    # Store as knowledge if credibility is high enough
                    if store_as_knowledge and credibility >= self.min_credibility_for_knowledge:
                        knowledge = KnowledgeItem(
                            title=source_record["title"],
                            content=page_data.get("text", "")[:4000],
                            source=url,
                            confidence_level=credibility,
                            verification_status="unverified",
                            topic=query,
                            metadata_={
                                "research_query": query,
                                "source_index": idx,
                                "discovered_via": "autonomous_research",
                            },
                        )
                        db.add(knowledge)
                        await db.flush()

                        knowledge_source = KnowledgeSource(
                            knowledge_item_id=knowledge.id,
                            url=url,
                            title=source_record["title"],
                            credibility_score=credibility,
                        )
                        db.add(knowledge_source)

                except Exception as e:
                    logger.error(f"Research error for {url}: {e}")
                    continue

            if store_as_knowledge:
                await db.commit()

            # Calculate overall credibility
            if research_record["sources"]:
                scores = [s["credibility_score"] for s in research_record["sources"]]
                research_record["credibility_score"] = sum(scores) / len(scores)

            research_record["completed_at"] = datetime.utcnow().isoformat()
            research_record["source_count"] = len(research_record["sources"])

        return research_record

    def _evaluate_credibility(
        self, page_data: Dict[str, Any], search_result: Dict[str, Any]
    ) -> float:
        """
        Evaluate source credibility using heuristic signals.
        
        Factors: HTTPS, domain reputation hints, metadata presence,
        content length, search result position.
        """
        score = 0.5  # Base neutral score

        url = page_data.get("url", "")
        metadata = page_data.get("metadata", {})
        text_length = len(page_data.get("text", "") or "")

        # HTTPS
        if url.startswith("https://"):
            score += 0.1

        # Has description metadata
        if metadata.get("description"):
            score += 0.1

        # Has author metadata
        if metadata.get("author"):
            score += 0.1

        # Substantial content
        if text_length > 1000:
            score += 0.1
        if text_length > 5000:
            score += 0.1

        # Known trustworthy domains (heuristic)
        trusted_domains = [
            "wikipedia.org", "britannica.com", "nature.com", "science.org",
            "nih.gov", "who.int", "nasa.gov", "nih.gov", "cdc.gov",
            "edu", "gov", "org",
        ]
        for domain in trusted_domains:
            if domain in url:
                score += 0.1
                break

        return min(score, 1.0)

    async def verify_knowledge_against_sources(
        self, knowledge_id: str
    ) -> Dict[str, Any]:
        """
        Cross-reference a knowledge item against multiple sources
        to verify or dispute its claims.
        
        Returns verification result with supporting/contradicting sources.
        """
        # Placeholder for multi-source verification workflow
        # In production, this would search for the knowledge topic,
        # browse sources, and compare claims.
        return {
            "knowledge_id": knowledge_id,
            "verification_status": "unverified",
            "supporting_sources": [],
            "contradicting_sources": [],
            "note": "Multi-source verification workflow to be implemented",
        }


# Singleton instance
research_service = ResearchService()
