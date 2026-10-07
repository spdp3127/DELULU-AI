from fastapi import APIRouter, Depends
from delulu.auth.deps import get_current_user
from delulu.database.models import User
from delulu.skills.registry import skill_registry

router = APIRouter(prefix="/api/v1/skills", tags=["Skill Registry"])

@router.get("")
def list_skills(current_user: User = Depends(get_current_user)):
    items = []
    for name, sk in skill_registry.skills.items():
        items.append({
            "name": sk.name,
            "category": sk.category,
            "description": sk.description,
            "risk_level": sk.risk_level,
            "parameters": sk.parameters
        })
    return {"total": len(items), "skills": items}
