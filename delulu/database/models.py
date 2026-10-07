import uuid
import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .db import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.datetime.utcnow()

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), default="User")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    
    # Optional Per-User BYOK Keys
    byok_groq_key = Column(String(255), nullable=True)
    byok_gemini_key = Column(String(255), nullable=True)
    byok_eleven_key = Column(String(255), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("MemoryItem", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    files = relationship("UserFile", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("TaskItem", back_populates="user", cascade="all, delete-orphan")
    automations = relationship("AutomationRule", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    assistant_name = Column(String(50), default="DELULU")
    assistant_voice = Column(String(50), default="en-GB-RyanNeural")
    personality = Column(String(50), default="Efficient, witty & loyal Stark AI")
    memory_enabled = Column(Boolean, default=True)
    desktop_enabled = Column(Boolean, default=True)
    theme = Column(String(20), default="cyber-glass")

    user = relationship("User", back_populates="profile")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False) # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True) # JSON array of tool calls & results
    created_at = Column(DateTime, default=utcnow)

    conversation = relationship("Conversation", back_populates="messages")

class MemoryItem(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(30), default="long-term") # working, short-term, long-term, preference, semantic, episodic
    category = Column(String(50), default="general")
    content = Column(Text, nullable=False)
    importance = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="memories")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="projects")
    files = relationship("UserFile", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("TaskItem", back_populates="project", cascade="all, delete-orphan")

class UserFile(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    size_bytes = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="files")
    project = relationship("Project", back_populates="files")

class TaskItem(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="pending") # pending, running, completed, failed
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")

class AutomationRule(Base):
    __tablename__ = "automations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    trigger_type = Column(String(50), default="schedule") # schedule, time, file, web, event
    trigger_spec = Column(String(255), nullable=False) # e.g. "every 10 minutes", "0 9 * * *"
    action_skill = Column(String(100), nullable=False) # skill name e.g. "web.research", "email.read"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="automations")

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(100), default="Windows PC")
    pairing_token = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), default="disconnected") # connected, disconnected
    last_seen = Column(DateTime, default=utcnow)
    permissions = Column(Text, default="{}") # JSON allowed desktop controls

    user = relationship("User", back_populates="devices")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    risk_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(30), default="EXECUTED") # AUTHORIZED, EXECUTED, BLOCKED, REJECTED
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="audit_logs")
