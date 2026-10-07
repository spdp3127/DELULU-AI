from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, Profile
from delulu.auth.deps import get_current_user
from delulu.storage.storage_service import storage_service

router = APIRouter(prefix="/api/v1/settings", tags=["Settings & Privacy"])

class UpdateSettingsRequest(BaseModel):
    assistant_name: Optional[str] = None
    assistant_voice: Optional[str] = None
    personality: Optional[str] = None
    byok_groq_key: Optional[str] = None
    byok_gemini_key: Optional[str] = None
    byok_eleven_key: Optional[str] = None

@router.get("")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return {
        "full_name": current_user.full_name,
        "email": current_user.email,
        "assistant_name": profile.assistant_name if profile else "DELULU",
        "assistant_voice": profile.assistant_voice if profile else "en-GB-RyanNeural",
        "personality": profile.personality if profile else "Stark AI",
        "has_byok_groq": bool(current_user.byok_groq_key),
        "has_byok_gemini": bool(current_user.byok_gemini_key),
        "has_byok_eleven": bool(current_user.byok_eleven_key),
    }

@router.post("")
def update_settings(req: UpdateSettingsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile:
        if req.assistant_name:
            profile.assistant_name = req.assistant_name.strip()
        if req.assistant_voice:
            profile.assistant_voice = req.assistant_voice.strip()
        if req.personality:
            profile.personality = req.personality.strip()

    if req.byok_groq_key is not None:
        current_user.byok_groq_key = req.byok_groq_key.strip() or None
    if req.byok_gemini_key is not None:
        current_user.byok_gemini_key = req.byok_gemini_key.strip() or None
    if req.byok_eleven_key is not None:
        current_user.byok_eleven_key = req.byok_eleven_key.strip() or None

    db.commit()
    return {"status": "success", "message": "Settings updated successfully."}

@router.get("/export")
def export_user_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exports all user files and data into a downloadable archive."""
    zip_path = storage_service.export_all_user_data_zip(db, current_user.id)
    return FileResponse(zip_path, filename="delulu_user_data_export.zip", media_type="application/zip")

@router.delete("/account")
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """GDPR / Privacy right-to-be-forgotten: Purges entire user account, files, and memories."""
    user_id = current_user.id
    # Remove files on disk
    storage_service.delete_all_user_storage(user_id)
    # Cascade delete in database
    db.delete(current_user)
    db.commit()
    return {"status": "success", "message": "Your account and all associated data have been permanently deleted."}
