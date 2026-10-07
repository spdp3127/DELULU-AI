from typing import Dict, Any, Tuple

class PermissionGuard:
    """
    Central permission and risk evaluation engine for DELULU.
    Enforces risk classifications and generates action confirmation requirements.
    """

    SKILL_RISK_MAP = {
        # LOW Risk (Safe read-only or standard operations)
        "time.get": "LOW",
        "date.get": "LOW",
        "weather.get": "LOW",
        "web.search": "LOW",
        "memory.read": "LOW",
        "memory.search": "LOW",
        "files.list": "LOW",
        "files.read": "LOW",
        "projects.list": "LOW",
        "tasks.list": "LOW",
        "system.info": "LOW",

        # MEDIUM Risk (Non-destructive interactive actions)
        "memory.write": "MEDIUM",
        "files.upload": "MEDIUM",
        "files.create": "MEDIUM",
        "tasks.create": "MEDIUM",
        "tasks.update": "MEDIUM",
        "app.open": "MEDIUM",
        "input.mouse.click": "MEDIUM",
        "input.keyboard.type": "MEDIUM",
        "browser.open": "MEDIUM",
        "browser.search": "MEDIUM",
        "code.lint": "MEDIUM",
        "code.test": "MEDIUM",

        # HIGH Risk (State changes, file deletions, external messaging)
        "files.delete": "HIGH",
        "projects.delete": "HIGH",
        "email.send": "HIGH",
        "whatsapp.send": "HIGH",
        "app.close": "HIGH",
        "system.volume": "HIGH",
        "code.run": "HIGH",
        "code.edit": "HIGH",
        "system.lock": "HIGH",
        "automations.create": "HIGH",
        "automations.delete": "HIGH",

        # CRITICAL Risk (Irreversible or sensitive machine control)
        "system.shutdown": "CRITICAL",
        "system.reboot": "CRITICAL",
        "files.purge_all": "CRITICAL",
        "memory.clear_all": "CRITICAL",
        "account.delete": "CRITICAL",
    }

    @classmethod
    def get_risk_level(cls, skill_name: str) -> str:
        return cls.SKILL_RISK_MAP.get(skill_name, "MEDIUM")

    @classmethod
    def requires_confirmation(cls, skill_name: str, user_policy: str = "DEFAULT") -> Tuple[bool, str]:
        """
        Evaluates whether a skill call requires explicit user confirmation.
        Returns: (needs_confirmation, risk_level)
        """
        risk = cls.get_risk_level(skill_name)
        if user_policy == "ALLOW_ALL_SAFE":
            return risk in ["HIGH", "CRITICAL"], risk
        elif user_policy == "PARANOID":
            return risk != "LOW", risk
        else: # DEFAULT policy
            return risk in ["HIGH", "CRITICAL"], risk

    @classmethod
    def create_confirmation_request(cls, skill_name: str, target: str, reason: str) -> Dict[str, Any]:
        risk = cls.get_risk_level(skill_name)
        return {
            "type": "CONFIRMATION_REQUIRED",
            "action": skill_name,
            "target": target,
            "reason": reason,
            "risk_level": risk,
            "options": ["ALLOW_ONCE", "ALLOW", "DENY", "CANCEL"]
        }

permission_guard = PermissionGuard()
