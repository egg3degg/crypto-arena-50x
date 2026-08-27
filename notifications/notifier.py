"""
Notification & Alerting Service
Handles real-time console table broadcasting and Telegram notifications.
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
import aiohttp

logger = logging.getLogger("CryptoArena.Notifier")

class ArenaNotifier:
    def __init__(self, telegram_token: str = "", telegram_chat_id: str = ""):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_enabled = bool(telegram_token and telegram_chat_id)

    async def notify_trade(self, bot_name: str, symbol: str, side: str, price: float,
                           quantity: float, pnl: Optional[float] = None, pnl_pct: Optional[float] = None,
                           reason: str = "SIGNAL"):
        """Sends trade alert to Telegram and logs to console."""
        emoji = "🟢" if side == "BUY" else ("🎯" if (pnl or 0) > 0 else "🛑")
        pnl_text = f"\n💵 **PnL:** `${pnl:+.2f}` (`{pnl_pct:+.2f}%`)" if pnl is not None else ""

        message = (
            f"{emoji} **[{bot_name}] {side} EXECUTED**\n"
            f"🪙 **Pair:** `{symbol}`\n"
            f"💲 **Price:** `${price:.2f}`\n"
            f"📦 **Quantity:** `{quantity:.4f}`\n"
            f"📌 **Trigger:** `{reason}`"
            f"{pnl_text}\n"
            f"⏱ _CryptoArena 50X Engine_"
        )

        logger.info(f"[{bot_name}] {side} {quantity:.4f} {symbol} @ ${price:.2f} | Reason: {reason} | PnL: {pnl or 0.0:+.2f}")
        await self._send_telegram(message)

    async def notify_research(self, title: str, summary: str):
        message = (
            f"🧠 **[ARENA DEEP RESEARCH]**\n"
            f"🔎 **{title}**\n\n"
            f"{summary}"
        )
        await self._send_telegram(message)

    async def notify_parameter_tuning(self, bot_name: str, param: str, old_val: Any, new_val: Any, reason: str):
        message = (
            f"⚙️ **[SELF-IMPROVEMENT]** `{bot_name}`\n"
            f"Parameter `{param}` auto-tuned:\n"
            f"• Before: `{old_val}`\n"
            f"• After: `{new_val}`\n"
            f"💡 _Reason:_ {reason}"
        )
        await self._send_telegram(message)

    async def _send_telegram(self, message: str):
        if not self.telegram_enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"Telegram API responded with status {resp.status}")
        except Exception as e:
            logger.debug(f"Failed to send Telegram notification: {e}")
