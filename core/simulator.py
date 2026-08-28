"""
Paper Trading Simulation Engine
Manages $50 virtual capital per bot, realistic fees, slippage, and position execution.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from .database import ArenaDatabase

logger = logging.getLogger("CryptoArena.Simulator")

class PaperWallet:
    def __init__(self, bot_id: str, db: ArenaDatabase, initial_capital: float = 50.0,
                 fee_rate: float = 0.00075, slippage_rate: float = 0.0005,
                 min_order_usd: float = 10.0, max_open_trades: int = 2):
        self.bot_id = bot_id
        self.db = db
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.available_balance = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.min_order_usd = min_order_usd
        self.max_open_trades = max_open_trades

        # Load existing state from db if available
        bot_record = self.db.get_bot(bot_id)
        if bot_record:
            self.initial_capital = bot_record['initial_capital']
            self.current_balance = bot_record['current_balance']
            self.available_balance = bot_record['available_balance']
            self.peak_equity = bot_record['peak_equity']
            self.max_drawdown = bot_record['max_drawdown']
            self.total_pnl = bot_record['total_pnl']
            self.total_trades = bot_record['total_trades']
            self.winning_trades = bot_record['winning_trades']
            self.losing_trades = bot_record['losing_trades']
        else:
            self.peak_equity = initial_capital
            self.max_drawdown = 0.0
            self.total_pnl = 0.0
            self.total_trades = 0
            self.winning_trades = 0
            self.losing_trades = 0
            self.risk_per_trade = 0.02 # 2% risk budget per trade

    def calculate_volatility_adjusted_stake(self, price: float, atr: Optional[float] = None, base_stake: float = 25.0) -> float:
        """Dynamically scales position sizing based on 14-period ATR volatility."""
        if not atr or atr <= 0 or price <= 0:
            return max(self.min_order_usd, min(base_stake, self.available_balance))

        # Normalized volatility: ATR / Price
        volatility_ratio = atr / price
        # Risk budget = 2% of total equity
        total_eq = self.get_total_equity()
        risk_budget = total_eq * getattr(self, 'risk_per_trade', 0.02)
        
        # Volatility sizing: In quiet market bet higher conviction, in wild volatility bet safer
        vol_adjusted_stake = risk_budget / max(0.005, volatility_ratio)
        
        # Cap between min_order_usd ($10) and max stake ($45 or available cash)
        final_stake = max(self.min_order_usd, min(base_stake * 1.5, vol_adjusted_stake, self.available_balance))
        return round(final_stake, 2)

    def get_open_positions(self) -> List[Dict[str, Any]]:
        return self.db.get_open_positions(self.bot_id)

    def can_open_position(self, usd_amount: float) -> (bool, str):
        open_positions = self.get_open_positions()
        if len(open_positions) >= self.max_open_trades:
            return False, f"Max open positions reached ({len(open_positions)}/{self.max_open_trades})"
        if usd_amount < self.min_order_usd:
            return False, f"Order size ${usd_amount:.2f} below min order size ${self.min_order_usd:.2f}"
        if usd_amount > self.available_balance:
            return False, f"Insufficient balance (${self.available_balance:.2f} available, ${usd_amount:.2f} required)"
        return True, "OK"

    def execute_buy(self, symbol: str, price: float, usd_amount: float,
                    stop_loss_pct: Optional[float] = None,
                    take_profit_pct: Optional[float] = None,
                    trailing_stop_pct: Optional[float] = None,
                    atr: Optional[float] = None,
                    reason: str = "SIGNAL") -> Optional[Dict[str, Any]]:
        """Executes a simulated BUY order with optional volatility-adjusted position sizing."""
        # Calculate dynamic volatility sizing if ATR is provided
        if atr and atr > 0:
            usd_amount = self.calculate_volatility_adjusted_stake(price=price, atr=atr, base_stake=usd_amount)

        can_buy, msg = self.can_open_position(usd_amount)
        if not can_buy:
            logger.warning(f"[{self.bot_id}] BUY rejected for {symbol}: {msg}")
            return None

        # Apply slippage on entry (buy slightly higher)
        execution_price = price * (1 + self.slippage_rate)
        fee = usd_amount * self.fee_rate
        net_usd = usd_amount - fee
        quantity = net_usd / execution_price

        self.available_balance -= usd_amount

        position_id = str(uuid.uuid4())[:8]
        now_iso = datetime.now(timezone.utc).isoformat()

        stop_loss_price = execution_price * (1 - stop_loss_pct) if stop_loss_pct else None
        take_profit_price = execution_price * (1 + take_profit_pct) if take_profit_pct else None

        position = {
            'position_id': position_id,
            'bot_id': self.bot_id,
            'symbol': symbol,
            'side': 'LONG',
            'entry_price': execution_price,
            'current_price': execution_price,
            'quantity': quantity,
            'cost_basis': usd_amount,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'trailing_stop_pct': trailing_stop_pct,
            'highest_price': execution_price,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0,
            'status': 'OPEN',
            'opened_at': now_iso,
            'closed_at': None
        }

        self.db.save_position(position)

        # Record Buy Trade
        trade_id = str(uuid.uuid4())[:8]
        trade = {
            'trade_id': trade_id,
            'bot_id': self.bot_id,
            'position_id': position_id,
            'symbol': symbol,
            'side': 'BUY',
            'price': execution_price,
            'quantity': quantity,
            'cost_or_proceeds': usd_amount,
            'fee_paid': fee,
            'realized_pnl': 0.0,
            'realized_pnl_pct': 0.0,
            'reason': reason,
            'timestamp': now_iso
        }
        self.db.record_trade(trade)
        self._update_and_persist_stats()

        logger.info(f"[{self.bot_id}] BUY EXECUTED: {quantity:.4f} {symbol} @ ${execution_price:.2f} (Cost: ${usd_amount:.2f}, Fee: ${fee:.4f})")
        return position

    def execute_sell(self, position_id: str, current_price: float, reason: str = "SIGNAL") -> Optional[Dict[str, Any]]:
        """Closes an open position, realizes PnL, deducts fees, and credits capital."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE position_id = ? AND status = 'OPEN'", (position_id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"[{self.bot_id}] Cannot sell: Position {position_id} not found or already closed.")
                return None
            pos = dict(row)

        # Apply slippage on exit (sell slightly lower)
        execution_price = current_price * (1 - self.slippage_rate)
        gross_proceeds = pos['quantity'] * execution_price
        fee = gross_proceeds * self.fee_rate
        net_proceeds = gross_proceeds - fee

        realized_pnl = net_proceeds - pos['cost_basis']
        realized_pnl_pct = (realized_pnl / pos['cost_basis']) * 100.0

        # Update Balances
        self.available_balance += net_proceeds
        self.current_balance += realized_pnl
        self.total_pnl += realized_pnl
        self.total_trades += 1
        if realized_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        now_iso = datetime.now(timezone.utc).isoformat()

        # Update position record
        pos['current_price'] = execution_price
        pos['unrealized_pnl'] = 0.0
        pos['unrealized_pnl_pct'] = 0.0
        pos['status'] = 'CLOSED'
        pos['closed_at'] = now_iso
        self.db.save_position(pos)

        # Record Sell Trade
        trade_id = str(uuid.uuid4())[:8]
        trade = {
            'trade_id': trade_id,
            'bot_id': self.bot_id,
            'position_id': position_id,
            'symbol': pos['symbol'],
            'side': 'SELL',
            'price': execution_price,
            'quantity': pos['quantity'],
            'cost_or_proceeds': net_proceeds,
            'fee_paid': fee,
            'realized_pnl': realized_pnl,
            'realized_pnl_pct': realized_pnl_pct,
            'reason': reason,
            'timestamp': now_iso
        }
        self.db.record_trade(trade)
        self._update_and_persist_stats()

        logger.info(f"[{self.bot_id}] SELL EXECUTED ({reason}): {pos['quantity']:.4f} {pos['symbol']} @ ${execution_price:.2f} | PnL: ${realized_pnl:+.2f} ({realized_pnl_pct:+.2f}%)")
        return trade

    def update_open_positions_market_price(self, symbol: str, current_price: float):
        """Updates unrealized PnL and triggers automated Stop-Loss / Take-Profit / Trailing-Stop."""
        open_positions = [p for p in self.get_open_positions() if p['symbol'] == symbol]

        for pos in open_positions:
            pos_id = pos['position_id']
            entry_price = pos['entry_price']
            quantity = pos['quantity']
            cost_basis = pos['cost_basis']

            # Update highest price reached for trailing stop
            highest_price = max(pos.get('highest_price') or entry_price, current_price)
            pos['highest_price'] = highest_price

            gross_value = quantity * current_price
            exit_fee_est = gross_value * self.fee_rate
            unrealized_pnl = (gross_value - exit_fee_est) - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100.0

            pos['current_price'] = current_price
            pos['unrealized_pnl'] = unrealized_pnl
            pos['unrealized_pnl_pct'] = unrealized_pnl_pct

            # 1. Check Take Profit Trigger
            if pos.get('take_profit') and current_price >= pos['take_profit']:
                self.execute_sell(pos_id, current_price, reason="TAKE_PROFIT")
                continue

            # 2. Check Stop Loss Trigger
            if pos.get('stop_loss') and current_price <= pos['stop_loss']:
                self.execute_sell(pos_id, current_price, reason="STOP_LOSS")
                continue

            # 3. Check Trailing Stop Trigger
            if pos.get('trailing_stop_pct'):
                trailing_stop_price = highest_price * (1 - pos['trailing_stop_pct'])
                if current_price <= trailing_stop_price and current_price > entry_price:
                    self.execute_sell(pos_id, current_price, reason="TRAILING_STOP")
                    continue

            # Save updated position state
            self.db.save_position(pos)

        self._update_and_persist_stats()

    def get_total_equity(self) -> float:
        """Returns liquid balance + unrealized PnL of all open positions."""
        open_positions = self.get_open_positions()
        unrealized = sum(p.get('unrealized_pnl', 0.0) for p in open_positions)
        return self.available_balance + sum(p.get('cost_basis', 0.0) for p in open_positions) + unrealized

    def _update_and_persist_stats(self):
        total_equity = self.get_total_equity()
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity

        dd = 0.0
        if self.peak_equity > 0:
            dd = ((self.peak_equity - total_equity) / self.peak_equity) * 100.0
        if dd > self.max_drawdown:
            self.max_drawdown = dd

        roi_pct = ((total_equity - self.initial_capital) / self.initial_capital) * 100.0
        win_rate = (self.winning_trades / self.total_trades * 100.0) if self.total_trades > 0 else 0.0
        total_pnl = total_equity - self.initial_capital

        self.db.update_bot_stats(
            bot_id=self.bot_id,
            current_balance=total_equity,
            available_balance=self.available_balance,
            total_pnl=total_pnl,
            roi_pct=roi_pct,
            win_rate=win_rate,
            total_trades=self.total_trades,
            winning_trades=self.winning_trades,
            losing_trades=self.losing_trades,
            max_drawdown=self.max_drawdown,
            peak_equity=self.peak_equity
        )
