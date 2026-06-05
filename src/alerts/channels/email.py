import os
import smtplib
from email.message import EmailMessage
import structlog
import asyncio
from src.alerts.channels.base import AlertChannel

logger = structlog.get_logger()

class EmailChannel(AlertChannel):
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.to_email = os.getenv("ALERT_EMAIL_TO")
        
        self.enabled = bool(self.smtp_host and self.smtp_user and self.smtp_pass and self.to_email)
        
        if not self.enabled:
            logger.warning("email_alerts_disabled", msg="SMTP credentials missing from environment.")

    def _send_sync(self, title: str, message: str) -> bool:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = f"🚨 ALERT: {title}"
        msg['From'] = self.smtp_user
        msg['To'] = self.to_email

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error("email_alert_exception", error=str(e))
            return False

    async def send_alert(self, title: str, message: str) -> bool:
        if not self.enabled:
            logger.debug("email_alerts_disabled", msg=f"Mock Email Alert: [{title}] {message}")
            return True
            
        loop = asyncio.get_event_loop()
        # Run synchronous SMTP code in a threadpool so it doesn't block the async event loop
        result = await loop.run_in_executor(None, self._send_sync, title, message)
        if result:
            logger.info("email_alert_sent", title=title)
        return result
