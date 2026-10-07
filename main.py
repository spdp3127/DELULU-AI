import os
import sys
import argparse
import threading 
import time
from dotenv import load_dotenv

# Load Environment variables
load_dotenv()

from core.voice import speak, listen, get_wake_words
from core.registry import SkillRegistry
from core.engine import JarvisEngine
from gui.app import run_gui as run_gui_app

def jarvis_loop(pause_event, registry, args):
    """
    Main conversational loop for JARVIS.
    Runs in a background thread when GUI is active, or main thread in --text mode.
    """
    jarvis = JarvisEngine(registry)
    wake_words = get_wake_words()
    primary_wake = wake_words[0] if wake_words else "delulu"

    # Status Announcement
    online_msg = f"Jarvis online. Awaiting your call, Sir. Wake word is '{primary_wake}'."
    if args.text:
        print(f"\n=======================================================")
        print(f"  JARVIS AI ASSISTANT ONLINE (Text Mode)")
        print(f"  Wake Words Active: {', '.join(wake_words)}")
        print(f"  Type 'quit' or 'exit' to shut down.")
        print(f"=======================================================\n")
    else:
        speak(online_msg)

    # Direct command keywords that can trigger action even without explicit wake word prefix
    direct_commands = [
        "open", "volume", "search", "create", "write", "read", "make",
        "who", "what", "when", "where", "how", "why", "thank", "hello",
        "weather", "screenshot", "detect", "lock", "camera", "photo", "time", "date"
    ]

    while True:
        # 1. Check if paused
        if pause_event.is_set():
            time.sleep(0.4)
            continue

        # 2. Get Input
        if args.text:
            try:
                user_query = input("\nYOU: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nShutting down JARVIS...")
                break
        else:
            user_query = listen()

        # Check pause again immediately
        if pause_event.is_set():
            continue

        if not user_query or user_query == "none":
            continue

        # 3. Check Exit
        if user_query in ["quit", "exit", "shutdown", "bye jarvis", "bye delulu"]:
            print("JARVIS: Powering down. Have a pleasant day, Sir.")
            if not args.text:
                speak("Powering down. Have a pleasant day, Sir.")
            break

        # 4. Wake Word / Command Filtering
        matched_wake = any(w in user_query for w in wake_words)
        is_direct = any(cmd in user_query for cmd in direct_commands)

        if not matched_wake and not is_direct:
            print(f"[Ignored - awaiting wake word '{primary_wake}']: {user_query}")
            continue

        # Strip wake words from query
        clean_query = user_query
        for w in wake_words:
            clean_query = clean_query.replace(w, " ")
        clean_query = clean_query.strip()
        if not clean_query:
            clean_query = "hello"

        # 5. Process query through Multi-Brain Engine
        try:
            print(f"[JARVIS Thinking]: '{clean_query}'")
            response = jarvis.run_conversation(clean_query)

            if pause_event.is_set():
                continue

            if response:
                if args.text:
                    print(f"JARVIS: {response}")
                else:
                    speak(response)
        except Exception as e:
            print(f"[JARVIS Error]: {e}")
            err_msg = "An unexpected error occurred in my processing pipeline, Sir."
            if args.text:
                print(f"JARVIS: {err_msg}")
            else:
                speak(err_msg)

def main():
    parser = argparse.ArgumentParser(description="JARVIS AI Assistant (Windows Native Edition)")
    parser.add_argument("--text", action="store_true", help="Run in text mode (terminal interface, no voice mic)")
    parser.add_argument("--no-gui", action="store_true", help="Run voice assistant without PyQt HUD window")
    args = parser.parse_args()

    # Informational notice on API keys
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not groq_key and not gemini_key:
        print("\n[Notice]: No GROQ_API_KEY or GEMINI_API_KEY detected in .env.")
        print("          JARVIS is operating with Local Offline Brain fallback.")
        print("          Add your keys to .env anytime for full reasoning capabilities.\n")

    # 1. Setup Pause Event
    pause_event = threading.Event()
    context = {"pause_event": pause_event}

    # 2. Initialize Registry and Load Skills
    registry = SkillRegistry()
    skills_dir = os.path.join(os.path.dirname(__file__), "skills")
    print(f"[JARVIS Core] Loading skills from {skills_dir}...")
    registry.load_skills(skills_dir, context=context)
    print(f"[JARVIS Core] Active skills: {len(registry.skills)} loaded.")

    # 3. Execution flow
    if args.text or args.no_gui:
        # Run in console without GUI
        jarvis_loop(pause_event, registry, args)
    else:
        # Start Voice Loop in daemon thread
        worker = threading.Thread(target=jarvis_loop, args=(pause_event, registry, args), daemon=True)
        worker.start()
        # Launch PyQt6 HUD in main thread (blocks until window is closed)
        run_gui_app(pause_event)

if __name__ == "__main__":
    main()