"""
CryptoArena 100X - 100-Wallet Multichain Darwinian Tournament & Strategy Laboratory
=====================================================================================
100 Independent Paper Wallets ($100.00 each = $10,000 Total Simulated Capital)
competing side-by-side across different chains, strategies, risk models, and
experimental archetypes (including a simulated Meme Coin Deployer on a Bonding Curve).
"""

import os
import sys
import json
import time
import math
import random
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import requests
import pandas as pd

# Force UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
TOURNAMENT_FILE = os.path.join(DATA_DIR, "wallets_100_state.json")
DASHBOARD_FILE = os.path.join(DATA_DIR, "wallets_100_dashboard.html")

INITIAL_CAPITAL_PER_WALLET = 100.00
TOTAL_WALLETS = 100

# High-liquidity universe across multiple chains
MARKET_SYMBOLS = [
    "SOLUSDT", "BTCUSDT", "ETHUSDT", "SUIUSDT", "AVAXUSDT",
    "NEARUSDT", "JUPUSDT", "RENDERUSDT", "RAYUSDT", "PEPEUSDT",
    "WIFUSDT", "DOGEUSDT", "ARBUSDT", "OPUSDT", "LINKUSDT",
    "INJUSDT", "TIAUSDT", "APTUSDT", "FETUSDT", "SUIUSDT"
]

CATEGORY_NAMES = [
    "1. Solana High-Speed Scalpers",
    "2. Layer-2 Momentum (Base & Arbitrum)",
    "3. Grid & Market Makers",
    "4. Mean Reversion & Dip Catchers",
    "5. Breakout & Volatility Hunters",
    "6. DCA & Algorithmic Accumulation",
    "7. Whale & Smart Money Trackers",
    "8. Experimental & Token Creator",
    "9. Multi-Chain Macro Rotators",
    "10. Benchmarks & Control Baselines"
]


