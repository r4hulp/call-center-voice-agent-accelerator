"""Order status tool for checking order information."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict
import random

from app.tools import BaseTool

logger = logging.getLogger(__name__)


class OrderStatusTool(BaseTool):
    """Tool for checking order status (demo/mock implementation)."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the order status tool.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        # Mock orders database
        self.mock_orders = {
            "ORD-12345": {
                "order_id": "ORD-12345",
                "status": "shipped",
                "items": ["Product A", "Product B"],
                "total": "$149.99",
                "tracking_number": "1Z999AA10123456784",
                "estimated_delivery": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            },
            "ORD-67890": {
                "order_id": "ORD-67890",
                "status": "processing",
                "items": ["Product C"],
                "total": "$79.99",
                "tracking_number": None,
                "estimated_delivery": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
            },
        }

    @property
    def name(self) -> str:
        return "check_order_status"

    @property
    def description(self) -> str:
        return (
            "Checks the status of a customer's order. "
            "Use this when the user wants to know about their order status, tracking, or delivery information."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID or order number (e.g., ORD-12345)",
                },
                "email": {
                    "type": "string",
                    "description": "Customer's email address associated with the order (for verification)",
                },
            },
            "required": ["order_id"],
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the order status check.

        Args:
            arguments: Dictionary containing 'order_id' and optional 'email'

        Returns:
            Dictionary with order status information
        """
        order_id = arguments.get("order_id", "").upper()
        email = arguments.get("email")

        # Check if order exists
        if order_id in self.mock_orders:
            order = self.mock_orders[order_id]
            
            result = {
                "success": True,
                "order_id": order["order_id"],
                "status": order["status"],
                "items": order["items"],
                "total": order["total"],
                "estimated_delivery": order["estimated_delivery"],
            }
            
            if order["tracking_number"]:
                result["tracking_number"] = order["tracking_number"]
                result["message"] = f"Order {order_id} is {order['status']}. Tracking number: {order['tracking_number']}"
            else:
                result["message"] = f"Order {order_id} is {order['status']}. No tracking number yet."
            
            logger.info("Order status retrieved: %s", order_id)
            return result
        else:
            # Order not found - in production, you might want to search by email
            return {
                "success": False,
                "message": f"Order {order_id} not found. Please verify the order number is correct.",
                "suggestion": "Try checking your order confirmation email for the correct order number.",
            }
