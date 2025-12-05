"""Email service for sending call summaries."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending functionality."""

    def __init__(self, config: dict):
        """Initialize email service with configuration."""
        self.smtp_server = config.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(config.get("SMTP_PORT", "587"))
        self.smtp_username = config.get("SMTP_USERNAME", "")
        self.smtp_password = config.get("SMTP_PASSWORD", "")
        self.from_email = config.get("FROM_EMAIL", self.smtp_username)
        self.enabled = bool(self.smtp_username and self.smtp_password)

        if not self.enabled:
            logger.warning(
                "Email service is not configured. Set SMTP_USERNAME and SMTP_PASSWORD to enable."
            )

    async def send_email_summary(
        self,
        to_email: str,
        subject: str,
        summary: str,
        call_id: Optional[str] = None,
    ) -> bool:
        """
        Send an email with call summary.

        Args:
            to_email: Recipient email address
            subject: Email subject
            summary: Call summary text
            call_id: Optional call identifier

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service is not enabled. Skipping email send.")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Create plain text and HTML versions
            text_content = f"""
Call Summary

{summary}
"""
            if call_id:
                text_content += f"\nCall ID: {call_id}"

            html_content = f"""
<html>
  <head></head>
  <body>
    <h2>Call Summary</h2>
    <div style="white-space: pre-wrap;">{summary}</div>
"""
            if call_id:
                html_content += f"""
    <hr>
    <p><small>Call ID: {call_id}</small></p>
"""
            html_content += """
  </body>
</html>
"""

            # Attach both parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info("Email summary sent successfully to %s", to_email)
            return True

        except Exception as e:
            logger.exception("Failed to send email summary: %s", str(e))
            return False
