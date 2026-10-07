from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, AuditLog
from delulu.auth.deps import get_current_user

router = APIRouter(prefix="/api/v1/activity", tags=["Audit & Activity Logs"])

@router.get("")
def get_activity_log(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).order_by(AuditLog.timestamp.desc()).limit(100).all()
    import json
    return [{
        "id": l.id,
        "action": l.action,
        "target": l.target,
        "risk_level": l.risk_level,
        "status": l.status,
        "details": json.loads(l.details) if l.details and l.details.startswith("{") else l.details,
        "timestamp": l.timestamp.isoformat()
    } for l in logs]
