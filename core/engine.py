"""
Tournament Master Engine
Orchestrates the 5 competing bots, market data ingestion, paper wallets,
autonomous research, and self-improvement loops.
"""
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    from core.database import ArenaDatabase
    from core.simulator import PaperWallet
    from core.market_feed import MarketFeed
    from strategies.base_strategy import BaseStrategy, Signal
    from strategies.alpha_trend import AlphaTrendStrategy
    from strategies.mean_revert import MeanRevertStrategy
    from strategies.breakout_hunter import BreakoutHunterStrategy
    from strategies.adaptive_grid import AdaptiveGridStrategy
    from strategies.smart_money import SmartMoneyTrackerStrategy
    from strategies.polymarket_predictor import PolymarketPredictorStrategy
    from strategies.indian_stock_breakout import BharatBreakoutStrategy
    from strategies.indian_stock_meanrevert import DesiMeanRevertStrategy
    from strategies.hyperliquid_gold_silver import HyperliquidGoldSilverStrategy
    from research.regime_analyzer import MarketRegimeAnalyzer
    from research.smart_wallet_tracker import SmartWalletTracker
    from research.sentiment_analyzer import SentimentAnalyzer
    from research.polymarket_feed import PolymarketFeed
    from research.indian_market_feed import IndianAndCommodityFeed
    from core.backtester import StrategyBacktester
    from learning.self_improver import SelfImprovementEngine
    from notifications.notifier import ArenaNotifier
    from config import config
except (ImportError, ValueError):
    from .database import ArenaDatabase
    from .simulator import PaperWallet
    from .market_feed import MarketFeed
    from .backtester import StrategyBacktester
    from ..strategies.base_strategy import BaseStrategy, Signal
    from ..strategies.alpha_trend import AlphaTrendStrategy
    from ..strategies.mean_revert import MeanRevertStrategy
    from ..strategies.breakout_hunter import BreakoutHunterStrategy
    from ..strategies.adaptive_grid import AdaptiveGridStrategy
    from ..strategies.smart_money import SmartMoneyTrackerStrategy
    from ..strategies.polymarket_predictor import PolymarketPredictorStrategy
    from ..strategies.indian_stock_breakout import BharatBreakoutStrategy
    from ..strategies.indian_stock_meanrevert import DesiMeanRevertStrategy
    from ..strategies.hyperliquid_gold_silver import HyperliquidGoldSilverStrategy
    from ..research.regime_analyzer import MarketRegimeAnalyzer
    from ..research.smart_wallet_tracker import SmartWalletTracker
    from ..research.sentiment_analyzer import SentimentAnalyzer
    from ..research.polymarket_feed import PolymarketFeed
    from ..research.indian_market_feed import IndianAndCommodityFeed
    from ..learning.self_improver import SelfImprovementEngine
    from ..notifications.notifier import ArenaNotifier
    from ..config import config

logger = logging.getLogger("CryptoArena.Engine")

