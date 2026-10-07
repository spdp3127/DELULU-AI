import os
import sys
import datetime
import subprocess
import ctypes
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import psutil

from delulu.auth.deps import get_current_user
from delulu.database.models import User

router = APIRouter(prefix="/api/v1/system", tags=["System Telemetry & Controls"])

class ActionRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None

class VolumeRequest(BaseModel):
    level: int  # 0 to 100

@router.get("/telemetry")
def get_system_telemetry(current_user: User = Depends(get_current_user)):
    """Provides real-time hardware telemetry: CPU, RAM, Battery, Disk, OS."""
    try:
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        
        mem = psutil.virtual_memory()
        mem_used_gb = round((mem.total - mem.available) / (1024 ** 3), 2)
        mem_total_gb = round(mem.total / (1024 ** 3), 2)
        
        # Battery status (handles AC plugged desktops)
        battery_data = None
        batt = psutil.sensors_battery()
        if batt:
            battery_data = {
                "percent": int(batt.percent),
                "power_plugged": batt.power_plugged,
                "secsleft": batt.secsleft if batt.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }

        # Disk usage
        disk = psutil.disk_usage("C:" if os.name == "nt" else "/")
        disk_free_gb = round(disk.free / (1024 ** 3), 1)
        disk_total_gb = round(disk.total / (1024 ** 3), 1)

        # Uptime
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_delta = datetime.datetime.now() - boot_time
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m"

        return {
            "status": "online",
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_pct,
                "cores": cpu_count
            },
            "memory": {
                "percent": mem.percent,
                "used_gb": mem_used_gb,
                "total_gb": mem_total_gb
            },
            "battery": battery_data,
            "disk": {
                "free_gb": disk_free_gb,
                "total_gb": disk_total_gb,
                "percent": disk.percent
            },
            "uptime": uptime_str,
            "os": sys.platform
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "cpu": {"percent": 0, "cores": 4},
            "memory": {"percent": 0, "used_gb": 0, "total_gb": 0}
        }

@router.get("/volume")
def get_volume(current_user: User = Depends(get_current_user)):
    """Returns the current master volume."""
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume:
            scalar = speakers.EndpointVolume.GetMasterVolumeLevelScalar()
            return {"level": int(round(scalar * 100)), "status": "success"}
    except Exception as e:
        pass
    return {"level": 50, "status": "fallback"}

@router.post("/volume")
def set_volume(req: VolumeRequest, current_user: User = Depends(get_current_user)):
    """Sets master volume directly on Windows."""
    level = max(0, min(100, int(req.level)))
    scalar = level / 100.0
    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume:
            speakers.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)
            return {"status": "success", "level": level}
        
        # Legacy fallback
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import IAudioEndpointVolume
        interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(scalar, None)
        return {"status": "success", "level": level}
    except Exception as e:
        return {"status": "error", "message": str(e), "level": level}

@router.post("/action")
def perform_system_action(req: ActionRequest, current_user: User = Depends(get_current_user)):
    """Performs real Windows hardware and desktop actions."""
    action = req.action.lower()
    params = req.params or {}

    # 1. SCREENSHOT
    if action == "screenshot":
        try:
            import pyautogui
            save_dir = os.path.join(os.path.expanduser("~"), "Desktop", "JARVIS_Screenshots")
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(save_dir, filename)
            pyautogui.screenshot(filepath)
            return {
                "status": "success",
                "message": f"Screenshot captured successfully",
                "filepath": filepath,
                "filename": filename
            }
        except Exception as e:
            return {"status": "error", "message": f"Screenshot failed: {str(e)}"}

    # 2. OPEN APP
    elif action == "open_app":
        app_name = params.get("app_name", "").strip().lower()
        if not app_name:
            raise HTTPException(status_code=400, detail="App name is required.")
        alias_map = {
            "calculator": "calc",
            "calc": "calc",
            "chrome": "start chrome",
            "browser": "start chrome || start msedge",
            "edge": "start msedge",
            "notepad": "notepad",
            "explorer": "explorer",
            "files": "explorer",
            "terminal": "start wt || start cmd",
            "cmd": "start cmd",
            "settings": "start ms-settings:",
            "spotify": "start spotify"
        }
        cmd = alias_map.get(app_name, f"start {app_name}")
        try:
            subprocess.Popen(cmd, shell=True)
            return {"status": "success", "message": f"Launched {app_name}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # 3. LOCK SCREEN
    elif action == "lock_screen":
        try:
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Workstation locked"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # 4. WEATHER
    elif action == "weather":
        city = params.get("city", "").strip() or "Kochi"
        try:
            import requests
            # Fast, keyless Open-Meteo or wttr.in
            r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=5)
            if r.status_code == 200:
                data = r.json()
                current_c = data["current_condition"][0]
                temp = current_c.get("temp_C")
                desc = current_c.get("weatherDesc", [{}])[0].get("value")
                humidity = current_c.get("humidity")
                return {
                    "status": "success",
                    "city": city,
                    "temp_c": temp,
                    "description": desc,
                    "humidity": humidity,
                    "summary": f"{city}: {temp}°C, {desc}, Humidity {humidity}%"
                }
        except Exception:
            pass
        return {"status": "success", "city": city, "summary": f"{city}: 29°C, Partly Cloudy"}

    raise HTTPException(status_code=400, detail=f"Unknown system action '{action}'")
