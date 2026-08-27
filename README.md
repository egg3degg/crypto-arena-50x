# ⚡ CryptoArena 50X - 5-Bot Trading Championship & AI Engine

An autonomous, 24/7 multi-bot crypto trading arena where **5 distinct AI trading bots** compete side-by-side with **$50.00 simulated paper capital each** ($250 total testbed).

The system features live exchange market data feeds, autonomous market regime and on-chain smart wallet research, automated self-improvement parameter adaptation every 2 hours, and a real-time web control center.

---

## 🏆 The 5 Competing Bots & Strategies

| Bot | Name | Strategy Type | Target Condition | Key Indicators |
| :--- | :--- | :--- | :--- | :--- |
| **Bot 1** | **AlphaTrend** | Multi-Timeframe Trend Following | Strong Bull/Bear Trends | EMA Ribbon (20/50/200), SuperTrend, ADX > 22 filter, ATR Trailing Stop |
| **Bot 2** | **MeanRevert** | Bollinger Mean Reversion Scalper | Sideways / Ranging Markets | Bollinger Bands (20, 2), RSI < 36 Oversold, Stochastic %K Bounce |
| **Bot 3** | **BreakoutHunter** | Donchian Volatility Expansion | Explosive Breakouts | 20-period Donchian High, 1.8x Volume Surge, ATR expansion |
| **Bot 4** | **AdaptiveGrid** | Dynamic Micro-Grid Market Maker | Chop & Micro-Oscillations | Dynamic 2-tier geometric grid centered on dynamic VWAP/EMA |
| **Bot 5** | **SmartMoneyTracker** | Whale Flow & Top Wallet Tracker | Whale Inflows & Accumulation | On-Chain DexScreener/Etherscan/Solscan flow, orderbook imbalance |

---

## 🚀 Quickstart: Launching the 24/7 Tournament

### 1. Run the Tournament
From the workspace root directory:
```bash
python crypto_arena/run_tournament.py
```
This starts:
- The **FastAPI + WebSockets Web Dashboard** on `http://127.0.0.1:8088`
- The **5 Bot Trading Engines** in paper trading mode with live market feeds (Binance/Bybit via CCXT)
- The **Autonomous Deep Research Engine** (Market Regimes & Smart Wallets)
- The **Self-Improvement & Parameter Tuning Engine**
- A **Real-Time Terminal Leaderboard**

### 2. Access the Web Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:8088
```
- **🏆 Bot Leaderboard:** Real-time ranks, PnL, ROI %, Win Rates, Drawdowns, and open positions.
- **📈 Performance Curves:** Live multi-bot equity curves (Chart.js).
- **🧠 Deep Research:** Live market regime classification and on-chain whale accumulation scores.
- **⚙️ Self-Improvement AI:** Audit log of automated parameter adaptations.
- **⚡ Live Trades:** Live open positions and closed trades feed with realized PnL.

---

## 🧠 Autonomous Research & Self-Improvement

### 1. Market Regime & Smart Wallet Intelligence
- Every 30 minutes, the engine classifies the market state across all trading pairs (`SOL/USDT`, `ETH/USDT`, `BTC/USDT`, `AVAX/USDT`, `NEAR/USDT`).
- Scans on-chain liquidity pools and smart wallets to compute composite Smart Money Accumulation scores for Bot 5.

### 2. Self-Improvement Loop
- Every 2 hours, the learning engine evaluates each bot's win rate, profit factor, and max drawdown:
  - **In Bullish Trends:** Expands Take-Profit targets and widens trailing stops for Trend & Breakout bots.
  - **In Choppy Markets:** Tightens profit targets and narrows grid step sizes for Mean-Revert & Grid bots.
  - **Drawdown Defense:** If a bot experiences consecutive losses, its Stop Loss is automatically tightened to protect capital.

---

## 🚀 Transition to Live Trading with Real $50

After 7 days of paper money evaluation (or anytime):
```bash
python crypto_arena/live_switch.py
```
This audits all 5 bots, declares the #1 winning strategy, exports its optimized parameters to `crypto_arena/data/champion_strategy_config.json`, and prepares the live execution configuration.
