from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, TaskItem
from delulu.auth.deps import get_current_user

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: Optional[str] = None

class UpdateTaskStatusRequest(BaseModel):
    status: str # pending, running, completed, failed

@router.get("")
def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = db.query(TaskItem).filter(TaskItem.user_id == current_user.id).order_by(TaskItem.created_at.desc()).all()
    return [{
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "created_at": t.created_at.isoformat()
    } for t in tasks]

@router.post("")
def create_task(req: CreateTaskRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = TaskItem(
        user_id=current_user.id,
        title=req.title,
        description=req.description,
        project_id=req.project_id,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"status": "success", "id": task.id, "title": task.title}

@router.put("/{task_id}/status")
def update_status(task_id: str, req: UpdateTaskStatusRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task.status = req.status
    db.commit()
    return {"status": "success", "task_id": task.id, "new_status": task.status}

@router.delete("/{task_id}")
def delete_task(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    db.delete(task)
    db.commit()
    return {"status": "success", "message": "Task deleted."}
