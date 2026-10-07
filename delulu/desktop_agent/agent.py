import sys
import os
import json
import time
import argparse
import subprocess
import ctypes

try:
    import websockets
    import asyncio
except ImportError:
    print("[Error]: 'websockets' library is required for the Desktop Agent.")
    print("Run: pip install websockets")
    sys.exit(1)

class DeluluDesktopAgent:
    def __init__(self, server_url: str, pairing_token: str):
        # Convert http/https server url to ws/wss
        ws_base = server_url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
        self.ws_url = f"{ws_base}/api/v1/devices/ws/{pairing_token}"
        self.pairing_token = pairing_token
        self.running = True

    def execute_local_action(self, action: str, payload: dict) -> dict:
        print(f"\n[Agent Action Received]: {action} with args {payload}")
        
        # 1. System Volume
        if action == "system.volume":
            try:
                from pycaw.pycaw import AudioUtilities
                level = max(0, min(100, int(payload.get("level", 50))))
                scalar = level / 100.0
                speakers = AudioUtilities.GetSpeakers()
                if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume:
                    speakers.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)
                    return {"status": "success", "level": level, "message": f"Volume set to {level}%"}
                return {"status": "error", "message": "Volume control endpoint unavailable"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # 2. Open Application
        elif action == "app.open":
            app_name = payload.get("app_name", "").strip()
            alias_map = {
                "calculator": "calc",
                "calc": "calc",
                "notepad": "notepad",
                "chrome": "start chrome",
                "edge": "start msedge",
                "explorer": "explorer",
                "terminal": "start cmd",
            }
            cmd = alias_map.get(app_name.lower(), f"start {app_name}")
            try:
                subprocess.Popen(cmd, shell=True)
                return {"status": "success", "app": app_name, "message": f"Launched '{app_name}'"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # 3. Lock Workstation
        elif action == "system.lock":
            try:
                ctypes.windll.user32.LockWorkStation()
                return {"status": "success", "message": "Workstation locked"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # 4. System Info
        elif action == "system.info":
            import platform
            return {
                "status": "success",
                "os": platform.system(),
                "release": platform.release(),
                "node": platform.node(),
                "processor": platform.processor()
            }

        return {"status": "error", "message": f"Unsupported desktop action: {action}"}

    async def run(self):
        print("=" * 60)
        print("       DELULU WINDOWS DESKTOP AGENT v1.0")
        print("=" * 60)
        print(f"Connecting to DELULU Cloud at: {self.ws_url}")
        print(f"Token: {self.pairing_token[:12]}...")

        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    print("\n[+] Secure WebSocket connected to DELULU Cloud!")
                    print("[+] Device is now active and ready to receive commands.")

                    while self.running:
                        msg_text = await ws.recv()
                        data = json.loads(msg_text)

                        if data.get("type") == "EXECUTE_ACTION":
                            req_id = data.get("request_id")
                            action = data.get("action")
                            payload = data.get("payload", {})

                            result = self.execute_local_action(action, payload)

                            response = {
                                "type": "ACTION_RESULT",
                                "request_id": req_id,
                                "result": result
                            }
                            await ws.send(json.dumps(response))

            except websockets.exceptions.ConnectionClosed:
                print("[-] Connection lost. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[-] Connection error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="DELULU Desktop Agent for Windows")
    parser.add_argument("--token", required=True, help="Pairing token generated in DELULU Settings")
    parser.add_argument("--server", default="http://localhost:8000", help="DELULU Cloud API server URL")
    args = parser.parse_args()

    agent = DeluluDesktopAgent(server_url=args.server, pairing_token=args.token)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n[+] Desktop Agent stopped by user.")

if __name__ == "__main__":
    main()
