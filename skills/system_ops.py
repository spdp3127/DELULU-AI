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
        """Launches application on Windows."""
        try:
            alias_map = {
                "calculator": "calc",
                "browser": "start chrome || start msedge",
                "chrome": "start chrome",
                "edge": "start msedge",
                "notepad": "notepad",
                "explorer": "explorer",
                "files": "explorer",
                "settings": "start ms-settings:",
                "terminal": "start wt || start cmd",
                "cmd": "start cmd",
            }
            clean_name = app_name.lower().strip()
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
