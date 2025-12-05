"""Tests for ACSMediaHandler isolation in concurrent scenarios."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.handler.acs_media_handler import ACSMediaHandler


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    return {
        "AZURE_VOICE_LIVE_ENDPOINT": "https://test.endpoint.com",
        "VOICE_LIVE_MODEL": "gpt-4o-mini",
        "AZURE_VOICE_LIVE_API_KEY": "test-key",
        "AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID": "",
    }


@pytest.mark.asyncio
async def test_handler_independence(mock_config):
    """Test that multiple handlers are independent."""
    # Create two handlers
    handler1 = ACSMediaHandler(mock_config)
    handler2 = ACSMediaHandler(mock_config)
    
    # They should have different connection IDs
    assert handler1.connection_id != handler2.connection_id
    
    # They should have different queues
    assert handler1.send_queue is not handler2.send_queue
    
    # Modifying one should not affect the other
    handler1.caller_id = "caller1"
    handler2.caller_id = "caller2"
    
    assert handler1.caller_id == "caller1"
    assert handler2.caller_id == "caller2"


@pytest.mark.asyncio
async def test_multiple_handlers_track_separately(mock_config):
    """Test that multiple handlers are tracked separately in ConnectionManager."""
    handlers = []
    
    # Create multiple handlers
    for i in range(5):
        handler = ACSMediaHandler(mock_config)
        handlers.append(handler)
    
    # All should have unique connection IDs
    conn_ids = [h.connection_id for h in handlers]
    assert len(conn_ids) == len(set(conn_ids))  # All unique


@pytest.mark.asyncio
async def test_handler_session_isolation(mock_config):
    """Test that conversation transcripts are isolated per handler."""
    handler1 = ACSMediaHandler(mock_config)
    handler2 = ACSMediaHandler(mock_config)
    
    # Add different transcripts to each
    handler1.conversation_transcript.append({"role": "user", "content": "Hello from caller 1"})
    handler2.conversation_transcript.append({"role": "user", "content": "Hello from caller 2"})
    
    # Transcripts should be independent
    assert len(handler1.conversation_transcript) == 1
    assert len(handler2.conversation_transcript) == 1
    assert handler1.conversation_transcript[0]["content"] == "Hello from caller 1"
    assert handler2.conversation_transcript[0]["content"] == "Hello from caller 2"


@pytest.mark.asyncio
async def test_concurrent_handler_initialization(mock_config):
    """Test that multiple handlers can be initialized concurrently."""
    async def create_handler():
        handler = ACSMediaHandler(mock_config)
        # Simulate some initialization work
        await asyncio.sleep(0.01)
        return handler
    
    # Create 10 handlers concurrently
    tasks = [create_handler() for _ in range(10)]
    handlers = await asyncio.gather(*tasks)
    
    # All should be created successfully
    assert len(handlers) == 10
    
    # All should have unique connection IDs
    conn_ids = [h.connection_id for h in handlers]
    assert len(conn_ids) == len(set(conn_ids))


@pytest.mark.asyncio
async def test_cleanup_does_not_affect_other_handlers(mock_config):
    """Test that cleaning up one handler doesn't affect others."""
    with patch('app.handler.acs_media_handler.get_connection_manager') as mock_get_manager:
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.register_connection = AsyncMock(return_value=True)
        mock_manager.unregister_connection = AsyncMock()
        
        # Create multiple handlers
        handler1 = ACSMediaHandler(mock_config)
        handler2 = ACSMediaHandler(mock_config)
        
        # Initialize both
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        
        await handler1.init_incoming_websocket(mock_websocket1, is_raw_audio=False, caller_id="caller1")
        await handler2.init_incoming_websocket(mock_websocket2, is_raw_audio=False, caller_id="caller2")
        
        # Cleanup handler1
        handler1.ws = AsyncMock()
        handler1.send_task = None
        await handler1.cleanup()
        
        # handler1 should be cleaned up
        assert mock_manager.unregister_connection.call_count == 1
        assert mock_manager.unregister_connection.call_args[0][0] == handler1.connection_id
        
        # handler2 should still be registered
        assert handler2._is_registered is True
        assert handler2.connection_id != handler1.connection_id


@pytest.mark.asyncio
async def test_audio_queue_isolation(mock_config):
    """Test that audio queues are isolated between handlers."""
    handler1 = ACSMediaHandler(mock_config)
    handler2 = ACSMediaHandler(mock_config)
    
    # Add data to each queue
    await handler1.audio_to_voicelive("audio1")
    await handler2.audio_to_voicelive("audio2")
    
    # Queues should contain different data
    msg1 = await handler1.send_queue.get()
    msg2 = await handler2.send_queue.get()
    
    assert "audio1" in msg1
    assert "audio2" in msg2
    assert msg1 != msg2


@pytest.mark.asyncio  
async def test_handler_timestamps_are_independent(mock_config):
    """Test that call start times are independent per handler."""
    handler1 = ACSMediaHandler(mock_config)
    await asyncio.sleep(0.01)  # Small delay
    handler2 = ACSMediaHandler(mock_config)
    
    # Start times should be different
    assert handler1.call_start_time != handler2.call_start_time
    assert handler1.call_start_time < handler2.call_start_time
