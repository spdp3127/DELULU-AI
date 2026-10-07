from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from delulu.database.db import get_db
from delulu.database.models import User
from delulu.auth.jwt_handler import decode_token

security = HTTPBearer(auto_error=False)

def get_default_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "deva", User.is_active == True).first()
    if not user:
        user = db.query(User).filter(~User.email.like("guest_%"), User.is_active == True).order_by(User.created_at.asc()).first()
    if not user:
        import uuid
        from delulu.auth.hashing import hash_password
        from delulu.database.models import Profile
        user = User(
            email="deva",
            password_hash=hash_password(uuid.uuid4().hex),
            full_name="Devaprayag"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        profile = Profile(user_id=user.id, assistant_name="DELULU")
        db.add(profile)
        db.commit()
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        return get_default_user(db)

    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return get_default_user(db)

    user_id = payload.get("sub")
    if not user_id:
        return get_default_user(db)

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        return get_default_user(db)

    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user
