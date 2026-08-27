"""
Base Strategy Interface for all CryptoArena bots.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class Signal:
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class StrategyDecision:
    def __init__(self, action: str, symbol: str = "",
                 stake_usd: float = 25.0,
                 stop_loss_pct: Optional[float] = None,
                 take_profit_pct: Optional[float] = None,
                 trailing_stop_pct: Optional[float] = None,
                 reason: str = "",
                 confidence: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        self.action = action  # "BUY", "SELL", "HOLD"
        self.symbol = symbol
        self.stake_usd = stake_usd
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.reason = reason
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'symbol': self.symbol,
            'stake_usd': self.stake_usd,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'reason': self.reason,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

class BaseStrategy(ABC):
    def __init__(self, bot_id: str, name: str, description: str, params: Optional[Dict[str, Any]] = None):
        self.bot_id = bot_id
        self.name = name
        self.description = description
        self.params = params or {}

    @abstractmethod
    def evaluate(self, symbol: str, df: pd.DataFrame, ticker: Dict[str, Any],
                 open_positions: list, available_balance: float) -> StrategyDecision:
        """Evaluates candle data and returns a StrategyDecision (BUY, SELL, or HOLD)."""
        pass

    def update_parameters(self, new_params: Dict[str, Any]):
        """Dynamically update hyper-parameters via self-improvement engine."""
        self.params.update(new_params)
