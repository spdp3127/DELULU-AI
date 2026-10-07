import json
import datetime
from sqlalchemy.orm import Session
from delulu.database.models import AuditLog

class AuditLogger:
    @staticmethod
    def log(db: Session, user_id: str, action: str, target: str = None, risk_level: str = "LOW", status: str = "EXECUTED", details: Any = None):
        try:
            details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details) if details else None
            entry = AuditLog(
                user_id=user_id,
                action=action,
                target=target,
                risk_level=risk_level,
                status=status,
                details=details_str,
                timestamp=datetime.datetime.utcnow()
            )
            db.add(entry)
            db.commit()
            print(f"[AUDIT] User: {user_id[:8]}.. | Action: {action} | Risk: {risk_level} | Status: {status}")
        except Exception as e:
            print(f"[AuditLogger Error]: {e}")

audit_logger = AuditLogger()
