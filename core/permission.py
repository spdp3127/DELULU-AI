import os
import sys
from typing import Dict, Any, Tuple

class PermissionGuard:
    """
    Safeguard system for JARVIS: 'Access system with permission'.
    Intercepts sensitive actions (file deletion, app launches, external messaging, system shutdown)
    and requires explicit confirmation from the user.
    """

    SENSITIVE_ACTIONS = {
        "shutdown_system": "shut down or reboot the computer",
        "lock_screen": "lock the computer workstation",
        "delete_file": "delete a file from your system",
        "send_email": "send an email from your account",
        "send_whatsapp_message": "send a WhatsApp message to an external contact",
        "open_app": "launch an external application",
        "write_file": "overwrite or create a file on your system",
    }

    def __init__(self, enabled: bool = True):
        # Can be toggled via environment variable
        env_val = os.getenv("REQUIRE_PERMISSION_FOR_SENSITIVE_OPS", "true").lower()
        self.enabled = enabled and (env_val in ["true", "1", "yes"])

    def is_sensitive(self, function_name: str, args: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Returns whether a function call requires user permission and an action description."""
        if not self.enabled:
            return False, ""

        if function_name in self.SENSITIVE_ACTIONS:
            desc = self.SENSITIVE_ACTIONS[function_name]
            # Contextualize description with args if available
            if args:
                if "app_name" in args:
                    desc = f"launch '{args['app_name']}'"
                elif "filepath" in args:
                    desc = f"modify or write to '{args['filepath']}'"
                elif "recipient" in args:
                    desc = f"send an email to '{args['recipient']}'"
                elif "phone_number" in args:
                    desc = f"send a WhatsApp message to '{args['phone_number']}'"
            return True, desc

        return False, ""

    def request_permission(self, action_description: str, voice_ask_fn=None, voice_listen_fn=None) -> bool:
        """
        Prompts the user for permission.
        Supports both voice interaction and terminal input.
        """
        prompt = f"Sir, you have requested to {action_description}. May I have your authorization to proceed?"
        print(f"\n[JARVIS PERMISSION GUARD]: {prompt}")

        if voice_ask_fn and voice_listen_fn:
            try:
                voice_ask_fn(f"Sir, may I have your authorization to {action_description}?")
                print("[Listening for confirmation: 'yes'/'confirm' or 'no'/'cancel']...")
                reply = voice_listen_fn()
                if reply and any(word in reply.lower() for word in ["yes", "proceed", "confirm", "authorized", "do it", "sure"]):
                    print("[Permission GRANTED by user]")
                    return True
                else:
                    print(f"[Permission DENIED or cancelled (heard: '{reply}')]")
                    return False
            except Exception as e:
                print(f"Voice permission prompt error: {e}")

        # Fallback to text prompt
        try:
            user_choice = input("Authorize operation? (yes/no): ").strip().lower()
            return user_choice in ["yes", "y", "proceed", "confirm"]
        except Exception:
            return False
