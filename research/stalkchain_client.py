"""
Thin async client for the StalkChain Data REST API.
Docs: https://data.stalkchain.com/llms.txt
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import aiohttp

try:
    from config import config
except ImportError:
    from ..config import config

logger = logging.getLogger("CryptoArena.StalkChain")

DEFAULT_BASE = "https://data.stalkchain.com/api/v1"


class StalkChainError(RuntimeError):
    pass


class StalkChainClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.api_key = (api_key or config.STALKCHAIN_API_KEY or "").strip()
        self.base_url = (base_url or config.STALKCHAIN_API_BASE or DEFAULT_BASE).rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def call_tool(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.enabled:
            raise StalkChainError(
                "STALKCHAIN_API_KEY is not set. Create a key at https://data.stalkchain.com/dashboard"
            )
        url = f"{self.base_url}/tools/{name}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        query = {k: v for k, v in (params or {}).items() if v is not None}
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=headers, params=query) as resp:
                body = await resp.json(content_type=None)
                if resp.status >= 400:
                    err = body.get("error") if isinstance(body, dict) else body
                    message = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                    raise StalkChainError(f"StalkChain {name} failed ({resp.status}): {message}")
                if not isinstance(body, dict):
                    return {"data": body}
                return body

    async def health(self) -> Dict[str, Any]:
        return await self.call_tool("stalkchain_health")

    async def account(self) -> Dict[str, Any]:
        return await self.call_tool("stalkchain_account")

    async def coordinated_buys(
        self, min_traders: int = 3, window_minutes: int = 60
    ) -> Dict[str, Any]:
        return await self.call_tool(
            "stalkchain_fomo_coordinated_activity",
            {"side": "buy", "minTraders": min_traders, "windowMinutes": window_minutes},
        )

    async def trending_token_board(self, limit: int = 25) -> Dict[str, Any]:
        return await self.call_tool(
            "stalkchain_fomo_token_board", {"board": "trending", "limit": limit}
        )


def coordinated_buy_symbols(payload: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract base ticker symbols from coordinated-activity style payloads.
    Values are trader counts (higher = stronger smart-money convergence).
    """
    symbols: Dict[str, float] = {}
    candidates = payload.get("data") or payload.get("tokens") or payload.get("items") or payload
    if isinstance(candidates, dict):
        candidates = candidates.get("tokens") or candidates.get("items") or list(candidates.values())
    if not isinstance(candidates, list):
        return symbols

    for row in candidates:
        if not isinstance(row, dict):
            continue
        sym = (
            row.get("symbol")
            or row.get("ticker")
            or row.get("tokenSymbol")
            or row.get("name")
        )
        if not sym or not isinstance(sym, str):
            continue
        sym = sym.upper().replace("$", "").strip()
        if "/" in sym:
            sym = sym.split("/")[0]
        traders = float(
            row.get("traderCount")
            or row.get("traders")
            or row.get("count")
            or row.get("minTraders")
            or 1
        )
        symbols[sym] = max(symbols.get(sym, 0.0), traders)
    return symbols
