"""Email service for sending call summaries (Mock Implementation)."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending functionality (Mock/Simulation)."""

    def __init__(self, config: dict):
        """Initialize email service with configuration."""
        self.config = config
        logger.info("Email service initialized in MOCK mode - emails will be simulated")

    async def send_email_summary(
        self,
        to_email: str,
        subject: str,
        summary: str,
        call_id: Optional[str] = None,
    ) -> bool:
        """
        Simulate sending an email with call summary.

        This is a mock implementation that logs the email content instead of actually sending it.
        In a production environment, you would integrate with an actual email service.

        Args:
            to_email: Recipient email address
            subject: Email subject
            summary: Call summary text
            call_id: Optional call identifier

        Returns:
            bool: Always returns True to simulate successful sending
        """
        # Simulate email sending by logging the details
        logger.info("=" * 70)
        logger.info("SIMULATED EMAIL SENT")
        logger.info("=" * 70)
        logger.info("To: %s", to_email)
        logger.info("Subject: %s", subject)
        logger.info("Call ID: %s", call_id if call_id else "N/A")
        logger.info("-" * 70)
        logger.info("Summary Content:")
        logger.info("%s", summary)
        logger.info("=" * 70)

        # Always return True to simulate successful sending
        return True
