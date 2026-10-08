import os
import sys
import time
import subprocess
import threading
import urllib.request
from typing import Optional

# Ensure root directory is on python sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

def is_server_running(url: str = "http://127.0.0.1:8000/api/v1/system/telemetry") -> bool:
    try:
        r = urllib.request.urlopen(url, timeout=1.5)
        return r.status == 200
    except Exception:
        return False

def start_backend_server():
    """Starts Uvicorn server in a background daemon thread if not already active."""
    import uvicorn
    uvicorn.run("delulu.backend.main:app", host="127.0.0.1", port=8000, log_level="warning")

def get_browser_exe(browser_name: str = "chrome") -> Optional[str]:
    """Finds path to Chrome or Edge executable on Windows."""
    paths = []
    if browser_name == "chrome":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
    elif browser_name in ["edge", "msedge"]:
        paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]
    for p in paths:
        if os.path.isfile(p):
            return p
    return None

def launch_native_desktop_window():
    """
    Launches DELULU as a native standalone desktop app window without browser URL bars,
    tabs, or localhost text (identical to Gemini Desktop / ChatGPT Desktop).
    """
    target_url = "http://127.0.0.1:8000"

    # Wait for server to become available
    for _ in range(30):
        if is_server_running():
            break
        time.sleep(0.3)

    # 1. Primary: pywebview Native Desktop Window (powered by Edge WebView2 engine)
    try:
        import webview
        print("[DELULU Desktop] Launching Native Windows Desktop App...")
        webview.create_window(
            title="DELULU AI Assistant",
            url=target_url,
            width=1320,
            height=860,
            resizable=True,
            min_size=(960, 600),
            text_select=True,
            confirm_close=False
        )
        webview.start()
        return
    except Exception as e:
        print(f"[DELULU Desktop] pywebview note: {e}. Falling back to Native App Window...")

    # 2. Secondary: Chrome / Edge Standalone App Mode (No URL bar, no localhost, no tabs)
    chrome_exe = get_browser_exe("chrome")
    edge_exe = get_browser_exe("edge")

    app_args = [f"--app={target_url}", "--window-size=1320,860", "--window-position=center"]
    if chrome_exe:
        subprocess.Popen([chrome_exe] + app_args)
        return
    elif edge_exe:
        subprocess.Popen([edge_exe] + app_args)
        return
    else:
        # Generic Windows msedge start
        subprocess.Popen(f'start msedge --app="{target_url}"', shell=True)

def main():
    print("========================================================")
    print("     DELULU - NATIVE DESKTOP AI ASSISTANT")
    print("========================================================")

    # 1. Start server if not running
    if not is_server_running():
        print("[DELULU Desktop] Starting background AI engine...")
        t = threading.Thread(target=start_backend_server, daemon=True)
        t.start()

    # 2. Launch Native Desktop Window (zero localhost URL bar, pure native UI)
    launch_native_desktop_window()

if __name__ == "__main__":
    main()
