import os
import sys
import json
import ctypes
import subprocess
from typing import List, Dict, Any, Callable
from core.skill import Skill

def get_browser_exe(name="chrome"):
    import os
    if name == "chrome":
        candidates = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    elif name in ["edge", "msedge"]:
        candidates = [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    return None

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
        import os
        import subprocess
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

            chrome_exe = get_browser_exe("chrome")
            edge_exe = get_browser_exe("edge")

            def _launch_url(target_url):
                if chrome_exe:
                    try:
                        subprocess.Popen([chrome_exe, target_url])
                        return
                    except Exception:
                        pass
                if edge_exe:
                    try:
                        subprocess.Popen([edge_exe, target_url])
                        return
                    except Exception:
                        pass
                try:
                    os.startfile(target_url)
                except Exception:
                    webbrowser.open(target_url)

            # YouTube search if query included, e.g. "youtube mr beast" or "youtube search mr beast"
            if "youtube" in clean_name and any(clean_name.startswith(p) for p in ["youtube ", "youtube search ", "search youtube "]):
                q_part = re.sub(r'^(?:youtube\s+(?:search\s+)?|search\s+youtube\s+)', '', clean_name).strip()
                if q_part:
                    yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q_part)}"
                    _launch_url(yt_url)
                    return json.dumps({"status": "success", "app": "youtube", "url": yt_url, "query": q_part})

            # Google search if query included
            if "google" in clean_name and any(clean_name.startswith(p) for p in ["google ", "google search ", "search google "]):
                q_part = re.sub(r'^(?:google\s+(?:search\s+)?|search\s+google\s+)', '', clean_name).strip()
                if q_part:
                    g_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q_part)}"
                    _launch_url(g_url)
                    return json.dumps({"status": "success", "app": "google", "url": g_url, "query": q_part})

            if clean_name in websites:
                w_url = websites[clean_name]
                _launch_url(w_url)
                return json.dumps({"status": "success", "app": clean_name, "url": w_url})

            if clean_name.startswith("http://") or clean_name.startswith("https://") or clean_name.endswith(".com") or clean_name.endswith(".org") or clean_name.endswith(".in"):
                url = clean_name if clean_name.startswith("http") else f"https://{clean_name}"
                _launch_url(url)
                return json.dumps({"status": "success", "app": clean_name, "url": url})

            # 2. Desktop Windows Applications
            if clean_name in ["chrome", "google chrome", "browser"]:
                if chrome_exe:
                    subprocess.Popen([chrome_exe])
                    return json.dumps({"status": "success", "app": "chrome", "url": "https://www.google.com"})
                elif edge_exe:
                    subprocess.Popen([edge_exe])
                    return json.dumps({"status": "success", "app": "edge"})
                else:
                    _launch_url("https://www.google.com")
                    return json.dumps({"status": "success", "app": "chrome", "url": "https://www.google.com"})

            if clean_name in ["edge", "msedge", "microsoft edge"]:
                if edge_exe:
                    subprocess.Popen([edge_exe])
                else:
                    subprocess.Popen("start msedge", shell=True)
                return json.dumps({"status": "success", "app": "edge"})

            if clean_name in ["calc", "calculator", "കാൽക്കുലേറ്റർ", "കൽക്കുലേറ്റർ", "कैलकुलेटर"]:
                try:
                    os.startfile("calc.exe")
                except Exception:
                    subprocess.Popen("calc.exe", shell=True)
                return json.dumps({"status": "success", "app": "calculator"})

            if clean_name in ["notepad", "notes", "note", "നോട്ട്പാഡ്", "नोटपैड"]:
                try:
                    subprocess.Popen("notepad.exe")
                except Exception:
                    os.startfile("notepad.exe")
                return json.dumps({"status": "success", "app": "notepad"})

            if clean_name in ["task manager", "taskmgr"]:
                subprocess.Popen("taskmgr.exe")
                return json.dumps({"status": "success", "app": "task manager"})

            if clean_name in ["explorer", "files", "file explorer"]:
                subprocess.Popen("explorer.exe")
                return json.dumps({"status": "success", "app": "explorer"})

            if clean_name in ["cmd", "command prompt"]:
                subprocess.Popen("start cmd", shell=True)
                return json.dumps({"status": "success", "app": "cmd"})

            if clean_name in ["powershell"]:
                subprocess.Popen("start powershell", shell=True)
                return json.dumps({"status": "success", "app": "powershell"})

            if clean_name in ["settings", "windows settings"]:
                os.startfile("ms-settings:")
                return json.dumps({"status": "success", "app": "settings"})

            if clean_name in ["camera"]:
                os.startfile("microsoft.windows.camera:")
                return json.dumps({"status": "success", "app": "camera"})

            if clean_name in ["spotify"]:
                try:
                    subprocess.Popen("start spotify", shell=True)
                except Exception:
                    _launch_url("https://open.spotify.com")
                return json.dumps({"status": "success", "app": "spotify", "url": "https://open.spotify.com"})

            # Fallback
            subprocess.Popen(f"start {app_name}", shell=True)
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
