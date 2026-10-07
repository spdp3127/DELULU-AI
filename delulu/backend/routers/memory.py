from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, MemoryItem, Profile
from delulu.auth.deps import get_current_user
from delulu.memory.memory_service import memory_service

router = APIRouter(prefix="/api/v1/memory", tags=["Personal Memory"])

class CreateMemoryRequest(BaseModel):
    content: str
    type: str = "long-term"
    category: str = "general"
    importance: float = 1.0

class ToggleMemoryRequest(BaseModel):
    enabled: bool

@router.get("")
def list_memories(query: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memories = memory_service.recall_memories(db, current_user.id, query=query or "", limit=50)
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return {
        "memory_enabled": profile.memory_enabled if profile else True,
        "items": [{
            "id": m.id,
            "type": m.type,
            "category": m.category,
            "content": m.content,
            "importance": m.importance,
            "created_at": m.created_at.isoformat()
        } for m in memories]
    }

@router.post("")
def add_memory(req: CreateMemoryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = memory_service.write_memory(
        db=db,
        user_id=current_user.id,
        content=req.content,
        memory_type=req.type,
        category=req.category,
        importance=req.importance
    )
    if not mem:
        raise HTTPException(status_code=400, detail="Memory recording is disabled in your preferences.")
    return {"status": "success", "id": mem.id, "content": mem.content}

@router.delete("/clear")
def clear_memories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory_service.clear_all_memories(db, current_user.id)
    return {"status": "success", "message": "All personal memories cleared."}

@router.delete("/{memory_id}")
def delete_memory_item(memory_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ok = memory_service.delete_memory(db, current_user.id, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory item not found.")
    return {"status": "success", "message": "Memory deleted."}

@router.post("/toggle")
def toggle_memory(req: ToggleMemoryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prof = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if prof:
        prof.memory_enabled = req.enabled
        db.commit()
    return {"status": "success", "memory_enabled": req.enabled}
