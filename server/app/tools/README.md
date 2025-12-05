# Voice Agent Tools

This directory contains tools that can be called by the Azure Voice Live API during customer interactions. Tools enable the voice agent to perform actions like sending emails, booking appointments, looking up information, and more.

## Available Tools

### 1. Email Summary Tool (`email_summary.py`)
Sends an email with a summary of the call conversation.
- **Use Case**: When customers request a summary or when the call is ending
- **Parameters**: 
  - `email`: Recipient's email address
  - `summary`: Concise summary of the conversation

### 2. Appointment Booking Tool (`appointment_booking.py`)
Books appointments for customers.
- **Use Case**: When customers want to schedule meetings, consultations, or services
- **Parameters**: 
  - `customer_name`: Customer's full name
  - `date`: Appointment date (YYYY-MM-DD)
  - `time`: Appointment time (HH:MM 24-hour format)
  - `service_type`: Type of service (e.g., consultation, support, demo)
  - `phone`: Customer's phone number (optional)

### 3. Knowledge Base Tool (`knowledge_base.py`)
Looks up information from the company knowledge base.
- **Use Case**: When customers ask about policies, hours, pricing, etc.
- **Parameters**: 
  - `topic`: Topic to look up (e.g., business_hours, return_policy, shipping)
  - `query`: Additional context (optional)

### 4. Order Status Tool (`order_status.py`)
Checks the status of customer orders.
- **Use Case**: When customers want order status, tracking, or delivery information
- **Parameters**: 
  - `order_id`: Order ID or order number
  - `email`: Customer's email (optional, for verification)

## How to Add a New Tool

Adding a new tool is simple and follows a consistent pattern. Follow these steps:

### Step 1: Create a New Tool Class

Create a new Python file in this directory (e.g., `my_new_tool.py`) and implement a class that inherits from `BaseTool`:

```python
"""My new tool description."""

import logging
from typing import Any, Dict

from app.tools import BaseTool

logger = logging.getLogger(__name__)


class MyNewTool(BaseTool):
    """Brief description of what this tool does."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the tool.

        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}
        # Add any initialization logic here

    @property
    def name(self) -> str:
        """Return the unique name of the tool (used by Voice Live API)."""
        return "my_new_tool"

    @property
    def description(self) -> str:
        """Return a description that helps the AI decide when to use this tool."""
        return (
            "Description of what the tool does and when to use it. "
            "Be specific about the use case."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool parameters."""
        return {
            "type": "object",
            "properties": {
                "parameter1": {
                    "type": "string",
                    "description": "Description of parameter1",
                },
                "parameter2": {
                    "type": "number",
                    "description": "Description of parameter2",
                },
            },
            "required": ["parameter1"],  # List required parameters
        }

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool logic.

        Args:
            arguments: Dictionary containing the parameters

        Returns:
            Dictionary with execution results (should include 'success' and 'message' keys)
        """
        try:
            # Extract parameters
            param1 = arguments.get("parameter1")
            param2 = arguments.get("parameter2")

            # Implement your tool logic here
            # For example: call an API, query a database, etc.
            result = self._do_something(param1, param2)

            # Return success response
            return {
                "success": True,
                "message": "Operation completed successfully",
                "data": result,
            }
        except Exception as e:
            logger.exception("Error in my_new_tool")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
            }

    def _do_something(self, param1, param2):
        """Helper method for tool logic."""
        # Implement the actual logic here
        return {"result": "example"}
```

### Step 2: Register the Tool

Edit `utils.py` in this directory and add your tool to the registry:

1. Import your tool class at the top:
```python
from app.tools.my_new_tool import MyNewTool
```

2. Register it in the `create_tool_registry` function:
```python
def create_tool_registry(config: Dict[str, Any], session_id: str = None) -> ToolRegistry:
    registry = ToolRegistry()

    # Existing tools
    registry.register(EmailSummaryTool(config, session_id))
    registry.register(AppointmentBookingTool(config))
    registry.register(KnowledgeBaseTool(config))
    registry.register(OrderStatusTool(config))
    
    # Add your new tool here
    registry.register(MyNewTool(config))

    return registry
```

### Step 3: Test Your Tool

1. Restart the server
2. The tool will automatically be available to the Voice Live API
3. Test it by having a conversation that would trigger the tool

## Tool Design Guidelines

### Best Practices

1. **Clear Descriptions**: Write clear, concise descriptions that help the AI understand when to use the tool
2. **Parameter Validation**: Always validate required parameters in the `execute` method
3. **Error Handling**: Use try-except blocks and return meaningful error messages
4. **Logging**: Log important events, errors, and execution details
5. **Return Format**: Always return a dictionary with at least `success` and `message` keys

### Return Value Format

Tools should return a dictionary with the following structure:

```python
{
    "success": True,  # or False
    "message": "Human-readable description of what happened",
    # Add any additional data as needed
    "data": {...},
    "custom_field": "..."
}
```

### Parameter Schema Format

Use JSON Schema format for parameters:

```python
{
    "type": "object",
    "properties": {
        "param_name": {
            "type": "string",  # or "number", "boolean", "array", "object"
            "description": "Clear description of the parameter",
            "enum": ["option1", "option2"],  # Optional: restrict to specific values
        }
    },
    "required": ["param1", "param2"],  # List required parameters
}
```

## Architecture

The tool system uses a registry pattern that provides:

- **Modularity**: Each tool is self-contained
- **Extensibility**: Easy to add new tools without modifying core code
- **Discoverability**: Tools automatically appear in the Voice Live API configuration
- **Type Safety**: Base class enforces consistent interface

## Configuration

Some tools may require configuration (e.g., API keys, endpoints). Pass these via the `config` parameter:

```python
# In server.py or your initialization code
config = {
    "SMTP_SERVER": "smtp.gmail.com",
    "API_KEY": "your-api-key",
    # ... other config
}

# Tools receive this config in their __init__ method
tool = MyNewTool(config)
```

## Examples

See the existing tool implementations for complete examples:
- `email_summary.py` - Integrates with external service (email)
- `appointment_booking.py` - Mock implementation showing data structure
- `knowledge_base.py` - Simple lookup with in-memory data
- `order_status.py` - Mock implementation with more complex logic

## Troubleshooting

### Tool Not Being Called

1. Check that the tool is registered in `utils.py`
2. Verify the description clearly indicates when to use the tool
3. Ensure parameters are correctly defined in the schema
4. Check server logs for any errors

### Tool Execution Errors

1. Review logs for exception details
2. Verify parameter types match the schema
3. Check that required external services are available
4. Ensure configuration is properly passed

## Future Enhancements

Potential improvements to the tool system:

- Add middleware for authentication/authorization
- Implement retry logic for failed tool calls
- Add rate limiting per tool
- Create tool execution metrics/analytics
- Support tool chaining (one tool calling another)
