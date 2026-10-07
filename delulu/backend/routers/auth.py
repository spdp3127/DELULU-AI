from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User, Profile
from delulu.auth.hashing import hash_password, verify_password
from delulu.auth.jwt_handler import create_access_token, create_refresh_token
from delulu.auth.deps import get_current_user, get_default_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str
    full_name: str = "User"

class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user_handle = (req.username or req.email or "").strip().lower()
    if not user_handle:
        raise HTTPException(status_code=400, detail="Username is required.")

    existing = db.query(User).filter(User.email == user_handle).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this username already exists.")

    user = User(
        email=user_handle,
        password_hash=hash_password(req.password),
        full_name=req.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize default private profile
    profile = Profile(user_id=user.id, assistant_name="DELULU")
    db.add(profile)
    db.commit()

    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.email,
            "full_name": user.full_name,
            "assistant_name": profile.assistant_name
        }
    }

@router.post("/guest", response_model=TokenResponse)
def guest_login(db: Session = Depends(get_db)):
    import uuid
    guest_tag = uuid.uuid4().hex[:6].upper()
    username = f"guest_{guest_tag.lower()}"

    user = User(
        email=username,
        password_hash=hash_password(uuid.uuid4().hex),
        full_name=f"Guest ({guest_tag})"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize private profile for guest
    profile = Profile(user_id=user.id, assistant_name="DELULU")
    db.add(profile)
    db.commit()

    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.email,
            "full_name": user.full_name,
            "assistant_name": profile.assistant_name
        }
    }

@router.post("/default", response_model=TokenResponse)
@router.get("/default", response_model=TokenResponse)
def default_login(db: Session = Depends(get_db)):
    user = get_default_user(db)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.email,
            "full_name": user.full_name,
            "assistant_name": profile.assistant_name if profile else "DELULU",
            "is_admin": user.is_admin
        }
    }

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user_handle = (req.username or req.email or "").strip().lower()
    if not user_handle:
        raise HTTPException(status_code=400, detail="Username is required.")

    user = db.query(User).filter(User.email == user_handle).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. If you don't have an account yet, please click 'CREATE ACCOUNT'."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been suspended.")

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    access_token = create_access_token({"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.email,
            "full_name": user.full_name,
            "assistant_name": profile.assistant_name if profile else "DELULU",
            "is_admin": user.is_admin
        }
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "username": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat(),
        "profile": {
            "assistant_name": profile.assistant_name if profile else "DELULU",
            "assistant_voice": profile.assistant_voice if profile else "en-GB-RyanNeural",
            "personality": profile.personality if profile else "Intelligent, loyal AI personal assistant",
            "theme": profile.theme if profile else "cyber-glass",
            "memory_enabled": profile.memory_enabled if profile else True,
            "desktop_enabled": profile.desktop_enabled if profile else True
        }
    }
