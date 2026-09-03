"""
Market Feed Module
Fetches real-time OHLCV candles, tickers, and orderbook data from Binance/Bybit via CCXT.
Calculates technical indicators on dataframes.
"""
import time
import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import ccxt

logger = logging.getLogger("CryptoArena.MarketFeed")

class MarketFeed:
    def __init__(self, exchange_id: str = "binance", timeframe: str = "15m", limit: int = 100):
        self.exchange_id = exchange_id
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = None
        self.cached_candles: Dict[str, pd.DataFrame] = {}
        self.cached_tickers: Dict[str, Dict[str, Any]] = {}
        self.last_update_time = 0
        self._init_exchange()

    def _init_exchange(self):
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': 10000,
            })
            logger.info(f"Initialized CCXT exchange: {self.exchange_id}")
        except Exception as e:
            logger.error(f"Failed to initialize exchange {self.exchange_id}: {e}. Trying fallback 'bybit'.")
            try:
                self.exchange = ccxt.bybit({'enableRateLimit': True})
            except Exception as e2:
                logger.error(f"Failed to initialize fallback exchange: {e2}")

    def _symbol_to_raw(self, symbol: str) -> str:
        return symbol.replace('/', '').replace(':USDT', '').upper()

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetches latest ticker with price, 24h volume, bid, ask with ultra-low memory direct API."""
        try:
            if self.exchange and hasattr(self.exchange, 'publicGetTicker24hr'):
                raw = self.exchange.publicGetTicker24hr({'symbol': self._symbol_to_raw(symbol)})
                self.cached_tickers[symbol] = {
                    'symbol': symbol,
                    'price': float(raw.get('lastPrice') or 0.0),
                    'bid': float(raw.get('bidPrice') or raw.get('lastPrice') or 0.0),
                    'ask': float(raw.get('askPrice') or raw.get('lastPrice') or 0.0),
                    'volume_24h': float(raw.get('volume') or 0.0),
                    'change_24h_pct': float(raw.get('priceChangePercent') or 0.0),
                    'timestamp': int(raw.get('closeTime') or time.time() * 1000)
                }
                return self.cached_tickers[symbol]
        except Exception:
            pass

        try:
            if self.exchange:
                ticker = self.exchange.fetch_ticker(symbol)
                self.cached_tickers[symbol] = {
                    'symbol': symbol,
                    'price': float(ticker.get('last') or ticker.get('close') or 0.0),
                    'bid': float(ticker.get('bid') or ticker.get('last') or 0.0),
                    'ask': float(ticker.get('ask') or ticker.get('last') or 0.0),
                    'volume_24h': float(ticker.get('baseVolume') or 0.0),
                    'change_24h_pct': float(ticker.get('percentage') or 0.0),
                    'timestamp': ticker.get('timestamp') or int(time.time() * 1000)
                }
                return self.cached_tickers[symbol]
        except Exception as e:
            logger.warning(f"⚠️ [MARKET_FEED] Exchange fetch_ticker error for {symbol}: {e}")

        # Fallback to cached or synthetic estimate
        if symbol in self.cached_tickers:
            return self.cached_tickers[symbol]

        logger.warning(f"🚨 [DATA TRANSPARENCY WARNING] Generating synthetic fallback ticker for {symbol} because exchange API and cache are unavailable.")
        return {'symbol': symbol, 'price': 100.0, 'bid': 99.95, 'ask': 100.05, 'volume_24h': 100000, 'change_24h_pct': 0.0, 'timestamp': int(time.time() * 1000), 'is_synthetic': True}

    def fetch_ohlcv_dataframe(self, symbol: str, timeframe: Optional[str] = None) -> pd.DataFrame:
        """Fetches OHLCV and calculates indicators into a Pandas DataFrame using low-memory direct klines."""
        tf = timeframe or self.timeframe
        # 1. Fast direct kline endpoint (bypasses memory-heavy load_markets)
        try:
            if self.exchange and hasattr(self.exchange, 'publicGetKlines'):
                klines = self.exchange.publicGetKlines({
                    'symbol': self._symbol_to_raw(symbol),
                    'interval': tf,
                    'limit': min(self.limit, 60)
                })
                raw_ohlcv = [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])] for k in klines]
                df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['symbol'] = symbol
                df = self.calculate_indicators(df)
                self.cached_candles[symbol] = df
                return df
        except Exception:
            pass

        try:
            if self.exchange:
                raw_ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=tf, limit=min(self.limit, 60))
                df = pd.DataFrame(raw_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['symbol'] = symbol

                # Calculate standard indicators
                df = self.calculate_indicators(df)
                self.cached_candles[symbol] = df
                return df
        except Exception as e:
            logger.warning(f"⚠️ [MARKET_FEED] Exchange fetch_ohlcv error for {symbol} ({tf}): {e}")

        if symbol in self.cached_candles:
            return self.cached_candles[symbol]

        # Generate synthetic fallback DF if completely offline
        logger.warning(f"🚨 [DATA TRANSPARENCY WARNING] Falling back to synthetic model OHLCV generation for {symbol} because exchange connection is offline.")
        return self._generate_fallback_df(symbol)

    async def async_fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Non-blocking async wrapper around fetch_ticker."""
        return await asyncio.to_thread(self.fetch_ticker, symbol)

    async def async_fetch_ohlcv_dataframe(self, symbol: str, timeframe: Optional[str] = None) -> pd.DataFrame:
        """Non-blocking async wrapper around fetch_ohlcv_dataframe."""
        return await asyncio.to_thread(self.fetch_ohlcv_dataframe, symbol, timeframe)

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Appends technical indicators: EMAs, RSI, Bollinger Bands, ATR, ADX, SuperTrend, Volume SMA."""
        if len(df) < 20:
            return df

        # EMAs
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=min(len(df), 200), adjust=False).mean()

        # RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)

        # Bollinger Bands (20, 2)
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_pct_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']).replace(0, np.nan)

        # ATR (14)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean().fillna(true_range.mean())

        # Donchian Channels (20)
        df['donchian_high'] = df['high'].rolling(window=20).max()
        df['donchian_low'] = df['low'].rolling(window=20).min()
        df['donchian_mid'] = (df['donchian_high'] + df['donchian_low']) / 2

        # Volume Profile & Surge
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_surge_ratio'] = df['volume'] / df['volume_sma_20'].replace(0, np.nan)

        # ADX Approximation (14)
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
        tr = true_range.replace(0, np.nan)
        plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / tr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / tr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
        df['adx'] = dx.rolling(14).mean().fillna(20)

        # Stochastic Oscillator (14, 3, 3)
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14).replace(0, np.nan))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

        return df

    def _generate_fallback_df(self, symbol: str) -> pd.DataFrame:
        """Generates realistic synthetic candle data if offline."""
        np.random.seed(42)
        n = self.limit
        base_price = 150.0 if "SOL" in symbol else (3000.0 if "ETH" in symbol else 65000.0)
        returns = np.random.normal(0.0002, 0.005, n)
        price_series = base_price * np.cumprod(1 + returns)

        df = pd.DataFrame({
            'timestamp': [int(time.time() * 1000) - (n - i) * 900000 for i in range(n)],
            'open': price_series * (1 - 0.001 * np.random.rand(n)),
            'high': price_series * (1 + 0.004 * np.random.rand(n)),
            'low': price_series * (1 - 0.004 * np.random.rand(n)),
            'close': price_series,
            'volume': np.random.uniform(500, 5000, n)
        })
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        return self.calculate_indicators(df)
