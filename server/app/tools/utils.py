"""Helper functions for initializing and managing tools."""

import logging
from typing import Any, Dict, Optional

from app.tools import ToolRegistry
from app.tools.appointment_booking import AppointmentBookingTool
from app.tools.email_summary import EmailSummaryTool
from app.tools.knowledge_base import KnowledgeBaseTool
from app.tools.order_status import OrderStatusTool

logger = logging.getLogger(__name__)


def create_tool_registry(config: Dict[str, Any], session_id: Optional[str] = None) -> ToolRegistry:
    """
    Create and populate a tool registry with all available tools.

    This function makes it easy to add new tools - simply:
    1. Create a new tool class that inherits from BaseTool
    2. Import it at the top of this file
    3. Add a registry.register() call below

    Args:
        config: Configuration dictionary
        session_id: Optional session ID for tools that need it

    Returns:
        Initialized ToolRegistry with all tools registered
    """
    registry = ToolRegistry()

    # Register all available tools
    # To add a new tool, simply create the tool class and register it here
    registry.register(EmailSummaryTool(config, session_id))
    registry.register(AppointmentBookingTool(config))
    registry.register(KnowledgeBaseTool(config))
    registry.register(OrderStatusTool(config))

    logger.info("Initialized tool registry with %d tools", len(registry.get_all_tools()))
    
    return registry


def get_session_config_with_tools(registry: ToolRegistry) -> Dict[str, Any]:
    """
    Generate a session configuration with all registered tools.

    Args:
        registry: ToolRegistry containing all available tools

    Returns:
        Session configuration dictionary for Voice Live API
    """
    # Get all tool definitions from the registry
    tools = registry.get_function_definitions()
    
    # Create a dynamic instruction based on available tools
    tool_names = [tool.name for tool in registry.get_all_tools()]
    tools_description = ", ".join(tool_names)
    
    instructions = (
        "You are a helpful AI assistant for a customer service call center. "
        "You have access to the following tools to help customers: "
        f"{tools_description}. "
        "Use these tools proactively when appropriate based on the customer's needs. "
        "For example:\n"
        "- Use 'send_email_summary' when the customer wants to receive a summary or when the call is ending\n"
        "- Use 'book_appointment' when the customer wants to schedule a meeting\n"
        "- Use 'lookup_information' when asked about policies, hours, or company info\n"
        "- Use 'check_order_status' when the customer asks about their order\n"
        "Always be polite, professional, and helpful."
    )

    return {
        "type": "session.update",
        "session": {
            "instructions": instructions,
            "turn_detection": {
                "type": "azure_semantic_vad",
                "threshold": 0.3,
                "prefix_padding_ms": 200,
                "silence_duration_ms": 200,
                "remove_filler_words": False,
                "end_of_utterance_detection": {
                    "model": "semantic_detection_v1",
                    "threshold": 0.01,
                    "timeout": 2,
                },
            },
            "input_audio_noise_reduction": {"type": "azure_deep_noise_suppression"},
            "input_audio_echo_cancellation": {"type": "server_echo_cancellation"},
            "voice": {
                "name": "en-US-Aria:DragonHDLatestNeural",
                "type": "azure-standard",
                "temperature": 0.8,
            },
            "tools": tools,
            "tool_choice": "auto",
        },
    }
