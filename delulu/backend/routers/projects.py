from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, Project
from delulu.auth.deps import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None

@router.get("")
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projs = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()
    return [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "created_at": p.created_at.isoformat()
    } for p in projs]

@router.post("")
def create_project(req: CreateProjectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = Project(user_id=current_user.id, name=req.name, description=req.description)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"status": "success", "id": proj.id, "name": proj.name}

@router.delete("/{project_id}")
def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    db.delete(proj)
    db.commit()
    return {"status": "success", "message": "Project deleted."}
