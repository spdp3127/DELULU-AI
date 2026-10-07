import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from fastapi import WebSocket

class DesktopGateway:
    """
    Manages authenticated WebSocket connections from client Windows Desktop Agents.
    Routes commands from the cloud orchestrator to the user's local PC securely.
    """
    def __init__(self):
        # Maps user_id -> active WebSocket
        self.active_agents: Dict[str, WebSocket] = {}
        # Maps request_id -> Future
        self.pending_responses: Dict[str, asyncio.Future] = {}

    def register_agent(self, user_id: str, websocket: WebSocket):
        self.active_agents[user_id] = websocket
        print(f"[DesktopGateway] Agent connected for user: {user_id[:8]}..")

    def unregister_agent(self, user_id: str):
        if user_id in self.active_agents:
            del self.active_agents[user_id]
            print(f"[DesktopGateway] Agent disconnected for user: {user_id[:8]}..")

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_agents

    async def send_command_async(self, user_id: str, action: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        ws = self.active_agents.get(user_id)
        if not ws:
            return {"status": "error", "message": "Desktop agent is not currently connected."}

        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.pending_responses[request_id] = future

        msg = {
            "type": "EXECUTE_ACTION",
            "request_id": request_id,
            "action": action,
            "payload": payload
        }

        try:
            await ws.send_text(json.dumps(msg))
            # Wait for response from agent
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"status": "timeout", "message": f"Desktop agent timed out after {timeout}s."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            self.pending_responses.pop(request_id, None)

    def send_command_sync(self, user_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for thread-based callers."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task in current loop or run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(asyncio.run, self.send_command_async(user_id, action, payload)).result(timeout=12)
            else:
                return loop.run_until_complete(self.send_command_async(user_id, action, payload))
        except Exception as e:
            return {"status": "error", "message": f"Desktop bridge dispatch error: {e}"}

    def handle_agent_response(self, request_id: str, response_data: Dict[str, Any]):
        future = self.pending_responses.get(request_id)
        if future and not future.done():
            future.set_result(response_data)

desktop_gateway = DesktopGateway()
