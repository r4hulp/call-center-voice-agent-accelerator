"""Tests for ConnectionManager to verify concurrent call handling."""

import asyncio
import pytest

from app.handler.connection_manager import ConnectionManager, get_connection_manager


@pytest.fixture
def connection_manager():
    """Create a fresh ConnectionManager for each test."""
    return ConnectionManager()


@pytest.mark.asyncio
async def test_register_single_connection(connection_manager):
    """Test registering a single connection."""
    conn_id = "test-conn-1"
    result = await connection_manager.register_connection(conn_id, "caller1", "acs")
    
    assert result is True
    assert await connection_manager.get_active_count() == 1
    
    info = await connection_manager.get_connection_info(conn_id)
    assert info is not None
    assert info["caller_id"] == "caller1"
    assert info["connection_type"] == "acs"
    assert info["status"] == "connected"


@pytest.mark.asyncio
async def test_register_multiple_concurrent_connections(connection_manager):
    """Test registering multiple connections concurrently."""
    # Register 10 connections concurrently
    tasks = [
        connection_manager.register_connection(f"conn-{i}", f"caller-{i}", "acs")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(results)
    assert await connection_manager.get_active_count() == 10


@pytest.mark.asyncio
async def test_unregister_connection(connection_manager):
    """Test unregistering a connection."""
    conn_id = "test-conn-1"
    await connection_manager.register_connection(conn_id, "caller1", "acs")
    
    assert await connection_manager.get_active_count() == 1
    
    await connection_manager.unregister_connection(conn_id)
    
    assert await connection_manager.get_active_count() == 0
    assert await connection_manager.get_connection_info(conn_id) is None


@pytest.mark.asyncio
async def test_connection_limit_enforcement(connection_manager):
    """Test that connection limits are enforced."""
    # Set a low limit for testing
    connection_manager.set_max_connections(5)
    
    # Register 5 connections - should all succeed
    for i in range(5):
        result = await connection_manager.register_connection(f"conn-{i}", f"caller-{i}", "acs")
        assert result is True
    
    # Try to register a 6th connection - should fail
    result = await connection_manager.register_connection("conn-6", "caller-6", "acs")
    assert result is False
    assert await connection_manager.get_active_count() == 5


@pytest.mark.asyncio
async def test_concurrent_register_and_unregister(connection_manager):
    """Test concurrent registration and unregistration."""
    async def register_and_unregister(conn_id, delay):
        await connection_manager.register_connection(conn_id, f"caller-{conn_id}", "acs")
        await asyncio.sleep(delay)
        await connection_manager.unregister_connection(conn_id)
    
    # Start 20 concurrent operations with varying delays
    tasks = [
        register_and_unregister(f"conn-{i}", 0.01 * (i % 5))
        for i in range(20)
    ]
    await asyncio.gather(*tasks)
    
    # All should be unregistered
    assert await connection_manager.get_active_count() == 0


@pytest.mark.asyncio
async def test_get_all_connections(connection_manager):
    """Test retrieving all active connections."""
    # Register multiple connections
    for i in range(5):
        await connection_manager.register_connection(
            f"conn-{i}", 
            f"caller-{i}", 
            "acs" if i % 2 == 0 else "web"
        )
    
    all_conns = await connection_manager.get_all_connections()
    
    assert len(all_conns) == 5
    assert "conn-0" in all_conns
    assert all_conns["conn-0"]["caller_id"] == "caller-0"
    assert all_conns["conn-0"]["connection_type"] == "acs"
    assert all_conns["conn-1"]["connection_type"] == "web"


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that get_connection_manager returns the same instance."""
    manager1 = get_connection_manager()
    manager2 = get_connection_manager()
    
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_unregister_unknown_connection(connection_manager):
    """Test unregistering a connection that doesn't exist."""
    # Should not raise an exception
    await connection_manager.unregister_connection("non-existent")
    assert await connection_manager.get_active_count() == 0


@pytest.mark.asyncio
async def test_connection_types_tracking(connection_manager):
    """Test tracking different connection types."""
    await connection_manager.register_connection("acs-1", "caller1", "acs")
    await connection_manager.register_connection("acs-2", "caller2", "acs")
    await connection_manager.register_connection("web-1", None, "web")
    
    all_conns = await connection_manager.get_all_connections()
    
    acs_conns = [c for c in all_conns.values() if c["connection_type"] == "acs"]
    web_conns = [c for c in all_conns.values() if c["connection_type"] == "web"]
    
    assert len(acs_conns) == 2
    assert len(web_conns) == 1
