import secrets
import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from delulu.database.db import get_db, SessionLocal
from delulu.database.models import User, Device
from delulu.auth.deps import get_current_user
from delulu.desktop_agent.gateway import desktop_gateway

router = APIRouter(prefix="/api/v1/devices", tags=["Desktop Agent & Devices"])

@router.get("")
def list_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.user_id == current_user.id).all()
    # Check live connection via gateway
    is_live = desktop_gateway.is_user_connected(current_user.id)
    return {
        "is_agent_online": is_live,
        "devices": [{
            "id": d.id,
            "device_name": d.device_name,
            "pairing_token": d.pairing_token,
            "status": "connected" if is_live else "disconnected",
            "last_seen": d.last_seen.isoformat()
        } for d in devices]
    }

@router.post("/token")
def generate_pairing_token(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Create or update device token
    token = f"DELULU-LINK-{secrets.token_hex(4).upper()}"
    device = db.query(Device).filter(Device.user_id == current_user.id).first()
    if not device:
        device = Device(user_id=current_user.id, device_name="Windows PC", pairing_token=token)
        db.add(device)
    else:
        device.pairing_token = token
        device.last_seen = datetime.datetime.utcnow()

    db.commit()
    db.refresh(device)
    return {
        "status": "success",
        "pairing_token": device.pairing_token,
        "instructions": f"Run on your Windows PC: python delulu/desktop_agent/agent.py --token {device.pairing_token}"
    }

@router.websocket("/ws/{pairing_token}")
async def desktop_agent_websocket(websocket: WebSocket, pairing_token: str):
    await websocket.accept()
    db = SessionLocal()
    device = None
    user_id = None
    try:
        device = db.query(Device).filter(Device.pairing_token == pairing_token).first()
        if not device:
            await websocket.send_text(json.dumps({"type": "ERROR", "message": "Invalid pairing token."}))
            await websocket.close()
            return

        user_id = device.user_id
        device.status = "connected"
        device.last_seen = datetime.datetime.utcnow()
        db.commit()

        # Register with desktop gateway
        desktop_gateway.register_agent(user_id, websocket)

        # Listen for messages / responses from desktop agent
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)
            if data.get("type") == "ACTION_RESULT":
                req_id = data.get("request_id")
                result = data.get("result", {})
                desktop_gateway.handle_agent_response(req_id, result)

    except WebSocketDisconnect:
        if user_id:
            desktop_gateway.unregister_agent(user_id)
            if device:
                device.status = "disconnected"
                device.last_seen = datetime.datetime.utcnow()
                db.commit()
    except Exception as e:
        print(f"[WebSocket Error]: {e}")
        if user_id:
            desktop_gateway.unregister_agent(user_id)
    finally:
        db.close()
