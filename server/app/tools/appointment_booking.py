"""Appointment booking tool for scheduling appointments."""

import logging
from datetime import datetime
from typing import Any, Dict

from app.tools import BaseTool

logger = logging.getLogger(__name__)


class AppointmentBookingTool(BaseTool):
    """Tool for booking appointments (demo/mock implementation)."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the appointment booking tool.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        # In a real implementation, this would connect to a calendar service
        self.booked_appointments = []

    @property
    def name(self) -> str:
        return "book_appointment"

    @property
    def description(self) -> str:
        return (
            "Books an appointment for the customer. "
            "Use this when the user wants to schedule a meeting, consultation, or service."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "The customer's full name",
                },
                "date": {
                    "type": "string",
                    "description": "Appointment date in YYYY-MM-DD format",
                },
                "time": {
                    "type": "string",
                    "description": "Appointment time in HH:MM format (24-hour)",
                },
                "service_type": {
                    "type": "string",
                    "description": "Type of service or meeting (e.g., consultation, support, demo)",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer's phone number",
                },
            },
            "required": ["customer_name", "date", "time", "service_type"],
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the appointment booking tool.

        Args:
            arguments: Dictionary containing appointment details

        Returns:
            Dictionary with booking confirmation
        """
        customer_name = arguments.get("customer_name")
        date = arguments.get("date")
        time = arguments.get("time")
        service_type = arguments.get("service_type")
        phone = arguments.get("phone", "Not provided")

        # Validate required fields
        if not all([customer_name, date, time, service_type]):
            return {
                "success": False,
                "message": "Missing required fields for appointment booking",
            }

        # Validate date format
        try:
            appointment_date = datetime.strptime(date, "%Y-%m-%d")
            appointment_time = datetime.strptime(time, "%H:%M")
        except ValueError:
            return {
                "success": False,
                "message": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time.",
            }

        # Mock booking (in real implementation, this would connect to a calendar API)
        appointment_id = f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        appointment = {
            "appointment_id": appointment_id,
            "customer_name": customer_name,
            "date": date,
            "time": time,
            "service_type": service_type,
            "phone": phone,
            "status": "confirmed",
        }
        
        self.booked_appointments.append(appointment)
        
        logger.info("Appointment booked: %s", appointment)

        return {
            "success": True,
            "message": f"Appointment successfully booked for {customer_name} on {date} at {time}",
            "appointment_id": appointment_id,
            "details": appointment,
        }
