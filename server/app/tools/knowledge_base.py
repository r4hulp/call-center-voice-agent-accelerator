"""Knowledge base lookup tool for retrieving information."""

import logging
from typing import Any, Dict

from app.tools import BaseTool

logger = logging.getLogger(__name__)


class KnowledgeBaseTool(BaseTool):
    """Tool for looking up information from a knowledge base."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the knowledge base tool.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        # Mock knowledge base - in real implementation, this would query a database or API
        self.knowledge_base = {
            "business_hours": "Our business hours are Monday-Friday 9am-5pm EST",
            "return_policy": "We offer a 30-day money-back guarantee on all products. Items must be in original condition.",
            "shipping": "Standard shipping takes 5-7 business days. Express shipping is available for 2-3 day delivery.",
            "support": "For technical support, email support@example.com or call 1-800-SUPPORT",
            "pricing": "Our pricing varies by plan. Basic plan starts at $9.99/month, Professional at $29.99/month, and Enterprise is custom priced.",
            "contact": "You can reach us at contact@example.com or call 1-800-CONTACT",
            "cancellation": "You can cancel your subscription anytime from your account settings. No cancellation fees apply.",
            "warranty": "All products come with a 1-year manufacturer warranty covering defects in materials and workmanship.",
        }

    @property
    def name(self) -> str:
        return "lookup_information"

    @property
    def description(self) -> str:
        return (
            "Looks up information from the company knowledge base. "
            "Use this when the user asks about business hours, policies, pricing, shipping, "
            "support, or other company information."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "The topic to look up. Examples: business_hours, return_policy, "
                        "shipping, support, pricing, contact, cancellation, warranty"
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "Additional context or specific question about the topic",
                },
            },
            "required": ["topic"],
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the knowledge base lookup.

        Args:
            arguments: Dictionary containing 'topic' and optional 'query'

        Returns:
            Dictionary with lookup results
        """
        topic = arguments.get("topic", "").lower()
        query = arguments.get("query", "")

        # Try exact match first
        if topic in self.knowledge_base:
            return {
                "success": True,
                "topic": topic,
                "information": self.knowledge_base[topic],
                "message": f"Found information about {topic}",
            }

        # Try fuzzy matching
        for key, value in self.knowledge_base.items():
            if topic in key or key in topic:
                return {
                    "success": True,
                    "topic": key,
                    "information": value,
                    "message": f"Found information about {key}",
                }

        # If no match found
        available_topics = ", ".join(self.knowledge_base.keys())
        return {
            "success": False,
            "message": f"No information found for topic: {topic}",
            "available_topics": available_topics,
        }
