"""Manages active WebSocket connections and tracks concurrent calls."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe connection manager for tracking active calls."""

    def __init__(self):
        self._connections: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._max_connections = 100  # Configurable limit

    async def register_connection(
        self, connection_id: str, caller_id: Optional[str] = None, connection_type: str = "acs"
    ) -> bool:
        """
        Register a new connection.
        
        Args:
            connection_id: Unique identifier for the connection
            caller_id: Optional caller identifier
            connection_type: Type of connection (acs or web)
            
        Returns:
            True if registered successfully, False if limit reached
        """
        async with self._lock:
            if len(self._connections) >= self._max_connections:
                logger.warning(
                    "Connection limit reached (%d/%d). Rejecting connection %s",
                    len(self._connections),
                    self._max_connections,
                    connection_id,
                )
                return False

            self._connections[connection_id] = {
                "caller_id": caller_id,
                "connection_type": connection_type,
                "connected_at": datetime.now(),
                "status": "connected",
            }

            logger.info(
                "Connection registered: %s (type=%s, caller=%s). Active connections: %d/%d",
                connection_id,
                connection_type,
                caller_id or "unknown",
                len(self._connections),
                self._max_connections,
            )
            return True

    async def unregister_connection(self, connection_id: str):
        """Remove a connection from tracking."""
        async with self._lock:
            if connection_id in self._connections:
                conn_info = self._connections.pop(connection_id)
                duration = (datetime.now() - conn_info["connected_at"]).total_seconds()
                logger.info(
                    "Connection unregistered: %s (duration=%.2fs). Active connections: %d/%d",
                    connection_id,
                    duration,
                    len(self._connections),
                    self._max_connections,
                )
            else:
                logger.warning(
                    "Attempted to unregister unknown connection: %s", connection_id
                )

    async def get_active_count(self) -> int:
        """Get the number of active connections."""
        async with self._lock:
            return len(self._connections)

    async def get_connection_info(self, connection_id: str) -> Optional[dict]:
        """Get information about a specific connection."""
        async with self._lock:
            return self._connections.get(connection_id)

    async def get_all_connections(self) -> Dict[str, dict]:
        """Get information about all active connections."""
        async with self._lock:
            return self._connections.copy()

    def get_max_connections(self) -> int:
        """Get the maximum number of concurrent connections."""
        return self._max_connections

    def set_max_connections(self, max_connections: int):
        """Set the maximum number of concurrent connections."""
        if max_connections > 0:
            self._max_connections = max_connections
            logger.info("Max connections set to %d", max_connections)


# Global singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
