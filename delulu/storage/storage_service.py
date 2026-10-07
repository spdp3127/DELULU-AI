import os
import shutil
import uuid
import zipfile
import tempfile
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from delulu.database.models import UserFile

BASE_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "users"))

class StorageService:
    def __init__(self, base_dir: str = BASE_STORAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> str:
        # Sanitize user_id to prevent directory traversal
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        user_dir = os.path.abspath(os.path.join(self.base_dir, safe_id))
        if not user_dir.startswith(self.base_dir):
            raise ValueError("Unauthorized storage path traversal attempt.")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def save_file(self, db: Session, user_id: str, filename: str, content: bytes, mime_type: str = "application/octet-stream", project_id: Optional[str] = None) -> UserFile:
        user_dir = self._get_user_dir(user_id)
        file_id = str(uuid.uuid4())
        safe_name = os.path.basename(filename)
        stored_filename = f"{file_id}_{safe_name}"
        abs_path = os.path.join(user_dir, stored_filename)

        with open(abs_path, "wb") as f:
            f.write(content)

        file_record = UserFile(
            id=file_id,
            user_id=user_id,
            project_id=project_id,
            filename=safe_name,
            file_path=abs_path,
            size_bytes=len(content),
            mime_type=mime_type
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        return file_record

    def get_file_content(self, db: Session, user_id: str, file_id: str) -> Optional[bytes]:
        record = db.query(UserFile).filter(UserFile.id == file_id, UserFile.user_id == user_id).first()
        if not record or not os.path.exists(record.file_path):
            return None
        with open(record.file_path, "rb") as f:
            return f.read()

    def delete_file(self, db: Session, user_id: str, file_id: str) -> bool:
        record = db.query(UserFile).filter(UserFile.id == file_id, UserFile.user_id == user_id).first()
        if not record:
            return False
        if os.path.exists(record.file_path):
            try:
                os.remove(record.file_path)
            except Exception:
                pass
        db.delete(record)
        db.commit()
        return True

    def export_all_user_data_zip(self, db: Session, user_id: str) -> str:
        """Packages all files belonging to user into a private zip archive for Data Export."""
        user_dir = self._get_user_dir(user_id)
        temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp_zip.close()

        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files = db.query(UserFile).filter(UserFile.user_id == user_id).all()
            for uf in files:
                if os.path.exists(uf.file_path):
                    zipf.write(uf.file_path, arcname=uf.filename)
        return temp_zip.name

    def delete_all_user_storage(self, user_id: str):
        """Purges the entire user storage directory upon account deletion."""
        user_dir = self._get_user_dir(user_id)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir, ignore_errors=True)

storage_service = StorageService()
