"""Email summary tool for sending call summaries via email."""

import logging
from typing import Any, Dict

from app.services.email_service import EmailService
from app.tools import BaseTool

logger = logging.getLogger(__name__)


class EmailSummaryTool(BaseTool):
    """Tool for sending call summaries via email."""

    def __init__(self, config: Dict[str, Any], session_id: str = None):
        """
        Initialize the email summary tool.

        Args:
            config: Configuration dictionary containing email settings
            session_id: Optional session ID to include in the email
        """
        self.email_service = EmailService(config)
        self.session_id = session_id

    @property
    def name(self) -> str:
        return "send_email_summary"

    @property
    def description(self) -> str:
        return (
            "Sends an email with a summary of the call conversation. "
            "Use this when the user requests a summary or when the call is ending."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The recipient's email address",
                },
                "summary": {
                    "type": "string",
                    "description": "A concise summary of the call conversation including key points discussed",
                },
            },
            "required": ["email", "summary"],
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the email summary tool.

        Args:
            arguments: Dictionary containing 'email' and 'summary'

        Returns:
            Dictionary with success status and message
        """
        email = arguments.get("email")
        summary = arguments.get("summary")

        if not email or not summary:
            return {
                "success": False,
                "message": "Email and summary are required",
            }

        success = await self.email_service.send_email_summary(
            to_email=email,
            subject="Call Summary",
            summary=summary,
            call_id=self.session_id,
        )

        return {
            "success": success,
            "message": "Email sent successfully" if success else "Failed to send email",
        }
