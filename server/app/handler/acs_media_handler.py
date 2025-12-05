"""Handles media streaming to Azure Voice Live API via WebSocket."""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime

from app.handler.connection_manager import get_connection_manager
from app.tools.utils import create_tool_registry, get_session_config_with_tools
from azure.identity.aio import ManagedIdentityCredential
from websockets.asyncio.client import connect as ws_connect
from websockets.typing import Data

logger = logging.getLogger(__name__)


class ConnectionLimitExceeded(Exception):
    """Raised when the maximum number of concurrent connections is reached."""
    pass


class ACSMediaHandler:
    """Manages audio streaming between client and Azure Voice Live API."""

    def __init__(self, config):
        self.endpoint = config["AZURE_VOICE_LIVE_ENDPOINT"]
        self.model = config["VOICE_LIVE_MODEL"]
        self.api_key = config["AZURE_VOICE_LIVE_API_KEY"]
        self.client_id = config["AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID"]
        self.send_queue = asyncio.Queue()
        self.ws = None
        self.send_task = None
        self.incoming_websocket = None
        self.is_raw_audio = True
        self.config = config
        self.session_id = None
        self.conversation_transcript = []
        self.call_start_time = datetime.now()
        self.tool_registry = None
        self.connection_id = self._generate_guid()  # Unique ID for this connection
        self.connection_manager = get_connection_manager()
        self.caller_id = None
        self._is_registered = False

    def _generate_guid(self):
        return str(uuid.uuid4())

    async def connect(self):
        """Connects to Azure Voice Live API via WebSocket."""
        try:
            endpoint = self.endpoint.rstrip("/")
            model = self.model.strip()
            url = f"{endpoint}/voice-live/realtime?api-version=2025-05-01-preview&model={model}"
            url = url.replace("https://", "wss://")

            headers = {"x-ms-client-request-id": self._generate_guid()}

            if self.client_id:
            # Use async context manager to auto-close the credential
                async with ManagedIdentityCredential(client_id=self.client_id) as credential:
                    token = await credential.get_token(
                        "https://cognitiveservices.azure.com/.default"
                    )
                    print(token.token)
                    headers["Authorization"] = f"Bearer {token.token}"
                    logger.info(
                        "[connection_id=%s] Connected to Voice Live API by managed identity",
                        self.connection_id
                    )
            else:
                headers["api-key"] = self.api_key

            self.ws = await ws_connect(url, additional_headers=headers)
            logger.info(
                "[connection_id=%s] Connected to Voice Live API for caller_id=%s",
                self.connection_id,
                self.caller_id or "unknown"
            )

            # Initialize tool registry
            self.tool_registry = create_tool_registry(self.config, self.session_id)
            
            # Send session configuration with tools
            session_config = get_session_config_with_tools(self.tool_registry)
            await self._send_json(session_config)
            await self._send_json({"type": "response.create"})

            asyncio.create_task(self._receiver_loop())
            self.send_task = asyncio.create_task(self._sender_loop())
        except Exception as e:
            logger.error(
                "[connection_id=%s] Failed to connect to Voice Live API: %s",
                self.connection_id,
                str(e)
            )
            await self.cleanup()
            raise

    async def init_incoming_websocket(self, socket, is_raw_audio=True, caller_id=None):
        """Sets up incoming ACS WebSocket."""
        self.incoming_websocket = socket
        self.is_raw_audio = is_raw_audio
        self.caller_id = caller_id
        
        # Register this connection
        # Connection type: "web" for browser clients (raw PCM audio), "acs" for phone calls (encoded audio)
        connection_type = "web" if is_raw_audio else "acs"
        registered = await self.connection_manager.register_connection(
            self.connection_id, caller_id, connection_type
        )
        
        if not registered:
            logger.error(
                "Failed to register connection %s - connection limit reached",
                self.connection_id
            )
            raise ConnectionLimitExceeded("Connection limit reached. Please try again later.")
        
        self._is_registered = True
        logger.info(
            "WebSocket initialized: connection_id=%s, type=%s, caller_id=%s",
            self.connection_id,
            connection_type,
            caller_id or "unknown"
        )

    async def audio_to_voicelive(self, audio_b64: str):
        """Queues audio data to be sent to Voice Live API."""
        await self.send_queue.put(
            json.dumps({"type": "input_audio_buffer.append", "audio": audio_b64})
        )

    async def _send_json(self, obj):
        """Sends a JSON object over WebSocket."""
        if self.ws:
            await self.ws.send(json.dumps(obj))

    async def _sender_loop(self):
        """Continuously sends messages from the queue to the Voice Live WebSocket."""
        try:
            while True:
                msg = await self.send_queue.get()
                if self.ws:
                    await self.ws.send(msg)
        except Exception:
            logger.exception("[VoiceLiveACSHandler] Sender loop error")

    async def _receiver_loop(self):
        """Handles incoming events from the Voice Live WebSocket."""
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")

                match event_type:
                    case "session.created":
                        session_id = event.get("session", {}).get("id")
                        self.session_id = session_id
                        logger.info("[VoiceLiveACSHandler] Session ID: %s", session_id)

                    case "input_audio_buffer.cleared":
                        logger.info("Input Audio Buffer Cleared Message")

                    case "input_audio_buffer.speech_started":
                        logger.info(
                            "Voice activity detection started at %s ms",
                            event.get("audio_start_ms"),
                        )
                        await self.stop_audio()

                    case "input_audio_buffer.speech_stopped":
                        logger.info("Speech stopped")

                    case "conversation.item.input_audio_transcription.completed":
                        transcript = event.get("transcript")
                        logger.info("User: %s", transcript)
                        self.conversation_transcript.append(
                            {"role": "user", "content": transcript}
                        )

                    case "conversation.item.input_audio_transcription.failed":
                        error_msg = event.get("error")
                        logger.warning("Transcription Error: %s", error_msg)

                    case "response.function_call_arguments.done":
                        # Handle function call completion
                        await self._handle_function_call(event)

                    case "response.done":
                        response = event.get("response", {})
                        logger.info("Response Done: Id=%s", response.get("id"))
                        if response.get("status_details"):
                            logger.info(
                                "Status Details: %s",
                                json.dumps(response["status_details"], indent=2),
                            )

                    case "response.audio_transcript.done":
                        transcript = event.get("transcript")
                        logger.info("AI: %s", transcript)
                        self.conversation_transcript.append(
                            {"role": "assistant", "content": transcript}
                        )
                        await self.send_message(
                            json.dumps({"Kind": "Transcription", "Text": transcript})
                        )

                    case "response.audio.delta":
                        delta = event.get("delta")
                        if self.is_raw_audio:
                            audio_bytes = base64.b64decode(delta)
                            await self.send_message(audio_bytes)
                        else:
                            await self.voicelive_to_acs(delta)

                    case "error":
                        logger.error("Voice Live Error: %s", event)

                    case _:
                        logger.debug(
                            "[VoiceLiveACSHandler] Other event: %s", event_type
                        )
        except Exception:
            logger.exception("[VoiceLiveACSHandler] Receiver loop error")

    async def send_message(self, message: Data):
        """Sends data back to client WebSocket."""
        try:
            await self.incoming_websocket.send(message)
        except Exception:
            logger.exception("[VoiceLiveACSHandler] Failed to send message")

    async def voicelive_to_acs(self, base64_data):
        """Converts Voice Live audio delta to ACS audio message."""
        try:
            data = {
                "Kind": "AudioData",
                "AudioData": {"Data": base64_data},
                "StopAudio": None,
            }
            await self.send_message(json.dumps(data))
        except Exception:
            logger.exception("[VoiceLiveACSHandler] Error in voicelive_to_acs")

    async def stop_audio(self):
        """Sends a StopAudio signal to ACS."""
        stop_audio_data = {"Kind": "StopAudio", "AudioData": None, "StopAudio": {}}
        await self.send_message(json.dumps(stop_audio_data))

    async def acs_to_voicelive(self, stream_data):
        """Processes audio from ACS and forwards to Voice Live if not silent."""
        try:
            data = json.loads(stream_data)
            if data.get("kind") == "AudioData":
                audio_data = data.get("audioData", {})
                if not audio_data.get("silent", True):
                    await self.audio_to_voicelive(audio_data.get("data"))
        except Exception:
            logger.exception("[VoiceLiveACSHandler] Error processing ACS audio")

    async def web_to_voicelive(self, audio_bytes):
        """Encodes raw audio bytes and sends to Voice Live API."""
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        await self.audio_to_voicelive(audio_b64)

    async def _handle_function_call(self, event):
        """Handles function call events from Voice Live API."""
        call_id = None
        try:
            call_id = event.get("call_id")
            name = event.get("name")
            arguments = event.get("arguments")

            logger.info(
                "Function call received: %s with arguments: %s", name, arguments
            )

            # Parse arguments if they're a string
            args = json.loads(arguments) if isinstance(arguments, str) else arguments

            # Execute the tool using the registry
            result = await self.tool_registry.execute_tool(name, args)

            # Send function call output back to Voice Live
            output_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result),
                },
            }
            await self._send_json(output_event)

            # Request a new response from the assistant
            await self._send_json({"type": "response.create"})

            logger.info("Tool %s executed successfully", name)

        except ValueError as e:
            logger.error("Tool not found: %s", str(e))
            # Send error response back to Voice Live if we have a call_id
            if call_id:
                output_event = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(
                            {"success": False, "message": f"Tool not found: {event.get('name', 'unknown')}"}
                        ),
                    },
                }
                await self._send_json(output_event)
                await self._send_json({"type": "response.create"})
        except Exception:
            logger.exception("Error handling function call")

    async def cleanup(self):
        """Clean up resources and unregister the connection."""
        try:
            # Close Voice Live WebSocket
            if self.ws:
                await self.ws.close()
                logger.info(
                    "[connection_id=%s] Voice Live WebSocket closed",
                    self.connection_id
                )

            # Cancel sender task
            if self.send_task and not self.send_task.done():
                self.send_task.cancel()
                try:
                    await self.send_task
                except asyncio.CancelledError:
                    pass

            # Unregister connection
            if self._is_registered:
                await self.connection_manager.unregister_connection(self.connection_id)
                self._is_registered = False

            logger.info(
                "[connection_id=%s] Cleanup completed for caller_id=%s",
                self.connection_id,
                self.caller_id or "unknown"
            )
        except Exception:
            logger.exception(
                "[connection_id=%s] Error during cleanup",
                self.connection_id
            )

    def is_registered(self) -> bool:
        """Check if this connection is registered with the connection manager."""
        return self._is_registered
