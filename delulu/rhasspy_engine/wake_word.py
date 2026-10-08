import os
import re
import time
from typing import Callable, List, Optional

class RhasspyWakeWordEngine:
    """
    Rhasspy Hermes Wake Word & Hotword Detection Engine.
    Handles wake words ('delulu', 'hey delulu', 'jarvis', 'computer')
    following the Hermes protocol hotword architecture.
    """
    def __init__(self, hotwords: Optional[List[str]] = None):
        self.hotwords = hotwords or ["hey delulu", "delulu", "jarvis", "hey jarvis", "computer"]
        self.is_active = True
        self._callbacks = []

    def register_hotword_callback(self, cb: Callable[[str], None]):
        """Registers a listener for hermes/hotword/detected events."""
        self._callbacks.append(cb)

    def detect_in_text(self, transcript: str) -> Optional[dict]:
        """
        Scans incoming audio transcription for wake word triggers.
        Returns: {'hotword': matched_word, 'command': remaining_command} or None.
        """
        if not transcript:
            return None

        clean = transcript.strip().lower()
        for hw in self.hotwords:
            # Matches hotword at the beginning or standalone
            if clean.startswith(hw):
                remainder = clean[len(hw):].strip().lstrip(" ,.?!")
                return {
                    "hotword": hw,
                    "command": remainder,
                    "hermes_topic": f"hermes/hotword/{hw}/detected"
                }

        return None

    def trigger_hotword(self, hotword_id: str = "delulu"):
        """Emits hermes/hotword/<id>/detected event to all listeners."""
        for cb in self._callbacks:
            try:
                cb(hotword_id)
            except Exception as e:
                print(f"[RhasspyHotword] Callback error: {e}")

rhasspy_wake_word = RhasspyWakeWordEngine()
