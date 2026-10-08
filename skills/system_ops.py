import os
import sys
import json
import ctypes
import subprocess
from typing import List, Dict, Any, Callable
from core.skill import Skill

class SystemSkill(Skill):
    @property
    def name(self) -> str:
        return "system_skill"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description": "Set system master volume (0-100)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {"type": "integer", "description": "Volume level between 0 and 100"}
                        },
                        "required": ["level"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_app",
                    "description": "Launch an application or program on Windows (e.g. notepad, chrome, calc, spotify)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "Name or executable of the application to open"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lock_screen",
                    "description": "Lock the Windows workstation screen",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            "set_volume": self.set_volume,
            "open_app": self.open_app,
            "lock_screen": self.lock_screen
        }

    def set_volume(self, level: int) -> str:
        """Sets Windows master volume via PyCaw (supports both new and legacy PyCaw APIs)."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            level = max(0, min(100, int(level)))
            scalar = level / 100.0

            speakers = AudioUtilities.GetSpeakers()
            
            # New PyCaw API (EndpointVolume property)
            if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume:
                speakers.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)
                return json.dumps({"status": "success", "level": level})

            # Legacy PyCaw COM Activate API
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(scalar, None)
            return json.dumps({"status": "success", "level": level})

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def open_app(self, app_name: str) -> str:
        """Launches application or opens website on Windows."""
        import webbrowser
        import urllib.parse
        import re
        try:
            clean_name = app_name.lower().strip()

            # 1. Websites & Web Services
            websites = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "whatsapp": "https://web.whatsapp.com",
                "gmail": "https://mail.google.com",
                "github": "https://github.com",
                "chatgpt": "https://chatgpt.com",
                "instagram": "https://www.instagram.com",
                "twitter": "https://x.com",
                "x": "https://x.com",
                "reddit": "https://www.reddit.com",
                "netflix": "https://www.netflix.com",
                "spotify web": "https://open.spotify.com",
                "amazon": "https://www.amazon.in",
                "facebook": "https://www.facebook.com",
                "linkedin": "https://www.linkedin.com"
            }

            # YouTube search if query included, e.g. "youtube mr beast" or "youtube search mr beast"
            if "youtube" in clean_name and any(clean_name.startswith(p) for p in ["youtube ", "youtube search ", "search youtube "]):
                q_part = re.sub(r'^(?:youtube\s+(?:search\s+)?|search\s+youtube\s+)', '', clean_name).strip()
                if q_part:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q_part)}")
                    return json.dumps({"status": "success", "app": "youtube", "query": q_part})

            # Google search if query included
            if "google" in clean_name and any(clean_name.startswith(p) for p in ["google ", "google search ", "search google "]):
                q_part = re.sub(r'^(?:google\s+(?:search\s+)?|search\s+google\s+)', '', clean_name).strip()
                if q_part:
                    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(q_part)}")
                    return json.dumps({"status": "success", "app": "google", "query": q_part})

            if clean_name in websites:
                webbrowser.open(websites[clean_name])
                return json.dumps({"status": "success", "app": clean_name, "url": websites[clean_name]})

            if clean_name.startswith("http://") or clean_name.startswith("https://") or clean_name.endswith(".com") or clean_name.endswith(".org") or clean_name.endswith(".in"):
                url = clean_name if clean_name.startswith("http") else f"https://{clean_name}"
                webbrowser.open(url)
                return json.dumps({"status": "success", "app": clean_name, "url": url})

            # 2. Desktop Windows Applications
            alias_map = {
                "calculator": "calc.exe",
                "calc": "calc.exe",
                "browser": "start chrome || start msedge",
                "chrome": "start chrome",
                "edge": "start msedge",
                "notepad": "notepad.exe",
                "notes": "notepad.exe",
                "explorer": "explorer.exe",
                "files": "explorer.exe",
                "settings": "start ms-settings:",
                "terminal": "start wt || start cmd",
                "cmd": "start cmd",
                "powershell": "start powershell",
                "paint": "mspaint.exe",
                "task manager": "taskmgr.exe",
                "taskmgr": "taskmgr.exe",
                "control panel": "control.exe",
                "spotify": "start spotify || start https://open.spotify.com",
                "code": "code",
                "vscode": "code",
                "visual studio code": "code",
                "camera": "start microsoft.windows.camera:",
            }

            cmd = alias_map.get(clean_name, f"start {app_name}")
            subprocess.Popen(cmd, shell=True)
            return json.dumps({"status": "success", "app": app_name})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def lock_screen(self) -> str:
        """Locks the Windows computer."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return json.dumps({"status": "success", "message": "Workstation locked"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
