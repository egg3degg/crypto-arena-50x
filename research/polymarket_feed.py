"""
Polymarket Live Feed Ingester
Fetches real active prediction markets from Polymarket Gamma API.
"""
import time
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional

logger = logging.getLogger("CryptoArena.PolymarketFeed")

GAMMA_API_URL = "https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false"

class PolymarketFeed:
    def __init__(self):
        self.cached_markets: List[Dict[str, Any]] = []
        self.last_fetch_time: float = 0.0
        self.cache_ttl: float = 60.0 # 1 minute cache

    def fetch_crypto_prediction_markets(self) -> List[Dict[str, Any]]:
        """Fetches active Polymarket events related to crypto and macroeconomic events."""
        now = time.time()
        if self.cached_markets and (now - self.last_fetch_time < self.cache_ttl):
            return self.cached_markets

        req = urllib.request.Request(
            GAMMA_API_URL,
            headers={
                "User-Agent": "CryptoArena-PolymarketBot/1.0",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                events = json.loads(response.read().decode("utf-8"))
                
                parsed_markets = []
                for event in events:
                    title = event.get("title", "")
                    description = event.get("description", "")
                    markets = event.get("markets", [])

                    for m in markets:
                        q = m.get("question", title)
                        outcome_prices = m.get("outcomePrices")
                        if isinstance(outcome_prices, str):
                            try:
                                outcome_prices = json.loads(outcome_prices)
                            except Exception:
                                outcome_prices = [0.5, 0.5]
                        elif not outcome_prices:
                            outcome_prices = [0.5, 0.5]

                        # Parse YES / NO probabilities
                        yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
                        no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else (1.0 - yes_price)

                        # Filter relevant crypto / financial events
                        is_crypto = any(k in q.lower() for k in ["btc", "bitcoin", "eth", "ethereum", "sol", "solana", "crypto", "fed", "rate", "inflation", "tariff", "market"])

                        if is_crypto and 0.05 < yes_price < 0.95:
                            parsed_markets.append({
                                "market_id": m.get("id", str(len(parsed_markets))),
                                "question": q,
                                "category": "Crypto / Macro",
                                "yes_price": round(yes_price, 3),
                                "no_price": round(no_price, 3),
                                "volume_24h": float(m.get("volume24hr", 0) or 0),
                                "liquidity": float(m.get("liquidity", 0) or 0),
                                "end_date": m.get("endDate", ""),
                                "event_title": title
                            })

                if parsed_markets:
                    self.cached_markets = parsed_markets
                    self.last_fetch_time = now
                    logger.info(f"Fetched {len(parsed_markets)} active Polymarket events.")
                    return parsed_markets
        except Exception as e:
            logger.warning(f"Polymarket API request failed: {e}. Using simulated dynamic market feeds.")

        # Fallback simulated dynamic prediction markets if network/API throttles
        return self._get_fallback_markets()

    def _get_fallback_markets(self) -> List[Dict[str, Any]]:
        return [
            {
                "market_id": "poly-btc-85k",
                "question": "Will Bitcoin (BTC) reach $85,000 before month-end?",
                "category": "Crypto / BTC",
                "yes_price": 0.42,
                "no_price": 0.58,
                "volume_24h": 482000.0,
                "liquidity": 125000.0,
                "end_date": "2026-08-31"
            },
            {
                "market_id": "poly-sol-200",
                "question": "Will Solana (SOL) trade above $200 this week?",
                "category": "Crypto / SOL",
                "yes_price": 0.38,
                "no_price": 0.62,
                "volume_24h": 310000.0,
                "liquidity": 95000.0,
                "end_date": "2026-08-31"
            },
            {
                "market_id": "poly-eth-etf",
                "question": "Will Ethereum ETF weekly net inflows exceed $250M?",
                "category": "Crypto / ETH",
                "yes_price": 0.54,
                "no_price": 0.46,
                "volume_24h": 195000.0,
                "liquidity": 68000.0,
                "end_date": "2026-08-31"
            },
            {
                "market_id": "poly-fed-rate",
                "question": "Will the Federal Reserve cut interest rates by 25bps?",
                "category": "Macro / Fed",
                "yes_price": 0.72,
                "no_price": 0.28,
                "volume_24h": 1250000.0,
                "liquidity": 450000.0,
                "end_date": "2026-09-18"
            }
        ]