def generate_100_wallet_configs() -> List[Dict[str, Any]]:
    """Generate 100 distinct wallet configurations across 10 categories."""
    configs = []
    
    # 1. Solana High-Speed Scalpers (Wallets 1-10)
    sol_strategies = [
        ("Sol_EMA_Scalper_1m", "Solana", "1m EMA 9/21 cross scalper on SOL/JUP", "SOLUSDT"),
        ("Sol_StochRSI_Dip_5m", "Solana", "Stochastic RSI oversold bounce sniper on SOL", "SOLUSDT"),
        ("Sol_SuperTrend_Runner", "Solana", "SuperTrend (10, 3) continuation runner on SOL", "SOLUSDT"),
        ("Sol_Raydium_MicroDEX", "Solana", "Raydium micro-liquidity scalper on RAY/SOL", "RAYUSDT"),
        ("Sol_Jup_Aggregator_Flow", "Solana", "Jupiter DEX volume momentum follower on JUP", "JUPUSDT"),
        ("Sol_Render_AI_Trend", "Solana", "Render Network momentum trend follower", "RENDERUSDT"),
        ("Sol_Meme_Surge_WIF", "Solana", "High-velocity momentum chaser on WIF", "WIFUSDT"),
        ("Sol_Orderbook_Imbalance", "Solana", "Orderbook bid-ask depth imbalance predictor", "SOLUSDT"),
        ("Sol_VWAP_Pullback", "Solana", "VWAP dynamic band dip buyer on SOL", "SOLUSDT"),
        ("Sol_ATR_Volatility_Band", "Solana", "ATR channel breakout with dynamic trailing stops", "SOLUSDT"),
    ]
    for i, (name, chain, desc, target) in enumerate(sol_strategies, start=1):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[0],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0005,
            "slippage": 0.0005,
            "risk_profile": "High Velocity",
            "type": "MOMENTUM_SCALPER"
        })

    # 2. Layer-2 Momentum (Base & Arbitrum) (Wallets 11-20)
    l2_strategies = [
        ("Base_Meme_Velocity", "Base", "Base DEX meme velocity & volume surge follower", "PEPEUSDT"),
        ("Base_Aerodrome_DEX", "Base", "Aerodrome liquidity inflow momentum follower", "ETHUSDT"),
        ("Base_ETH_Beta_Scalp", "Base", "High-beta ETH derivative scalp on Base L2", "ETHUSDT"),
        ("Arb_GMX_Perp_Trend", "Arbitrum", "GMX perpetual market trend-following engine", "ARBUSDT"),
        ("Arb_Volatility_Breakout", "Arbitrum", "Arbitrum ecosystem volatility expansion chaser", "ARBUSDT"),
        ("Arb_ETH_Correlation_Arb", "Arbitrum", "Arbitrum vs Ethereum mainnet spread tracker", "ETHUSDT"),
        ("Base_SocialFi_Hunter", "Base", "Base Farcaster/Clanker social sentiment tracker", "ETHUSDT"),
        ("Arb_Camelot_DEX_Scalper", "Arbitrum", "Camelot DEX liquidity concentration scalper", "ARBUSDT"),
        ("Base_Bluechip_DCA", "Base", "Aggressive 15m dips accumulator on Base ETH", "ETHUSDT"),
        ("OP_Superchain_Rotator", "Optimism", "Optimism Superchain liquidity rotation bot", "OPUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(l2_strategies, start=11):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[1],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0006,
            "slippage": 0.0006,
            "risk_profile": "Moderate High",
            "type": "L2_MOMENTUM"
        })

    # 3. Grid & Market Makers (Wallets 21-30)
    grid_strategies = [
        ("Grid_Tight_SOL", "Solana", "Tight 0.5% arithmetic grid on SOL/USDC (10 grids)", "SOLUSDT"),
        ("Grid_Wide_SOL", "Solana", "Wide 1.8% geometric grid on SOL/USDC (6 grids)", "SOLUSDT"),
        ("Grid_Dynamic_ATR_BTC", "Multi-Chain", "Dynamic ATR volatility-expanding grid on BTC", "BTCUSDT"),
        ("Grid_Dynamic_ATR_ETH", "Multi-Chain", "Dynamic ATR volatility-expanding grid on ETH", "ETHUSDT"),
        ("Grid_Asymmetric_Bull_SOL", "Solana", "70% Buy-skewed asymmetric accumulation grid", "SOLUSDT"),
        ("Grid_Asymmetric_Bear_SOL", "Solana", "70% Sell-skewed asymmetric hedge grid", "SOLUSDT"),
        ("Grid_Micro_JUP", "Solana", "Micro-tick market maker on Jupiter DEX pair", "JUPUSDT"),
        ("Grid_Chop_Harvester_SUI", "Sui", "Chop oscillation harvester on SUI/USDT", "SUIUSDT"),
        ("Grid_Bollinger_Band_Grid", "Multi-Chain", "Auto-rebalancing grid bound to 2-sigma Bollinger bands", "ETHUSDT"),
        ("Grid_Infinity_Accumulator", "Solana", "Infinity rebalancing grid holding 50% cash / 50% SOL", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(grid_strategies, start=21):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[2],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0004,
            "slippage": 0.0003,
            "risk_profile": "Market Neutral / Chop",
            "type": "GRID_MAKER"
        })

    # 4. Mean Reversion & Dip Catchers (Wallets 31-40)
    reversion_strategies = [
        ("MeanRev_Bollinger_2Sigma", "Solana", "Buys lower Bollinger Band touch with RSI < 32", "SOLUSDT"),
        ("MeanRev_Bollinger_3Sigma", "Multi-Chain", "Extreme outlier 3-sigma flash-crash buyer", "BTCUSDT"),
        ("MeanRev_RSI_Extreme_20", "Multi-Chain", "Deep capitulation buyer when RSI(14) < 22", "ETHUSDT"),
        ("MeanRev_Double_Bottom", "Solana", "Technical W-formation double bottom pattern detector", "SOLUSDT"),
        ("MeanRev_VWAP_Deviation", "Solana", "Mean-reverts to 15m VWAP on -2.5% deviation", "SOLUSDT"),
        ("MeanRev_Keltner_Bounce", "Multi-Chain", "Keltner Channel lower band envelope mean reversion", "NEARUSDT"),
        ("MeanRev_ZScore_Scalper", "Multi-Chain", "Statistical Z-Score price-distance reversion engine", "AVAXUSDT"),
        ("MeanRev_Knife_Catcher_5Pct", "Solana", "Catches sudden 5-minute red candles > 4% drop", "SOLUSDT"),
        ("MeanRev_RSI_Divergence", "Multi-Chain", "Bullish RSI divergence detector on 15m timeframe", "ETHUSDT"),
        ("MeanRev_Overextended_Cooloff", "Solana", "Contrarian fade on parabolic rallies", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(reversion_strategies, start=31):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[3],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0005,
            "slippage": 0.0005,
            "risk_profile": "Contrarian / Dip",
            "type": "MEAN_REVERSION"
        })

    # 5. Breakout & Volatility Hunters (Wallets 41-50)
    breakout_strategies = [
        ("Breakout_Donchian_20High", "Solana", "Buys new 20-period Donchian High on SOL", "SOLUSDT"),
        ("Breakout_Volume_Surge_2X", "Multi-Chain", "Fires when 15m volume is 2.2x 20-period average", "SOLUSDT"),
        ("Breakout_Consolidation_Squeeze", "Multi-Chain", "Bollinger Band inside Keltner squeeze release", "BTCUSDT"),
        ("Breakout_AllTimeHigh_Momentum", "Solana", "Rides 24h high breakouts with trailing ATR stop", "SOLUSDT"),
        ("Breakout_Render_AI_Surge", "Solana", "AI narrative volume surge breakout on RENDER", "RENDERUSDT"),
        ("Breakout_Sui_Ecosystem_Run", "Sui", "Sui network momentum breakout runner", "SUIUSDT"),
        ("Breakout_MultiTimeframe_Sync", "Multi-Chain", "1m, 5m, and 15m trend breakout alignment", "ETHUSDT"),
        ("Breakout_Near_L1_Expansion", "Near", "Near protocol volatility expansion breakout", "NEARUSDT"),
        ("Breakout_Avax_Subnet_Surge", "Avalanche", "Avalanche volatility surge momentum engine", "AVAXUSDT"),
        ("Breakout_Parabolic_Rider", "Solana", "Aggressive momentum pyramid on strong trend days", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(breakout_strategies, start=41):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[4],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0006,
            "slippage": 0.0007,
            "risk_profile": "High Momentum",
            "type": "BREAKOUT"
        })

    # 6. DCA & Algorithmic Accumulation (Wallets 51-60)
    dca_strategies = [
        ("DCA_Micro_Hourly", "Solana", "Allocates $5 USDC every hour into SOL regardless of price", "SOLUSDT"),
        ("DCA_Martingale_Dip", "Solana", "Doubles purchase size ($10->$20->$40) on successive -2% dips", "SOLUSDT"),
        ("DCA_FearAndGreed_Dynamic", "Multi-Chain", "Buys heavily when market drops, trims when euphoric", "BTCUSDT"),
        ("DCA_Value_Averaging", "Solana", "Maintains a predetermined linear target portfolio value", "SOLUSDT"),
        ("DCA_RSI_Filtered", "Solana", "Executes scheduled DCA purchase only if RSI < 50", "SOLUSDT"),
        ("DCA_GoldenCross_Accumulate", "Multi-Chain", "Accumulates heavily after 50/200 EMA golden cross", "ETHUSDT"),
        ("DCA_Weekend_Accumulator", "Solana", "Exploits weekend low-liquidity discount dips", "SOLUSDT"),
        ("DCA_Bluechip_Trio", "Multi-Chain", "Splits purchases equally: 40% BTC, 40% SOL, 20% ETH", "BTCUSDT"),
        ("DCA_Sui_HighBeta", "Sui", "DCA accumulation into Layer 1 challenger SUI", "SUIUSDT"),
        ("DCA_Cash_Protection_Buffer", "Solana", "50% fixed cash buffer + conservative pullback DCA", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(dca_strategies, start=51):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[5],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0004,
            "slippage": 0.0003,
            "risk_profile": "Systematic Accumulation",
            "type": "DCA_ACCUMULATOR"
        })

    # 7. Whale & Smart Money Trackers (Wallets 61-70)
    whale_strategies = [
        ("Whale_Solscan_Inflow_Mirror", "Solana", "Mirrors top 20 profitable Solana DEX smart wallets", "SOLUSDT"),
        ("Whale_CEX_Outflow_Accumulator", "Multi-Chain", "Buys when exchange reserves drop (whale accumulation)", "BTCUSDT"),
        ("Whale_Orderbook_Spoof_Detector", "Multi-Chain", "Detects real institutional iceberg buy walls", "ETHUSDT"),
        ("Whale_DexScreener_Volume_Tracker", "Solana", "Tracks rapid volume acceleration in DEX pools", "JUPUSDT"),
        ("Whale_Hyperliquid_TopPnl_Copy", "Hyperliquid", "Replicates top 10 leaderboard traders on Hyperliquid", "SOLUSDT"),
        ("Whale_Smart_Money_Cluster", "Solana", "Follows clusters where >3 smart wallets accumulate", "RAYUSDT"),
        ("Whale_Divergence_Accumulation", "Multi-Chain", "Spots hidden accumulation during flat price action", "SOLUSDT"),
        ("Whale_CEX_Inflow_Short_Hedge", "Multi-Chain", "Protects capital when massive whale deposits hit CEXs", "BTCUSDT"),
        ("Whale_Uniswap_V3_Concentrated", "Base", "Tracks high-yield LP position adjustments on Base", "ETHUSDT"),
        ("Whale_Meme_Early_Sniper", "Solana", "Identifies smart money early entries into meme liquidity", "PEPEUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(whale_strategies, start=61):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[6],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0006,
            "slippage": 0.0007,
            "risk_profile": "Smart Follower",
            "type": "WHALE_TRACKER"
        })

    # 8. Experimental & Token Creator (Wallets 71-80)
    # SPECIAL EXPERIMENTAL WALLET: Wallet 77 - The Meme Coin Bonding Curve Deployer!
    experimental_strategies = [
        ("Exp_CrossDEX_Arbitrage_Sim", "Solana", "Simulates micro-spread arb between Raydium & Orca", "SOLUSDT"),
        ("Exp_HighBeta_Meme_Trio", "Multi-Chain", "Momentum basket rebalanced across PEPE, WIF, DOGE", "PEPEUSDT"),
        ("Exp_FundingRate_CashCarry", "Hyperliquid", "Earns positive perp funding rate hedged with spot", "SOLUSDT"),
        ("Exp_Volatility_Breakout_Strangle", "Multi-Chain", "Straddle simulation expecting massive volatility", "BTCUSDT"),
        ("Exp_AI_Agent_Token_Basket", "Solana", "Momentum weighting on AI tokens (RENDER, FET)", "RENDERUSDT"),
        ("Exp_Perp_Basis_Arb", "Arbitrum", "Exploits futures premium vs spot index spread", "ETHUSDT"),
        ("Exp_PumpFun_TokenDeployer_77", "Solana", "CREATES & LAUNCHES 'PAPERCOIN' on Pump.fun bonding curve ($100 seed liquidity)!", "SOLUSDT"),
        ("Exp_Liquidity_Slippage_Harvester", "Solana", "Provides micro-liquidity during extreme volatility", "RAYUSDT"),
        ("Exp_DePIN_Infra_Basket", "Solana", "Decentralized Physical Infra sector momentum basket", "RENDERUSDT"),
        ("Exp_Inverse_Sentiment_Contrarian", "Multi-Chain", "Fades top trending social media sentiment tokens", "PEPEUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(experimental_strategies, start=71):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[7],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0008,
            "slippage": 0.0010,
            "risk_profile": "Experimental / Degen",
            "type": "EXPERIMENTAL" if i != 77 else "TOKEN_DEPLOYER"
        })

    # 9. Multi-Chain Macro Rotators (Wallets 81-90)
    rotator_strategies = [
        ("Rotator_Relative_Strength_L1", "Multi-Chain", "Rotates 100% capital to the single strongest Layer 1", "SOLUSDT"),
        ("Rotator_ETH_vs_SOL_Ratio", "Multi-Chain", "Trades the ETH/SOL cross pair momentum expansion", "SOLUSDT"),
        ("Rotator_BTC_Dominance_Shift", "Multi-Chain", "Allocates to Altcoins when BTC dominance drops", "SOLUSDT"),
        ("Rotator_Sector_Momentum", "Multi-Chain", "Rotates between AI, DeFi, and Meme sectors weekly", "RENDERUSDT"),
        ("Rotator_Top3_Winners_Momentum", "Multi-Chain", "Holds the top 3 best-performing coins of the last 24h", "SUIUSDT"),
        ("Rotator_RiskOn_RiskOff_Switch", "Multi-Chain", "100% Cash when BTC < EMA200, 100% Alts when > EMA50", "BTCUSDT"),
        ("Rotator_L2_Ecosystem_Surge", "Base", "Rotates between Base, Arbitrum, and Optimism leaders", "ETHUSDT"),
        ("Rotator_High_Beta_Spring", "Multi-Chain", "Rotates into oversold altcoins with highest recovery beta", "NEARUSDT"),
        ("Rotator_Volatility_Parity", "Multi-Chain", "Risk-parity weighted allocation across SOL, BTC, ETH", "BTCUSDT"),
        ("Rotator_Macro_Liquidity_Cycle", "Multi-Chain", "Follows global macro stablecoin liquidity inflows", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(rotator_strategies, start=81):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[8],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0006,
            "slippage": 0.0005,
            "risk_profile": "Dynamic Asset Rotation",
            "type": "ROTATOR"
        })

    # 10. Benchmarks & Control Baselines (Wallets 91-100)
    benchmark_strategies = [
        ("HODL_Pure_SOL_Control", "Solana", "Passive 100% Buy & Hold SOL benchmark baseline", "SOLUSDT"),
        ("HODL_Pure_BTC_Control", "Bitcoin", "Passive 100% Buy & Hold BTC benchmark baseline", "BTCUSDT"),
        ("HODL_Pure_ETH_Control", "Ethereum", "Passive 100% Buy & Hold ETH benchmark baseline", "ETHUSDT"),
        ("HODL_50BTC_50ETH", "Multi-Chain", "Passive 50% BTC / 50% ETH classic portfolio", "BTCUSDT"),
        ("HODL_Equal_Weight_Top5", "Multi-Chain", "Equal 20% split in SOL, BTC, ETH, SUI, NEAR", "SOLUSDT"),
        ("Control_Pure_Cash_USDC", "Solana", "100% Liquid USDC risk-free cash baseline ($100.00)", "SOLUSDT"),
        ("Control_Monkey_Random_Flipper", "Solana", "Executes random 50/50 buy/sell decisions (control test)", "SOLUSDT"),
        ("Control_Inverted_Trend_Worst", "Solana", "Buys at resistance, sells at support (antipattern test)", "SOLUSDT"),
        ("Control_50Cash_50SOL", "Solana", "Conservative 50% Cash / 50% SOL static portfolio", "SOLUSDT"),
        ("Control_Max_Leverage_Simulator", "Solana", "Simulates 10x leverage volatility impact on $100", "SOLUSDT")
    ]
    for i, (name, chain, desc, target) in enumerate(benchmark_strategies, start=91):
        configs.append({
            "id": f"wallet_{i:03d}",
            "name": name,
            "category": CATEGORY_NAMES[9],
            "chain": chain,
            "description": desc,
            "target_symbol": target,
            "fee_rate": 0.0005,
            "slippage": 0.0005,
            "risk_profile": "Control Benchmark",
            "type": "BENCHMARK"
        })

    return configs


