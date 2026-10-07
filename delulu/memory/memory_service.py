import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from delulu.database.models import MemoryItem, Profile

class MemoryService:
    """Multi-tier personal memory service strictly isolated per user."""

    VALID_TYPES = ["working", "short-term", "long-term", "preference", "semantic", "episodic"]

    def write_memory(self, db: Session, user_id: str, content: str, memory_type: str = "long-term", category: str = "general", importance: float = 1.0) -> MemoryItem:
        # Check if user has memory enabled
        prof = db.query(Profile).filter(Profile.user_id == user_id).first()
        if prof and not prof.memory_enabled:
            return None

        m_type = memory_type if memory_type in self.VALID_TYPES else "long-term"
        mem = MemoryItem(
            user_id=user_id,
            type=m_type,
            category=category,
            content=content.strip(),
            importance=importance
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)
        return mem

    def recall_memories(self, db: Session, user_id: str, query: str = "", limit: int = 15) -> List[MemoryItem]:
        """Recalls the most relevant memories for the user's ongoing conversation context."""
        prof = db.query(Profile).filter(Profile.user_id == user_id).first()
        if prof and not prof.memory_enabled:
            return []

        q = db.query(MemoryItem).filter(MemoryItem.user_id == user_id)
        if query:
            # Simple keyword search / relevance match
            keywords = [w.lower() for w in query.split() if len(w) > 3]
            if keywords:
                # Filter contains any keyword
                filters = [MemoryItem.content.ilike(f"%{kw}%") for kw in keywords]
                from sqlalchemy import or_
                q = q.filter(or_(*filters))

        memories = q.order_by(MemoryItem.importance.desc(), MemoryItem.created_at.desc()).limit(limit).all()
        return memories

    def get_preferences(self, db: Session, user_id: str) -> Dict[str, str]:
        items = db.query(MemoryItem).filter(
            MemoryItem.user_id == user_id,
            MemoryItem.type == "preference"
        ).all()
        return {item.category: item.content for item in items}

    def delete_memory(self, db: Session, user_id: str, memory_id: str) -> bool:
        item = db.query(MemoryItem).filter(MemoryItem.id == memory_id, MemoryItem.user_id == user_id).first()
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True

    def clear_all_memories(self, db: Session, user_id: str):
        db.query(MemoryItem).filter(MemoryItem.user_id == user_id).delete()
        db.commit()

memory_service = MemoryService()
