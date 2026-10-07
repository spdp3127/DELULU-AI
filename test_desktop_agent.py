import os
import sys
import asyncio
import json

root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi.testclient import TestClient
from delulu.backend.main import app

client = TestClient(app)

def test_desktop_gateway_flow():
    print("=" * 65)
    print("      DELULU DESKTOP AGENT GATEWAY VERIFICATION")
    print("=" * 65)

    # 1. Register test user
    email = f"agent_test_{os.getpid()}@delulu.ai"
    reg = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password789!",
        "full_name": "Agent Master"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate Pairing Token
    pair_res = client.post("/api/v1/devices/token", headers=headers)
    pairing_token = pair_res.json()["pairing_token"]
    print(f"[1] Generated Pairing Token: {pairing_token}")

    # 3. Connect Desktop Agent via WebSocket
    with client.websocket_connect(f"/api/v1/devices/ws/{pairing_token}") as ws:
        print("[2] Desktop Agent WebSocket Handshake: CONNECTED")

        # 4. Check device status via REST API
        dev_res = client.get("/api/v1/devices", headers=headers)
        assert dev_res.json()["is_agent_online"] == True, "Device should show as online!"
        print("[3] Live Agent Status Query: ONLINE (PASS)")

    print("\n" + "=" * 65)
    print("  DESKTOP AGENT WEBSOCKET GATEWAY 100% OPERATIONAL!")
    print("=" * 65)

if __name__ == "__main__":
    test_desktop_gateway_flow()
