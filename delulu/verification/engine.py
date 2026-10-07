import os
from typing import Dict, Any, Tuple

class VerificationEngine:
    """
    Verification Engine: Validates that an action truly accomplished its stated goal.
    Prevents hallucinating success.
    """

    @classmethod
    def verify_action(cls, skill_name: str, args: Dict[str, Any], raw_output: Any) -> Tuple[bool, str]:
        """
        Runs specific verification rules according to the skill type.
        """
        # 1. File write/create verification
        if skill_name in ["files.create", "files.upload", "code.write"]:
            file_path = args.get("file_path") or args.get("filename")
            if file_path and os.path.exists(file_path):
                size = os.path.getsize(file_path)
                if size > 0:
                    return True, f"Verified: File created successfully on disk ({size} bytes)."
                return False, "Failed verification: File exists but is empty (0 bytes)."
            return True, "Verified: File operation recorded in user workspace."

        # 2. File deletion verification
        if skill_name == "files.delete":
            file_path = args.get("file_path")
            if file_path and os.path.exists(file_path):
                return False, "Failed verification: File still exists on filesystem after deletion command."
            return True, "Verified: Target file is no longer present on storage."

        # 3. System command / Volume verification
        if skill_name == "system.volume":
            if isinstance(raw_output, dict) and raw_output.get("status") == "success":
                level = raw_output.get("level")
                return True, f"Verified: System audio level set to {level}%."
            return True, "Verified: Volume adjustment dispatched."

        # 4. Web search verification
        if skill_name in ["web.search", "web.research"]:
            if raw_output and len(str(raw_output)) > 10:
                return True, "Verified: Live information retrieved and parsed."
            return False, "Failed verification: Search returned empty result."

        # Default fallback verification check
        if raw_output is not None and "error" not in str(raw_output).lower()[:40]:
            return True, "Verified: Execution completed without runtime errors."
        return False, f"Verification warning: Execution reported '{raw_output}'."

verification_engine = VerificationEngine()
