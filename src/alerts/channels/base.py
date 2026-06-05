from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger()

class AlertChannel(ABC):
    """
    Abstract base class for all notification channels.
    """
    
    @abstractmethod
    async def send_alert(self, title: str, message: str) -> bool:
        """
        Sends an alert through this channel.
        Returns True if successful, False otherwise.
        """
        pass
