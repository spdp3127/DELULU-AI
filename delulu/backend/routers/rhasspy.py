import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from delulu.auth.deps import get_current_user, get_db
from delulu.database.models import User
from delulu.rhasspy_engine import rhasspy_nlu, rhasspy_system_controller, rhasspy_wake_word

router = APIRouter(prefix="/api/v1/rhasspy", tags=["Rhasspy Voice & System Control"])

class NLURequest(BaseModel):
    text: str

class HotwordTriggerRequest(BaseModel):
    hotword: str = "delulu"

@router.get("/status")
def get_rhasspy_status():
    """Returns real-time status of Rhasspy NLU, System Controller, and Hermes Hotword engine."""
    return {
        "status": "online",
        "rhasspy_version": "2.5-compatible",
        "nlu_engine": "Rhasspy NLU (rhasspynlu + fuzzy)",
        "grammar_loaded": rhasspy_nlu.graph is not None,
        "wake_word_engine": "Rhasspy Hermes Hotword Engine",
        "hotwords": rhasspy_wake_word.hotwords,
        "security_mode": "Full Access",
        "intents": [
            "OpenApp",
            "ChangeVolume",
            "TakeScreenshot",
            "LockScreen",
            "SystemTelemetry",
            "GetTime",
            "GetDate",
            "CalculateMath",
            "SwitchLanguage",
            "Identity",
            "Greeting"
        ]
    }

@router.post("/nlu")
def parse_nlu(req: NLURequest):
    """
    Rhasspy Human Language Understanding (NLU).
    Parses human language utterance into structured intent and slot entities.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    intent = rhasspy_nlu.recognize(req.text)
    if not intent:
        return {
            "matched": False,
            "text": req.text,
            "intent": None,
            "slots": {},
            "confidence": 0.0
        }

    return {
        "matched": True,
        "text": req.text,
        "intent": intent.name,
        "slots": intent.slots,
        "confidence": intent.confidence
    }

@router.post("/command")
def execute_system_command(
    req: NLURequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rhasspy End-to-End System Control:
    1. Parses human language utterance with Rhasspy NLU.
    2. Executes real Windows system control action (volume, app, screenshot, lock, math, etc.).
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    intent = rhasspy_nlu.recognize(req.text)
    if not intent:
        raise HTTPException(status_code=404, detail="No matching Rhasspy system intent found for this command.")

    context = {
        "user_id": current_user.id,
        "db": db
    }

    spoken_reply, tools_run, new_lang = rhasspy_system_controller.handle_intent(
        intent, context, active_lang="English"
    )

    return {
        "success": True,
        "intent": intent.name,
        "slots": intent.slots,
        "spoken_reply": spoken_reply,
        "tools_executed": tools_run,
        "language": new_lang or "en-US"
    }

@router.post("/hotword")
def trigger_hotword_event(req: HotwordTriggerRequest):
    """
    Rhasspy Hermes Hotword Trigger:
    Simulates or receives hermes/hotword/<id>/detected event.
    """
    rhasspy_wake_word.trigger_hotword(req.hotword)
    return {
        "status": "triggered",
        "hotword": req.hotword,
        "hermes_topic": f"hermes/hotword/{req.hotword}/detected"
    }
