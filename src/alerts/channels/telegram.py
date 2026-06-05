import os
import aiohttp
import structlog
from src.alerts.channels.base import AlertChannel

logger = structlog.get_logger()

class TelegramChannel(AlertChannel):
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("telegram_alerts_disabled", msg="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from environment.")

    async def send_alert(self, title: str, message: str) -> bool:
        if not self.enabled:
            logger.debug("telegram_alerts_disabled", msg=f"Mock Telegram Alert: [{title}] {message}")
            return True
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"🚨 *{title}*\n\n{message}",
            "parse_mode": "Markdown"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("telegram_alert_sent", title=title)
                        return True
                    else:
                        resp_text = await response.text()
                        logger.error("telegram_alert_failed", status=response.status, error=resp_text)
                        return False
        except Exception as e:
            logger.error("telegram_alert_exception", error=str(e))
            return False
