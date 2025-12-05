"""Base tool class and tool registry for Voice Live API."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all tools that can be called by the Voice Live API."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool parameters."""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given arguments.

        Args:
            arguments: Dictionary of arguments passed to the tool

        Returns:
            Dictionary containing the result of the tool execution
        """
        pass

    def to_function_definition(self) -> Dict[str, Any]:
        """
        Convert the tool to a Voice Live API function definition.

        Returns:
            Dictionary in the format expected by Voice Live API
        """
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.

        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info("Unregistered tool: %s", tool_name)

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance if found, None otherwise
        """
        return self._tools.get(tool_name)

    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.

        Returns:
            List of all registered tool instances
        """
        return list(self._tools.values())

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """
        Get function definitions for all registered tools.

        Returns:
            List of function definitions in Voice Live API format
        """
        return [tool.to_function_definition() for tool in self._tools.values()]

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Result of the tool execution

        Raises:
            ValueError: If tool is not found
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        logger.info("Executing tool: %s with arguments: %s", tool_name, arguments)
        result = await tool.execute(arguments)
        logger.info("Tool execution result: %s", result)
        return result
