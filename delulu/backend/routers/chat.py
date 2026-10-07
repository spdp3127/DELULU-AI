from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, Conversation, Message
from delulu.auth.deps import get_current_user
from delulu.core.orchestrator import orchestrator

router = APIRouter(prefix="/api/v1/chat", tags=["AI Chat"])

class SendMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    content: str

class CreateConversationRequest(BaseModel):
    title: str = "New Session"

@router.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()} for c in convs]

@router.post("/conversations")
def create_conversation(req: CreateConversationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = Conversation(user_id=current_user.id, title=req.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()}

@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    
    msgs = db.query(Message).filter(Message.conversation_id == conversation_id, Message.user_id == current_user.id).order_by(Message.created_at.asc()).all()
    import json
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "tool_calls": json.loads(m.tool_calls) if m.tool_calls else None,
        "created_at": m.created_at.isoformat()
    } for m in msgs]

@router.post("/send")
def send_chat_message(req: SendMessageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    conv_id = req.conversation_id
    if not conv_id:
        # Create a new conversation automatically
        first_words = " ".join(req.content.strip().split()[:5])
        conv = Conversation(user_id=current_user.id, title=first_words[:40] or "New Session")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        # Verify ownership
        conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == current_user.id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    # Process through orchestrator
    result = orchestrator.process_chat(db, current_user, conv_id, req.content)
    return result

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conv)
    db.commit()
    return {"status": "success", "message": "Conversation deleted."}
