import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(to: str, subject: str, body: str) -> None:
    """
    Send an email to the given recipient.

    """
    logger.info("=" * 60)
    logger.info("[EMAIL STUB] To:      %s", to)
    logger.info("[EMAIL STUB] Subject: %s", subject)
    logger.info("[EMAIL STUB] Body:\n%s", body)
    logger.info("=" * 60)