class Tournament100Engine:
    def __init__(self):
        self.state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(TOURNAMENT_FILE):
            try:
                with open(TOURNAMENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if len(data.get("wallets", [])) == TOTAL_WALLETS:
                        return data
            except Exception as e:
                print(f"[Warning] Loading existing state failed: {e}. Reinitializing.")

        configs = generate_100_wallet_configs()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        wallets = []
        for cfg in configs:
            wallets.append({
                "id": cfg["id"],
                "name": cfg["name"],
                "category": cfg["category"],
                "chain": cfg["chain"],
                "description": cfg["description"],
                "target_symbol": cfg["target_symbol"],
                "risk_profile": cfg["risk_profile"],
                "type": cfg["type"],
                "starting_balance": INITIAL_CAPITAL_PER_WALLET,
                "cash": INITIAL_CAPITAL_PER_WALLET,
                "positions_value": 0.0,
                "total_equity": INITIAL_CAPITAL_PER_WALLET,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "positions": [],
                "recent_trade": "None yet",
                "status": "ACTIVE",
                # Special fields for Wallet 77 (Token Creator)
                "created_token_meta": {
                    "token_name": "PAPERCOIN",
                    "ticker": "$PAPER",
                    "bonding_curve_progress_pct": 14.5,
                    "market_cap_usd": 7250.0,
                    "dev_holdings_pct": 70.0,
                    "liquidity_pool_usd": 100.0,
                    "graduated_to_raydium": False
                } if cfg["id"] == "wallet_077" else None
            })

        state = {
            "tournament_name": "CryptoArena 100X - 100-Wallet Darwinian Multichain Lab",
            "created_at": now_iso,
            "last_cycle": now_iso,
            "cycle_count": 0,
            "total_initial_capital": INITIAL_CAPITAL_PER_WALLET * TOTAL_WALLETS,
            "total_current_equity": INITIAL_CAPITAL_PER_WALLET * TOTAL_WALLETS,
            "total_pnl_usd": 0.0,
            "total_pnl_pct": 0.0,
            "best_wallet": None,
            "worst_wallet": None,
            "wallets": wallets,
            "category_summary": {}
        }
        self._save_state(state)
        return state

    def _save_state(self, state: Optional[Dict[str, Any]] = None):
        if state is not None:
            self.state = state
        self.state["last_cycle"] = datetime.now(timezone.utc).isoformat()
        with open(TOURNAMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def fetch_batch_market_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch 24h ticker prices and stats for all tracked assets in 1 batch call."""
        market = {}
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            r = requests.get(url, timeout=7).json()
            if isinstance(r, list):
                lookup = {item["symbol"]: item for item in r if item["symbol"] in MARKET_SYMBOLS}
                for sym, data in lookup.items():
                    price = float(data.get("lastPrice", 0.0))
                    change = float(data.get("priceChangePercent", 0.0))
                    high = float(data.get("highPrice", price))
                    low = float(data.get("lowPrice", price))
                    vol = float(data.get("volume", 0.0))
                    market[sym] = {
                        "symbol": sym,
                        "price": price,
                        "change_24h": change,
                        "high_24h": high,
                        "low_24h": low,
                        "volume": vol,
                        # Estimated indicators from high/low/close range
                        "est_rsi": min(95.0, max(15.0, 50.0 + (change * 1.8))),
                        "trend": "BULL" if change > 0 else "BEAR"
                    }
        except Exception as e:
            print(f"[Warning] Batch market feed error: {e}. Using fallback prices.")
            # Fallback realistic prices if offline
            fallback_prices = {
                "SOLUSDT": 116.30, "BTCUSDT": 63400.0, "ETHUSDT": 2650.0,
                "SUIUSDT": 1.55, "AVAXUSDT": 27.8, "NEARUSDT": 4.85,
                "JUPUSDT": 0.306, "RENDERUSDT": 1.77, "RAYUSDT": 1.74,
                "PEPEUSDT": 0.0000085, "WIFUSDT": 2.10, "DOGEUSDT": 0.115,
                "ARBUSDT": 0.58, "OPUSDT": 1.45, "LINKUSDT": 11.20
            }
            for sym, p in fallback_prices.items():
                market[sym] = {
                    "symbol": sym, "price": p, "change_24h": 2.5,
                    "high_24h": p * 1.05, "low_24h": p * 0.95, "volume": 100000.0,
                    "est_rsi": 55.0, "trend": "BULL"
                }
        return market

    def evaluate_wallet(self, w: Dict[str, Any], market: Dict[str, Dict[str, Any]]):
        """Evaluate a single wallet's strategy against live market data."""
        w_type = w.get("type", "MOMENTUM_SCALPER")
        target_sym = w["target_symbol"]
        m = market.get(target_sym, market.get("SOLUSDT"))
        if not m:
            return

        price = m["price"]
        change = m["change_24h"]
        rsi = m["est_rsi"]
        cash = w["cash"]

        # ==========================================
        # Strategy Execution Logic by Archetype
        # ==========================================

        # 1. HODL Benchmarks
        if w_type == "BENCHMARK":
            if w["id"] == "wallet_096":  # Pure Cash
                w["total_equity"] = 100.00
                w["cash"] = 100.00
                w["positions"] = []
                w["total_pnl"] = 0.0
                w["total_pnl_pct"] = 0.0
                return
            elif w["id"] == "wallet_097":  # Monkey Random
                if random.random() < 0.2:
                    if cash > 20.0:
                        buy_amt = min(cash * 0.5, 30.0)
                        qty = buy_amt / price
                        w["cash"] -= buy_amt
                        w["positions"].append({"symbol": target_sym, "qty": qty, "entry": price})
                        w["total_trades"] += 1
                        w["recent_trade"] = f"Random Coin-Flip Buy: ${buy_amt:.2f} {target_sym}"
            else:
                # Standard HODL: Invests 95% on day 1 and holds
                if not w["positions"] and cash > 20.0:
                    invest_amt = cash * 0.95
                    qty = invest_amt / price
                    w["cash"] -= invest_amt
                    w["positions"].append({"symbol": target_sym, "qty": qty, "entry": price})
                    w["total_trades"] += 1
                    w["recent_trade"] = f"Initial HODL Buy: {qty:.4f} {target_sym} @ ${price:.2f}"

        # 2. Token Deployer (Wallet 77 - Pump.fun Simulation)
        elif w_type == "TOKEN_DEPLOYER":
            meta = w.get("created_token_meta", {})
            # Simulates retail bot volume on the newly created meme token!
            rand_action = random.choice(["BUY_INFLOW", "BUY_INFLOW", "DUMP", "NEUTRAL"])
            if rand_action == "BUY_INFLOW":
                inflow = round(random.uniform(5.0, 25.0), 2)
                meta["liquidity_pool_usd"] += inflow
                meta["market_cap_usd"] += inflow * 28.0
                meta["bonding_curve_progress_pct"] = min(100.0, meta["bonding_curve_progress_pct"] + random.uniform(1.2, 3.8))
                w["recent_trade"] = f"🚀 Inflow on $PAPER bonding curve: +${inflow:.2f} USDC from retail buyers!"
            elif rand_action == "DUMP":
                outflow = round(random.uniform(3.0, 12.0), 2)
                meta["liquidity_pool_usd"] = max(20.0, meta["liquidity_pool_usd"] - outflow)
                meta["market_cap_usd"] = max(2000.0, meta["market_cap_usd"] - (outflow * 20.0))
                meta["bonding_curve_progress_pct"] = max(5.0, meta["bonding_curve_progress_pct"] - random.uniform(0.5, 2.0))
                w["recent_trade"] = f"⚠️ Early sniper dumped $PAPER: -${outflow:.2f} USDC."

            # Calculate valuation of Creator's 70% dev holding
            dev_share_value = round((meta["market_cap_usd"] * (meta["dev_holdings_pct"] / 100.0)) / 100.0, 2)
            # Bound realistic liquidity capture
            w["positions_value"] = min(dev_share_value, meta["liquidity_pool_usd"] * 1.5)
            w["total_equity"] = round(w["cash"] + w["positions_value"], 2)
            w["total_pnl"] = round(w["total_equity"] - INITIAL_CAPITAL_PER_WALLET, 2)
            w["total_pnl_pct"] = round((w["total_pnl"] / INITIAL_CAPITAL_PER_WALLET) * 100.0, 2)
            w["created_token_meta"] = meta
            return

        # 3. Momentum & Scalpers
        elif w_type in ["MOMENTUM_SCALPER", "L2_MOMENTUM", "BREAKOUT"]:
            # Buy if strong positive 24h change & healthy RSI
            if change > 1.5 and 45 <= rsi <= 75:
                if len(w["positions"]) < 2 and cash >= 30.0:
                    stake = min(35.0, cash - 15.0)
                    qty = stake / price
                    w["cash"] -= stake
                    w["positions"].append({
                        "symbol": target_sym, "qty": qty, "entry": price,
                        "tp": price * 1.045, "sl": price * 0.975
                    })
                    w["total_trades"] += 1
                    w["recent_trade"] = f"Long Momentum Entry: {qty:.3f} {target_sym} @ ${price:.2f}"

        # 4. Mean Reversion & Dip Catchers
        elif w_type == "MEAN_REVERSION":
            # Buy oversold dips (RSI < 40 or negative change)
            if rsi < 42 or change < -1.0:
                if len(w["positions"]) < 2 and cash >= 30.0:
                    stake = min(40.0, cash - 10.0)
                    qty = stake / price
                    w["cash"] -= stake
                    w["positions"].append({
                        "symbol": target_sym, "qty": qty, "entry": price,
                        "tp": price * 1.035, "sl": price * 0.97
                    })
                    w["total_trades"] += 1
                    w["recent_trade"] = f"Oversold Dip Buy: {qty:.3f} {target_sym} @ ${price:.2f}"

        # 5. Grid Market Makers
        elif w_type == "GRID_MAKER":
            # Grid holds 50% in asset, 50% in cash and captures oscillations
            if not w["positions"] and cash >= 45.0:
                half = cash * 0.5
                qty = half / price
                w["cash"] -= half
                w["positions"].append({"symbol": target_sym, "qty": qty, "entry": price, "grid_base": price})
                w["total_trades"] += 1
                w["recent_trade"] = f"Initialized Grid: {qty:.3f} {target_sym} (50% inventory)"
            elif w["positions"]:
                # Micro-oscillation fee capture
                grid_pos = w["positions"][0]
                grid_base = grid_pos.get("grid_base", price)
                price_diff_pct = abs((price - grid_base) / grid_base) * 100.0
                if price_diff_pct >= 0.8:
                    grid_profit = round(grid_pos["qty"] * price * 0.006, 2)
                    w["cash"] += grid_profit
                    w["realized_pnl"] += grid_profit
                    w["winning_trades"] += 1
                    w["total_trades"] += 1
                    grid_pos["grid_base"] = price
                    w["recent_trade"] = f"Grid arbitrage tick captured: +${grid_profit:.2f} USDC"

        # 6. Systematic DCA
        elif w_type == "DCA_ACCUMULATOR":
            # Steady programmatic buying
            if cash >= 15.0:
                dca_amt = min(15.0, cash * 0.25)
                qty = dca_amt / price
                w["cash"] -= dca_amt
                w["positions"].append({"symbol": target_sym, "qty": qty, "entry": price})
                w["total_trades"] += 1
                w["recent_trade"] = f"Programmatic Micro-DCA: +${dca_amt:.2f} into {target_sym}"

        # 7. Whale Trackers & Rotators
        elif w_type in ["WHALE_TRACKER", "ROTATOR"]:
            if change > 2.0 and cash >= 35.0:
                stake = min(40.0, cash - 10.0)
                qty = stake / price
                w["cash"] -= stake
                w["positions"].append({
                    "symbol": target_sym, "qty": qty, "entry": price,
                    "tp": price * 1.05, "sl": price * 0.97
                })
                w["total_trades"] += 1
                w["recent_trade"] = f"Followed Inflow Signal: {qty:.3f} {target_sym} @ ${price:.2f}"

        # ==========================================
        # Position Management & Mark-to-Market
        # ==========================================
        active_positions = []
        pos_val = 0.0

        for p in w["positions"]:
            curr_price = market.get(p["symbol"], {}).get("price", price)
            entry = p["entry"]
            qty = p["qty"]
            current_val = qty * curr_price
            pos_val += current_val

            # Check TP / SL for non-HODL positions
            if "tp" in p and curr_price >= p["tp"]:
                profit = (curr_price - entry) * qty
                w["cash"] += current_val
                w["realized_pnl"] += profit
                w["winning_trades"] += 1
                w["total_trades"] += 1
                w["recent_trade"] = f"🎯 TP Hit: Sold {p['symbol']} at ${curr_price:.2f} (+${profit:.2f})"
                continue
            elif "sl" in p and curr_price <= p["sl"]:
                loss = (curr_price - entry) * qty
                w["cash"] += current_val
                w["realized_pnl"] += loss
                w["losing_trades"] += 1
                w["total_trades"] += 1
                w["recent_trade"] = f"🛑 Stop Loss: Sold {p['symbol']} at ${curr_price:.2f} (${loss:.2f})"
                continue

            active_positions.append(p)

        w["positions"] = active_positions
        w["positions_value"] = round(pos_val, 2)
        total_equity = round(w["cash"] + pos_val, 2)
        w["total_equity"] = total_equity
        w["total_pnl"] = round(total_equity - INITIAL_CAPITAL_PER_WALLET, 2)
        w["total_pnl_pct"] = round((w["total_pnl"] / INITIAL_CAPITAL_PER_WALLET) * 100.0, 2)

        tot_t = w["total_trades"]
        w["win_rate_pct"] = round((w["winning_trades"] / tot_t * 100.0), 1) if tot_t > 0 else 0.0

        # Update status
        if total_equity >= 120.0:
            w["status"] = "CHAMPION"
        elif total_equity >= 100.0:
            w["status"] = "PROFITABLE"
        elif total_equity >= 80.0:
            w["status"] = "SURVIVING"
        else:
            w["status"] = "BLEEDING"

    def run_tournament_cycle(self) -> Dict[str, Any]:
        """Execute a full live evaluation pass for all 100 wallets."""
        market = self.fetch_batch_market_data()
        self.state["cycle_count"] += 1

        for w in self.state["wallets"]:
            self.evaluate_wallet(w, market)

        # Sort wallets by total equity descending for leaderboard
        self.state["wallets"].sort(key=lambda x: x["total_equity"], reverse=True)

        tot_eq = sum(w["total_equity"] for w in self.state["wallets"])
        self.state["total_current_equity"] = round(tot_eq, 2)
        self.state["total_pnl_usd"] = round(tot_eq - self.state["total_initial_capital"], 2)
        self.state["total_pnl_pct"] = round((self.state["total_pnl_usd"] / self.state["total_initial_capital"]) * 100.0, 2)

        self.state["best_wallet"] = {
            "id": self.state["wallets"][0]["id"],
            "name": self.state["wallets"][0]["name"],
            "equity": self.state["wallets"][0]["total_equity"],
            "pnl_pct": self.state["wallets"][0]["total_pnl_pct"],
            "category": self.state["wallets"][0]["category"]
        }
        self.state["worst_wallet"] = {
            "id": self.state["wallets"][-1]["id"],
            "name": self.state["wallets"][-1]["name"],
            "equity": self.state["wallets"][-1]["total_equity"],
            "pnl_pct": self.state["wallets"][-1]["total_pnl_pct"],
            "category": self.state["wallets"][-1]["category"]
        }

        # Category Aggregation
        cat_stats = {}
        for c_name in CATEGORY_NAMES:
            c_wallets = [w for w in self.state["wallets"] if w["category"] == c_name]
            if c_wallets:
                avg_eq = sum(w["total_equity"] for w in c_wallets) / len(c_wallets)
                avg_pnl = sum(w["total_pnl_pct"] for w in c_wallets) / len(c_wallets)
                best_w = max(c_wallets, key=lambda x: x["total_equity"])
                cat_stats[c_name] = {
                    "count": len(c_wallets),
                    "avg_equity": round(avg_eq, 2),
                    "avg_pnl_pct": round(avg_pnl, 2),
                    "best_performer": f"{best_w['name']} (${best_w['total_equity']:.2f})"
                }
        self.state["category_summary"] = cat_stats

        self._save_state()
        self.generate_html_dashboard(market)
        return self.state

    def generate_html_dashboard(self, market: Dict[str, Any]):
        """Generates a comprehensive interactive 100-wallet leaderboard dashboard."""
        s = self.state
        best = s["best_wallet"] or {}
        worst = s["worst_wallet"] or {}

        # Token creator meta (Wallet 77)
        w77 = next((w for w in s["wallets"] if w["id"] == "wallet_077"), None)
        token_meta = w77.get("created_token_meta", {}) if w77 else {}

        # Category Cards
        cat_cards = ""
        for c_name, c_data in s.get("category_summary", {}).items():
            col = "text-emerald-400" if c_data["avg_pnl_pct"] >= 0 else "text-rose-400"
            cat_cards += f"""
            <div class="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60 shadow flex flex-col justify-between">
                <div>
                    <div class="text-xs font-bold text-slate-400 truncate mb-1">{c_name}</div>
                    <div class="text-xl font-extrabold text-white">${c_data['avg_equity']:.2f} <span class="text-xs font-normal text-slate-400">avg</span></div>
                    <div class="text-xs font-semibold {col} mt-0.5">{c_data['avg_pnl_pct']:+.2f}% avg ROI</div>
                </div>
                <div class="mt-3 pt-2 border-t border-slate-700/50 text-xs text-slate-400 truncate">
                    ⭐ Top: <span class="text-cyan-300">{c_data['best_performer']}</span>
                </div>
            </div>
            """

        # Table rows for all 100 wallets
        rows = ""
        for rank, w in enumerate(s["wallets"], start=1):
            badge = ""
            if rank == 1:
                badge = "🥇 "
            elif rank == 2:
                badge = "🥈 "
            elif rank == 3:
                badge = "🥉 "

            col = "text-emerald-400 font-bold" if w["total_pnl"] >= 0 else "text-rose-400 font-bold"
            status_badge = {
                "CHAMPION": '<span class="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30">🏆 Champion</span>',
                "PROFITABLE": '<span class="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Profitable</span>',
                "SURVIVING": '<span class="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30">Surviving</span>',
                "BLEEDING": '<span class="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30">Bleeding</span>'
            }.get(w["status"], '<span class="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300">Active</span>')

            chain_col = {
                "Solana": "bg-purple-500/20 text-purple-300 border-purple-500/30",
                "Base": "bg-blue-500/20 text-blue-300 border-blue-500/30",
                "Arbitrum": "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
                "Multi-Chain": "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
            }.get(w["chain"], "bg-slate-700/40 text-slate-300 border-slate-600")

            rows += f"""
            <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
                <td class="py-2.5 px-3 font-mono font-bold text-slate-300">{badge}#{rank}</td>
                <td class="py-2.5 px-3">
                    <div class="font-bold text-white text-sm">{w['name']}</div>
                    <div class="text-xs text-slate-400">{w['description']}</div>
                </td>
                <td class="py-2.5 px-3">
                    <span class="px-2 py-0.5 rounded text-xs font-semibold border {chain_col}">{w['chain']}</span>
                </td>
                <td class="py-2.5 px-3 text-xs text-slate-300 truncate max-w-[140px]">{w['category'].split('. ')[-1]}</td>
                <td class="py-2.5 px-3 font-mono font-bold text-white">${w['total_equity']:.2f}</td>
                <td class="py-2.5 px-3 font-mono {col}">{w['total_pnl']:+.2f} USD ({w['total_pnl_pct']:+.2f}%)</td>
                <td class="py-2.5 px-3 text-xs font-mono text-slate-300">${w['cash']:.2f} / ${w['positions_value']:.2f}</td>
                <td class="py-2.5 px-3 text-xs font-mono text-slate-300">{w['win_rate_pct']:.0f}% ({w['total_trades']}T)</td>
                <td class="py-2.5 px-3 text-xs">{status_badge}</td>
                <td class="py-2.5 px-3 text-xs text-slate-400 truncate max-w-[200px]">{w.get('recent_trade', 'Idle')}</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CryptoArena 100X - 100-Wallet Darwinian Multichain Lab</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: radial-gradient(circle at top right, #0b1329, #020617); }}
    </style>
</head>
<body class="text-slate-100 min-h-screen p-4 md:p-8 font-sans">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur">
            <div>
                <div class="flex items-center gap-3">
                    <span class="text-3xl">🧬</span>
                    <div>
                        <h1 class="text-2xl font-black text-white tracking-tight">CryptoArena 100X - 100-Wallet Multichain Lab</h1>
                        <p class="text-sm text-cyan-400 font-mono">100 Independent Paper Wallets &bull; $100.00 Initial Bankroll Each ($10,000 Total Capital) &bull; Darwinian Evolution</p>
                    </div>
                </div>
            </div>
            <div class="mt-4 md:mt-0 flex items-center gap-3">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Cycle #{s['cycle_count']} Live
                </span>
                <span class="text-xs text-slate-400 font-mono">Updated: {s['last_cycle'][:19].replace('T', ' ')} UTC</span>
            </div>
        </header>

        <!-- KPI Summary Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Total Tournament Capital</div>
                <div class="text-3xl font-black text-white">${s['total_current_equity']:,.2f}</div>
                <div class="text-xs mt-1 text-slate-400">Starting: $10,000.00 USDC</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Tournament Net Return</div>
                <div class="text-3xl font-black {'text-emerald-400' if s['total_pnl_usd']>=0 else 'text-rose-400'}">{s['total_pnl_usd']:+,.2f} USD <span class="text-base font-semibold">({s['total_pnl_pct']:+.2f}%)</span></div>
                <div class="text-xs mt-1 text-slate-400">Aggregate 100 Wallets</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">🏆 #1 Leaderboard Champion</div>
                <div class="text-xl font-black text-amber-300 truncate">{best.get('name', 'N/A')}</div>
                <div class="text-xs mt-1 text-emerald-400 font-bold">${best.get('equity', 0):.2f} ({best.get('pnl_pct', 0):+.2f}%)</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">🩸 Largest Drawdown</div>
                <div class="text-xl font-black text-rose-400 truncate">{worst.get('name', 'N/A')}</div>
                <div class="text-xs mt-1 text-rose-400 font-bold">${worst.get('equity', 0):.2f} ({worst.get('pnl_pct', 0):+.2f}%)</div>
            </div>
        </div>

        <!-- Special Feature: Wallet 77 Token Deployer Launchpad Banner -->
        {f'''
        <div class="bg-gradient-to-r from-purple-950/60 via-slate-900/80 to-pink-950/60 border border-purple-500/40 rounded-2xl p-6 shadow-xl">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <div class="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 mb-2">
                        <span>🧪 Experimental Wallet 77</span> &bull; <span>Solana Pump.fun Simulator</span>
                    </div>
                    <h3 class="text-lg font-black text-white">Launched Token: <span class="text-yellow-400">{token_meta.get('token_name', 'PAPERCOIN')} ({token_meta.get('ticker', '$PAPER')})</span></h3>
                    <p class="text-xs text-slate-300 max-w-2xl mt-1">Wallet 77 allocated its $100.00 initial paper capital to deploy a meme coin on a Solana bonding curve. Simulating live buyer inflows, sniper dumps, and Raydium graduation!</p>
                </div>
                <div class="grid grid-cols-3 gap-4 text-center bg-slate-900/70 p-4 rounded-xl border border-slate-800">
                    <div>
                        <div class="text-xs text-slate-400">Bonding Curve</div>
                        <div class="text-lg font-black text-purple-400">{token_meta.get('bonding_curve_progress_pct', 0):.1f}%</div>
                    </div>
                    <div>
                        <div class="text-xs text-slate-400">Market Cap</div>
                        <div class="text-lg font-black text-cyan-300">${token_meta.get('market_cap_usd', 0):,.0f}</div>
                    </div>
                    <div>
                        <div class="text-xs text-slate-400">Wallet 77 Value</div>
                        <div class="text-lg font-black text-emerald-400">${w77['total_equity']:.2f}</div>
                    </div>
                </div>
            </div>
        </div>
        ''' if w77 else ''}

        <!-- 10 Strategy Categories Overview -->
        <div>
            <h3 class="text-lg font-bold text-white mb-3 flex items-center justify-between">
                <span>📊 Category Performance Matrix (10 Strategies &times; 10 Wallets)</span>
                <span class="text-xs font-normal text-slate-400">Ranked by category average equity</span>
            </h3>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
                {cat_cards}
            </div>
        </div>

        <!-- 100-Wallet Leaderboard Table -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
                <div>
                    <h3 class="text-lg font-bold text-white">🏆 The 100-Wallet Live Leaderboard</h3>
                    <p class="text-xs text-slate-400">All 100 wallets ranked in real time by net paper equity</p>
                </div>
                <div class="text-xs text-slate-400">
                    Filter: All 100 Wallets Displayed
                </div>
            </div>

            <div class="overflow-x-auto max-h-[600px] overflow-y-auto border border-slate-800 rounded-xl">
                <table class="w-full text-left text-xs">
                    <thead class="sticky top-0 bg-slate-950 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800">
                        <tr>
                            <th class="py-3 px-3">Rank</th>
                            <th class="py-3 px-3">Wallet & Strategy</th>
                            <th class="py-3 px-3">Chain</th>
                            <th class="py-3 px-3">Category</th>
                            <th class="py-3 px-3">Equity</th>
                            <th class="py-3 px-3">Total PnL</th>
                            <th class="py-3 px-3">Cash / Pos</th>
                            <th class="py-3 px-3">Win% (Trades)</th>
                            <th class="py-3 px-3">Status</th>
                            <th class="py-3 px-3">Recent Trade</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60 font-sans">
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(html)

    def print_terminal_summary(self):
        s = self.state
        print("\n" + "=" * 80)
        print("🧬 CRYPTOARENA 100X - 100-WALLET TOURNAMENT LEADERBOARD 🧬")
        print("=" * 80)
        print(f"• Cycle: #{s['cycle_count']} | Time: {s['last_cycle']}")
        print(f"• Total Capital:    ${s['total_current_equity']:,.2f} USDC (Starting: ${s['total_initial_capital']:,.2f})")
        print(f"• Aggregate Return: ${s['total_pnl_usd']:+,.2f} ({s['total_pnl_pct']:+.2f}%) across 100 wallets")
        best = s["best_wallet"] or {}
        worst = s["worst_wallet"] or {}
        print(f"• 🥇 #1 Leader:     {best.get('name')} -> ${best.get('equity', 0):.2f} ({best.get('pnl_pct', 0):+.2f}%)")
        print(f"• 🩸 Lowest:        {worst.get('name')} -> ${worst.get('equity', 0):.2f} ({worst.get('pnl_pct', 0):+.2f}%)")
        print("-" * 80)
        print(f"{'Rank':<5} | {'Wallet ID':<11} | {'Chain':<10} | {'Category':<22} | {'Equity ($)':<10} | {'PnL (%)':<10} | {'Status'}")
        print("-" * 80)
        for i, w in enumerate(s["wallets"][:15], start=1):
            print(f"#{i:<4} | {w['name'][:11]:<11} | {w['chain'][:10]:<10} | {w['category'][:22]:<22} | ${w['total_equity']:<9.2f} | {w['total_pnl_pct']:<+9.2f}% | {w['status']}")
        print(f"... and 85 more wallets running in parallel ...")
        print("-" * 80)
        print(f"📁 Full Visual Dashboard: {DASHBOARD_FILE}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    engine = Tournament100Engine()
    if "--reset" in sys.argv:
        if os.path.exists(TOURNAMENT_FILE):
            os.remove(TOURNAMENT_FILE)
        engine = Tournament100Engine()
        print("Tournament reset with fresh $100.00 for all 100 wallets.")

    engine.run_tournament_cycle()
    engine.print_terminal_summary()

    if "--loop" in sys.argv:
        interval = 60
        for arg in sys.argv:
            if arg.startswith("--interval="):
                try:
                    interval = int(arg.split("=")[1])
                except ValueError:
                    pass
        print(f"🔄 Running autonomous tournament loop every {interval}s. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(interval)
                engine.run_tournament_cycle()
                engine.print_terminal_summary()
        except KeyboardInterrupt:
            print("Loop stopped.")

