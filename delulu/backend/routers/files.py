from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, UserFile
from delulu.auth.deps import get_current_user
from delulu.storage.storage_service import storage_service

router = APIRouter(prefix="/api/v1/files", tags=["Private Files"])

@router.get("")
def list_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    files = db.query(UserFile).filter(UserFile.user_id == current_user.id).order_by(UserFile.created_at.desc()).all()
    return [{
        "id": f.id,
        "filename": f.filename,
        "size_bytes": f.size_bytes,
        "mime_type": f.mime_type,
        "created_at": f.created_at.isoformat()
    } for f in files]

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024: # 50 MB limit
        raise HTTPException(status_code=400, detail="File size exceeds maximum limit of 50MB.")

    record = storage_service.save_file(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "upload.bin",
        content=content,
        mime_type=file.content_type or "application/octet-stream"
    )
    return {
        "status": "success",
        "file": {
            "id": record.id,
            "filename": record.filename,
            "size_bytes": record.size_bytes
        }
    }

@router.get("/{file_id}/download")
def download_file(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = storage_service.get_file_content(db, current_user.id, file_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found or access denied.")

    record = db.query(UserFile).filter(UserFile.id == file_id, UserFile.user_id == current_user.id).first()
    return Response(
        content=content,
        media_type=record.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'}
    )

@router.delete("/{file_id}")
def delete_file(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ok = storage_service.delete_file(db, current_user.id, file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="File not found.")
    return {"status": "success", "message": "File deleted."}
