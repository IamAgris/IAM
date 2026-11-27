"""Read-only Polymarket public market-data adapter (Doc 25 Amendment A).

GET-only. No order placement, wallet funding, signing or private-key access.
Market data is recorded as *market-implied* probability only; IAM's own
probability estimates must be supplied independently by the research service.
"""

import json
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import SOUTH_AFRICA_NOTICE
from app.services.prediction_markets.service import (
    PredictionMarketDenied,
    PredictionMarketService,
)


class DataAdapterDenied(PredictionMarketDenied):
    """Raised when a data request breaks the read-only adapter boundary."""


class PolymarketDataAdapter:
    def __init__(self, db: AsyncSession, client: Optional[httpx.AsyncClient] = None):
        self.db = db
        self._client = client

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.prediction_markets_data_adapter_enabled,
            "gamma_configured": bool(settings.prediction_markets_gamma_url),
            "clob_configured": bool(settings.prediction_markets_clob_url),
            "data_api_configured": bool(settings.prediction_markets_data_url),
            "get_only": True,
            "trading_enabled": False,
            "wallet_access_enabled": False,
            "records_market_implied_probability_only": True,
            "independent_estimates_required": True,
            "max_markets_per_sync": settings.prediction_markets_max_markets,
            "south_africa_notice": SOUTH_AFRICA_NOTICE,
        }

    def status(self) -> Dict[str, Any]:
        policy = self.policy()
        configured = policy["gamma_configured"] and policy["clob_configured"]
        return {
            **policy,
            "configured": configured,
            "available": policy["enabled"] and configured,
        }

    async def fetch_markets(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read public Gamma markets and normalise the fields IAM needs."""
        count = self._market_limit(limit)
        payload = await self._get_json(
            settings.prediction_markets_gamma_url,
            "/markets",
            {"limit": count, "active": "true", "closed": "false"},
        )
        if not isinstance(payload, list):
            raise DataAdapterDenied("unexpected Gamma markets response")

        markets: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("closed") is True:
                continue
            outcomes = self._as_list(item.get("outcomes"))
            prices = self._as_list(item.get("outcomePrices"))
            if not outcomes or len(outcomes) != len(prices):
                continue
            implied = {}
            valid = True
            for outcome, raw_price in zip(outcomes, prices):
                try:
                    price = float(raw_price)
                except (TypeError, ValueError):
                    valid = False
                    break
                if not 0 <= price <= 1:
                    valid = False
                    break
                implied[str(outcome)] = price
            if not valid or not implied:
                continue
            market_ref = str(
                item.get("id") or item.get("slug") or item.get("conditionId") or ""
            )
            event_name = str(item.get("question") or item.get("title") or item.get("slug") or "")
            if not market_ref or not event_name:
                continue
            markets.append(
                {
                    "platform": "polymarket",
                    "market_ref": market_ref,
                    "event_name": event_name,
                    "outcomes": [str(value) for value in outcomes],
                    "implied_probabilities": implied,
                    "source_url": str(item.get("url") or "") or None,
                }
            )
            if len(markets) >= count:
                break
        return markets

    async def fetch_order_book(self, token_id: str) -> Dict[str, Any]:
        """Read a public CLOB snapshot — top bids/asks only, never an order."""
        self._require_enabled()
        if not token_id or not str(token_id).strip():
            raise DataAdapterDenied("token_id is required")
        book = await self._get_json(
            settings.prediction_markets_clob_url, "/book", {"token_id": str(token_id)}
        )
        if not isinstance(book, dict):
            raise DataAdapterDenied("unexpected CLOB book response")
        depth = max(1, min(int(settings.prediction_markets_book_depth), 20))
        levels = []
        for side in ("bids", "asks"):
            for entry in list(book.get(side) or [])[:depth]:
                if not isinstance(entry, dict):
                    continue
                levels.append(
                    {
                        "side": side,
                        "price": entry.get("price"),
                        "size": entry.get("size"),
                    }
                )
        return {
            "token_id": str(token_id),
            "levels": levels,
            "truncated": True,
            "read_only": True,
            "orders_placed": 0,
        }

    async def fetch_data(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Generic GET against the configured public Data API base URL."""
        self._require_enabled()
        if not settings.prediction_markets_data_url:
            raise DataAdapterDenied("Prediction Data API base URL is not configured")
        if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
            raise DataAdapterDenied("path must be an absolute URL path on the configured host")
        if ".." in path or "?" in path or "#" in path:
            raise DataAdapterDenied("path must not contain traversal or query fragments")
        return await self._get_json(settings.prediction_markets_data_url, path, params)

    async def sync_markets(self, actor: str = "iam", limit: Optional[int] = None) -> Dict[str, Any]:
        """Register discovered markets. Implied probabilities are not IAM estimates."""
        self._require_enabled()
        markets = await self.fetch_markets(limit)
        service = PredictionMarketService(self.db)
        created = 0
        existing = 0
        skipped = 0
        for market in markets:
            try:
                await service.register_market(
                    platform=market["platform"],
                    market_ref=market["market_ref"],
                    event_name=market["event_name"],
                    outcomes=market["outcomes"],
                    implied_probabilities=market["implied_probabilities"],
                    source_url=market["source_url"],
                    actor=actor,
                )
                created += 1
            except PredictionMarketDenied as exc:
                if "already registered" in str(exc):
                    existing += 1
                else:
                    skipped += 1
        self.db.add(
            AuditEvent(
                event_type="prediction_market_data_synced",
                actor=actor,
                target="polymarket_gamma",
                details={
                    "discovered": len(markets),
                    "created": created,
                    "existing": existing,
                    "skipped": skipped,
                    "market_implied_probabilities_only": True,
                    "read_only": True,
                },
            )
        )
        await self.db.commit()
        return {
            "discovered": len(markets),
            "created": created,
            "existing": existing,
            "skipped": skipped,
            "market_implied_probabilities_only": True,
            "read_only": True,
        }

    def _market_limit(self, limit: Optional[int]) -> int:
        configured = int(settings.prediction_markets_max_markets)
        if limit is None:
            return max(1, configured)
        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:
            raise DataAdapterDenied("limit must be an integer") from exc
        if value < 1:
            raise DataAdapterDenied("limit must be positive")
        return min(value, max(1, configured))

    def _require_enabled(self) -> None:
        if not settings.prediction_markets_data_adapter_enabled:
            raise DataAdapterDenied("prediction market data adapter is disabled")

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (ValueError, TypeError):
                return []
            return parsed if isinstance(parsed, list) else []
        return list(value) if isinstance(value, (list, tuple)) else []

    @staticmethod
    def _configured_base(value: str, name: str) -> str:
        if not value:
            raise DataAdapterDenied(f"{name} base URL is not configured")
        parsed = urlparse(str(value))
        if parsed.scheme != "https" or not parsed.netloc:
            raise DataAdapterDenied(f"{name} base URL must use https")
        return str(value).rstrip("/")

    async def _get_json(
        self, base: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        self._require_enabled()
        url = self._configured_base(base, "Prediction market data") + path
        timeout = float(settings.prediction_markets_request_timeout_seconds)
        try:
            if self._client is not None:
                response = await self._client.get(url, params=params, timeout=timeout)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DataAdapterDenied(f"public market-data request failed: {exc}") from exc