class TournamentEngine:
    def __init__(self, db: Optional[ArenaDatabase] = None):
        self.db = db or ArenaDatabase(config.DB_PATH)
        self.db.init_tournament(config.TOURNAMENT_NAME, config.INITIAL_CAPITAL_USD)

        self.market_feed = MarketFeed(
            exchange_id=config.DATA_EXCHANGE,
            timeframe=config.TIMEFRAME,
            limit=config.CANDLE_LIMIT
        )
        self.indian_feed = IndianAndCommodityFeed()
        self.regime_analyzer = MarketRegimeAnalyzer(self.db)
        self.smart_wallet_tracker = SmartWalletTracker(self.db)
        self.sentiment_analyzer = SentimentAnalyzer(self.db)
        self.polymarket_feed = PolymarketFeed()
        self.backtester = StrategyBacktester(self.market_feed)
        self.notifier = ArenaNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)

        # Dynamic trading pairs
        self.active_trading_pairs = list(config.TRADING_PAIRS)

        # Initialize all 9 Bots, Wallets & Strategies
        self.bots: Dict[str, Dict[str, Any]] = {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self.wallets: Dict[str, PaperWallet] = {}

        self._setup_bots()

        # Self-Improvement Engine
        self.self_improver = SelfImprovementEngine(self.db, self.strategies)

        self.is_running = False
        self.last_research_time = 0
        self.last_self_improve_time = 0
        self.last_snapshot_time = 0
        self.latest_market_overview = {}

    def _setup_bots(self):
        bot_configs = [
            {
                'id': 'bot_1_alphatrend',
                'name': 'AlphaTrend',
                'strategy_name': 'EMA Ribbon + SuperTrend + ADX Momentum',
                'description': 'Captures sustained high-momentum bull/bear trends on major crypto pairs with ATR trailing stops.',
                'strategy_class': AlphaTrendStrategy
            },
            {
                'id': 'bot_2_meanrevert',
                'name': 'MeanRevert',
                'strategy_name': 'Bollinger Bands + RSI Oversold Scalper',
                'description': 'Scalps ranging and sideways markets by buying extreme oversold bounces with tight risk parameters.',
                'strategy_class': MeanRevertStrategy
            },
            {
                'id': 'bot_3_breakouthunter',
                'name': 'BreakoutHunter',
                'strategy_name': 'Donchian 20-High + Volume Surge Expansion',
                'description': 'Detects volume explosion surges and rides fast momentum breakouts with volatility expansion filters.',
                'strategy_class': BreakoutHunterStrategy
            },
            {
                'id': 'bot_4_adaptivegrid',
                'name': 'AdaptiveGrid',
                'strategy_name': 'Dynamic ATR Micro-Grid Market Maker',
                'description': 'Dynamic 2-4 tier geometric grid centered around dynamic VWAP/EMA for steady passive accumulation.',
                'strategy_class': AdaptiveGridStrategy
            },
            {
                'id': 'bot_5_smartmoney',
                'name': 'SmartMoneyTracker',
                'strategy_name': 'On-Chain Whale Flow & Smart Wallet Follower',
                'description': 'Monitors top profitable DEX smart wallets and CEX whale inflows to mirror smart money accumulation.',
                'strategy_class': SmartMoneyTrackerStrategy
            },
            {
                'id': 'bot_6_polypredictor',
                'name': 'PolyPredictor',
                'strategy_name': 'Polymarket Event Probability & Statistical Arbitrage',
                'description': 'Trades real Polymarket prediction markets by exploiting pricing misalignments between implied odds and spot momentum.',
                'strategy_class': PolymarketPredictorStrategy
            },
            {
                'id': 'bot_7_bharatbreakout',
                'name': 'BharatBreakout (NSE/NIFTY)',
                'strategy_name': 'Indian Stock Market 15m Open-Range Breakout',
                'description': 'Trades high-liquidity Indian equities (NIFTY50, RELIANCE, TATAMOTORS) using 15m ORB + Supertrend.',
                'strategy_class': BharatBreakoutStrategy
            },
            {
                'id': 'bot_8_desimeanrevert',
                'name': 'DesiMeanRevert (NSE Scalper)',
                'strategy_name': 'Indian Stock Market Bollinger Band Dip Scalper',
                'description': 'Scalps oversold dips on Indian stocks (TATAMOTORS, INFY, ICICIBANK) with 2-sigma mean reversion.',
                'strategy_class': DesiMeanRevertStrategy
            },
            {
                'id': 'bot_9_hypergoldsilver',
                'name': 'HyperGoldSilver (Hyperliquid Commodities)',
                'strategy_name': 'Hyperliquid Gold (XAU) & Silver (XAG) Macro Perp Bot',
                'description': 'Trades Gold & Silver perps on Hyperliquid L1 DEX with macro trend-following & volatility breakouts.',
                'strategy_class': HyperliquidGoldSilverStrategy
            }
        ]

        for b in bot_configs:
            bot_id = b['id']
            self.db.register_bot(
                bot_id=bot_id,
                name=b['name'],
                strategy_name=b['strategy_name'],
                description=b['description'],
                initial_capital=config.INITIAL_CAPITAL_USD
            )

            wallet = PaperWallet(
                bot_id=bot_id,
                db=self.db,
                initial_capital=config.INITIAL_CAPITAL_USD,
                fee_rate=config.FEE_RATE,
                slippage_rate=config.SLIPPAGE_RATE,
                min_order_usd=config.MIN_ORDER_USD,
                max_open_trades=config.MAX_OPEN_TRADES_PER_BOT
            )
            strategy = b['strategy_class'](bot_id=bot_id)

            self.bots[bot_id] = b
            self.wallets[bot_id] = wallet
            self.strategies[bot_id] = strategy

    def add_trading_pair(self, symbol: str) -> bool:
        symbol = symbol.upper()
        if symbol not in self.active_trading_pairs:
            self.active_trading_pairs.append(symbol)
            return True
        return False

    def remove_trading_pair(self, symbol: str) -> bool:
        symbol = symbol.upper()
        if symbol in self.active_trading_pairs and len(self.active_trading_pairs) > 1:
            self.active_trading_pairs.remove(symbol)
            return True
        return False

    def get_sentiment_data(self) -> Dict[str, Any]:
        return self.sentiment_analyzer.get_latest_sentiment()

    def get_polymarket_events(self) -> List[Dict[str, Any]]:
        return self.polymarket_feed.fetch_crypto_prediction_markets()

    def run_backtest(self, strategy_type: str, symbol: str, tp: float, sl: float, stake: float) -> Dict[str, Any]:
        return self.backtester.run_backtest(
            strategy_type=strategy_type,
            symbol=symbol,
            stake_usd=stake,
            take_profit_pct=tp,
            stop_loss_pct=sl
        )

    def get_ohlcv_chart(self, symbol: str) -> List[Dict[str, Any]]:
        df = self.market_feed.fetch_ohlcv_dataframe(symbol)
        if df is None or len(df) == 0:
            return []
        candles = []
        for _, row in df.iterrows():
            candles.append({
                "time": str(row['timestamp']),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume'])
            })
        return candles[-60:] # Last 60 candles for chart

    async def run_tick(self):
        """Executes one evaluation cycle across all symbols and all 9 bots."""
        symbol_dfs = {}
        tickers = {}
        poly_events = self.get_polymarket_events()

        # 1. Ingest Market Data for all Active Crypto Pairs
        for symbol in self.active_trading_pairs:
            ticker = self.market_feed.fetch_ticker(symbol)
            df = self.market_feed.fetch_ohlcv_dataframe(symbol)
            tickers[symbol] = ticker
            symbol_dfs[symbol] = df

            for bot_id, wallet in self.wallets.items():
                wallet.update_open_positions_market_price(symbol, ticker['price'])

        # Ingest Indian Stock Market & Commodity Feeds
        indian_symbols = ["RELIANCE", "TATAMOTORS", "NIFTY50", "HDFCBANK"]
        commodity_symbols = ["GOLD/USD", "SILVER/USD"]
        for sym in indian_symbols + commodity_symbols:
            t = self.indian_feed.fetch_ticker(sym)
            d = self.indian_feed.fetch_ohlcv_dataframe(sym)
            tickers[sym] = t
            symbol_dfs[sym] = d

            for bot_id, wallet in self.wallets.items():
                wallet.update_open_positions_market_price(sym, t['price'])

        # 2. Run Strategy Decisions for each Bot
        for bot_id, strategy in self.strategies.items():
            bot_record = self.db.get_bot(bot_id)
            if bot_record and not bot_record.get('is_active', 1):
                continue

            wallet = self.wallets[bot_id]
            open_positions = wallet.get_open_positions()
            avail_balance = wallet.available_balance

            # Target relevant asset classes per bot
            if bot_id in ['bot_7_bharatbreakout', 'bot_8_desimeanrevert']:
                target_symbols = indian_symbols
            elif bot_id == 'bot_9_hypergoldsilver':
                target_symbols = commodity_symbols
            else:
                target_symbols = self.active_trading_pairs

            for symbol in target_symbols:
                df = symbol_dfs.get(symbol)
                ticker = tickers.get(symbol)
                if df is None or ticker is None:
                    continue

                if bot_id == 'bot_6_polypredictor':
                    decision = strategy.evaluate(
                        symbol=symbol,
                        df=df,
                        ticker=ticker,
                        open_positions=open_positions,
                        available_balance=avail_balance,
                        polymarket_events=poly_events
                    )
                else:
                    decision = strategy.evaluate(
                        symbol=symbol,
                        df=df,
                        ticker=ticker,
                        open_positions=open_positions,
                        available_balance=avail_balance
                    )

                if decision.action == Signal.BUY:
                    pos = wallet.execute_buy(
                        symbol=symbol,
                        price=ticker['price'],
                        usd_amount=decision.stake_usd,
                        stop_loss_pct=decision.stop_loss_pct,
                        take_profit_pct=decision.take_profit_pct,
                        trailing_stop_pct=decision.trailing_stop_pct,
                        reason=decision.reason
                    )
                    if pos:
                        await self.notifier.notify_trade(
                            bot_name=strategy.name,
                            symbol=symbol,
                            side="BUY",
                            price=pos['entry_price'],
                            quantity=pos['quantity'],
                            reason=decision.reason
                        )
                        avail_balance = wallet.available_balance

                elif decision.action == Signal.SELL:
                    matching = [p for p in open_positions if p['symbol'] == symbol]
                    for p in matching:
                        trade = wallet.execute_sell(
                            position_id=p['position_id'],
                            current_price=ticker['price'],
                            reason=decision.reason
                        )
                        if trade:
                            await self.notifier.notify_trade(
                                bot_name=strategy.name,
                                symbol=symbol,
                                side="SELL",
                                price=trade['price'],
                                quantity=trade['quantity'],
                                pnl=trade['realized_pnl'],
                                pnl_pct=trade['realized_pnl_pct'],
                                reason=decision.reason
                            )
                            avail_balance = wallet.available_balance

        # 3. Take Periodic Equity Snapshot (every 60 seconds)
        now = time.time()
        if now - self.last_snapshot_time > 60:
            self.last_snapshot_time = now
            for bot_id, wallet in self.wallets.items():
                total_equity = wallet.get_total_equity()
                open_pos = wallet.get_open_positions()
                unrealized = sum(p.get('unrealized_pnl', 0.0) for p in open_pos)
                roi_pct = ((total_equity - wallet.initial_capital) / wallet.initial_capital) * 100.0
                self.db.record_equity_snapshot(bot_id, wallet.available_balance, unrealized, total_equity, roi_pct)

        # 4. Periodic Deep Research Cycle (every 30m or initial)
        if now - self.last_research_time > config.RESEARCH_CYCLE_SECONDS:
            self.last_research_time = now
            await self.run_research_cycle(symbol_dfs)

        # 5. Periodic Self-Improvement Cycle (every 2 hours)
        if now - self.last_self_improve_time > config.SELF_IMPROVE_CYCLE_SECONDS:
            self.last_self_improve_time = now
            self.run_self_improvement_cycle()

    async def run_research_cycle(self, symbol_dfs: Optional[Dict[str, pd.DataFrame]] = None):
        """Runs autonomous market regime scan & on-chain smart wallet intelligence."""
        if not symbol_dfs:
            symbol_dfs = {sym: self.market_feed.fetch_ohlcv_dataframe(sym) for sym in config.TRADING_PAIRS}

        # Market Regime Analyzer
        self.latest_market_overview = self.regime_analyzer.generate_market_overview(symbol_dfs)

        # Smart Wallet Tracker
        smart_signals = await self.smart_wallet_tracker.scan_smart_money(config.TRADING_PAIRS)

        # Update Bot 5 (SmartMoneyTracker)
        smart_bot_strat = self.strategies.get("bot_5_smartmoney")
        if isinstance(smart_bot_strat, SmartMoneyTrackerStrategy):
            smart_bot_strat.update_smart_signals(smart_signals)

        logger.info("Autonomous research cycle completed successfully.")

    def run_self_improvement_cycle(self):
        """Runs performance audit and dynamically tunes bot parameters."""
        adjustments = self.self_improver.evaluate_and_optimize(self.latest_market_overview)
        for adj in adjustments:
            asyncio.create_task(self.notifier.notify_parameter_tuning(
                bot_name=adj['bot_id'],
                param=adj['param'],
                old_val=adj['old_value'],
                new_val=adj['new_value'],
                reason=adj['reason']
            ))

    async def start(self):
        """Starts 24/7 autonomous trading loop."""
        self.is_running = True
        logger.info("Starting CryptoArena 50X Tournament Engine...")
        # Initial research scan
        await self.run_research_cycle()

        while self.is_running:
            try:
                await self.run_tick()
            except Exception as e:
                logger.error(f"Error during tournament tick: {e}", exc_info=True)
            await asyncio.sleep(config.UPDATE_INTERVAL_SECONDS)

    def stop(self):
        self.is_running = False
        logger.info("Stopped CryptoArena 50X Tournament Engine.")

    def get_leaderboard_data(self) -> List[Dict[str, Any]]:
        """Returns live leaderboard sorted by PnL and ROI."""
        bots = self.db.get_all_bots()
        leaderboard = []
        for b in bots:
            bot_id = b['bot_id']
            wallet = self.wallets.get(bot_id)
            total_equity = wallet.get_total_equity() if wallet else b['current_balance']
            open_pos = wallet.get_open_positions() if wallet else []
            unrealized = sum(p.get('unrealized_pnl', 0.0) for p in open_pos)

            roi = ((total_equity - b['initial_capital']) / b['initial_capital']) * 100.0
            pnl = total_equity - b['initial_capital']

            leaderboard.append({
                'bot_id': bot_id,
                'name': b['name'],
                'strategy_name': b['strategy_name'],
                'description': b['description'],
                'initial_capital': b['initial_capital'],
                'current_equity': round(total_equity, 2),
                'available_balance': round(wallet.available_balance if wallet else b['available_balance'], 2),
                'total_pnl': round(pnl, 2),
                'roi_pct': round(roi, 2),
                'win_rate': round(b['win_rate'], 1),
                'total_trades': b['total_trades'],
                'winning_trades': b['winning_trades'],
                'losing_trades': b['losing_trades'],
                'max_drawdown': round(b['max_drawdown'], 2),
                'open_positions_count': len(open_pos),
                'is_active': bool(b.get('is_active', 1)),
                'active_strategy_params': self.strategies[bot_id].params if bot_id in self.strategies else {}
            })

        leaderboard.sort(key=lambda x: x['total_pnl'], reverse=True)
        return leaderboard

    def toggle_bot(self, bot_id: str, is_active: bool) -> bool:
        """Pauses or resumes an individual bot."""
        if bot_id not in self.wallets:
            return False
        self.db.set_bot_active_status(bot_id, is_active)
        logger.info(f"Bot '{bot_id}' active status set to {is_active}")
        return True

    def liquidate_bot(self, bot_id: str) -> List[Dict[str, Any]]:
        """Force closes all open positions for a bot at current market prices."""
        wallet = self.wallets.get(bot_id)
        if not wallet:
            return []
        open_pos = wallet.get_open_positions()
        closed = []
        for pos in open_pos:
            ticker = self.market_feed.fetch_ticker(pos['symbol'])
            trade = wallet.execute_sell(pos['position_id'], ticker['price'], reason="MANUAL_LIQUIDATE")
            if trade:
                closed.append(trade)
        return closed

    def update_bot_params(self, bot_id: str, new_params: Dict[str, Any]) -> bool:
        """Dynamically updates hyperparameters for an active strategy."""
        strat = self.strategies.get(bot_id)
        if not strat:
            return False
        old_params = dict(strat.params)
        strat.update_parameters(new_params)
        for k, v in new_params.items():
            self.db.log_parameter_adjustment(bot_id, k, old_params.get(k), v, "Manual User Dashboard Control")
        return True

    def create_custom_bot(self, name: str, strategy_type: str, description: str = "",
                          initial_capital: float = 50.0, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dynamically adds a new trading bot into the active tournament."""
        bot_id = f"bot_{len(self.wallets) + 1}_{name.lower().replace(' ', '_')}"
        
        # Strategy mapper
        strategy_classes = {
            'trend': AlphaTrendStrategy,
            'mean_revert': MeanRevertStrategy,
            'breakout': BreakoutHunterStrategy,
            'grid': AdaptiveGridStrategy,
            'smart_money': SmartMoneyTrackerStrategy
        }
        strat_cls = strategy_classes.get(strategy_type, AlphaTrendStrategy)

        self.db.register_bot(
            bot_id=bot_id,
            name=name,
            strategy_name=f"{strategy_type.capitalize()} Custom AI",
            description=description or f"Custom {strategy_type} automated bot",
            initial_capital=initial_capital
        )

        wallet = PaperWallet(
            bot_id=bot_id,
            db=self.db,
            initial_capital=initial_capital,
            fee_rate=config.FEE_RATE,
            slippage_rate=config.SLIPPAGE_RATE,
            min_order_usd=config.MIN_ORDER_USD,
            max_open_trades=config.MAX_OPEN_TRADES_PER_BOT
        )
        strategy = strat_cls(bot_id=bot_id, params=params)

        self.bots[bot_id] = {
            'id': bot_id,
            'name': name,
            'strategy_name': f"{strategy_type.capitalize()} Custom AI",
            'description': description
        }
        self.wallets[bot_id] = wallet
        self.strategies[bot_id] = strategy

        logger.info(f"Custom bot '{name}' ({bot_id}) dynamically registered with ${initial_capital} capital.")
        return {'bot_id': bot_id, 'name': name, 'strategy_type': strategy_type}

    def execute_manual_trade(self, bot_id: str, symbol: str, side: str, usd_amount: float = 25.0) -> Optional[Dict[str, Any]]:
        """Allows manual execution override for testing or emergency entry/exit."""
        wallet = self.wallets.get(bot_id)
        if not wallet:
            return None
        ticker = self.market_feed.fetch_ticker(symbol)
        if side.upper() == "BUY":
            return wallet.execute_buy(symbol, ticker['price'], usd_amount, stop_loss_pct=0.025, take_profit_pct=0.045, reason="MANUAL_OVERRIDE")
        else:
            open_pos = [p for p in wallet.get_open_positions() if p['symbol'] == symbol]
            if open_pos:
                return wallet.execute_sell(open_pos[0]['position_id'], ticker['price'], reason="MANUAL_OVERRIDE")
        return None

    def reset_tournament(self, capital: float = 50.0):
        """Resets all bots and trades to initial state."""
        self.db.reset_tournament(capital)
        for bot_id in self.wallets:
            self.wallets[bot_id] = PaperWallet(
                bot_id=bot_id,
                db=self.db,
                initial_capital=capital
            )
        logger.info(f"Tournament reset successfully with ${capital:.2f} per bot.")
