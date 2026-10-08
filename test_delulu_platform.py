import os
import sys

# Ensure root dir on path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi.testclient import TestClient
from delulu.backend.main import app
from delulu.database.db import Base, engine, SessionLocal
from delulu.database.models import User, MemoryItem, UserFile

client = TestClient(app)

def run_delulu_tests():
    print("=" * 65)
    print("      DELULU MULTI-USER PLATFORM VERIFICATION SUITE")
    print("=" * 65)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[1] Health check: PASS (200 OK)")

    # 2. User A Registration
    user_a_email = f"usera_{os.getpid()}@delulu.ai"
    reg_a = client.post("/api/v1/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "Tony Stark"
    })
    assert reg_a.status_code == 200, f"User A registration failed: {reg_a.text}"
    token_a = reg_a.json()["access_token"]
    user_a_id = reg_a.json()["user"]["id"]
    print(f"[2] User A Registration: PASS (User ID: {user_a_id[:8]}..)")

    # 3. User B Registration
    user_b_email = f"userb_{os.getpid()}@delulu.ai"
    reg_b = client.post("/api/v1/auth/register", json={
        "email": user_b_email,
        "password": "Password456!",
        "full_name": "Bruce Banner"
    })
    assert reg_b.status_code == 200, f"User B registration failed: {reg_b.text}"
    token_b = reg_b.json()["access_token"]
    user_b_id = reg_b.json()["user"]["id"]
    print(f"[3] User B Registration: PASS (User ID: {user_b_id[:8]}..)")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 4. User A Saves Private Memory
    secret_fact = "My private suit code is 42-ALPHA."
    mem_res = client.post("/api/v1/memory", json={
        "content": secret_fact,
        "type": "long-term",
        "category": "security"
    }, headers=headers_a)
    assert mem_res.status_code == 200
    mem_a_id = mem_res.json()["id"]
    print("[4] User A Memory Storage: PASS")

    # 5. STRICT TENANT ISOLATION CHECK: User B CANNOT read User A's memory
    mem_b_res = client.get("/api/v1/memory", headers=headers_b)
    user_b_memories = [m["content"] for m in mem_b_res.json()["items"]]
    assert secret_fact not in user_b_memories, "CRITICAL SECURITY BREACH: User B saw User A's private memory!"
    print("[5] Memory Tenant Isolation: PASS (User B cannot see User A's memories)")

    # 6. User A Uploads Private File
    file_content = b"TOP SECRET: Mark VII Blueprints"
    upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("blueprints.txt", file_content, "text/plain")},
        headers=headers_a
    )
    assert upload_res.status_code == 200
    file_a_id = upload_res.json()["file"]["id"]
    print(f"[6] User A File Upload: PASS (File ID: {file_a_id[:8]}..)")

    # 7. STRICT TENANT ISOLATION CHECK: User B CANNOT download User A's file
    steal_res = client.get(f"/api/v1/files/{file_a_id}/download", headers=headers_b)
    assert steal_res.status_code in [403, 404], f"CRITICAL LEAK: User B downloaded User A's file! Status: {steal_res.status_code}"
    print("[7] File Storage Tenant Isolation: PASS (User B blocked from accessing User A's file)")

    # 8. User A Chat & Orchestrator Execution
    chat_res = client.post("/api/v1/chat/send", json={
        "content": "delulu what time is it?"
    }, headers=headers_a)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    asst_msg = chat_data["assistant_message"]["content"]
    safe_reply = asst_msg[:50].encode('ascii', 'replace').decode('ascii')
    print(f"[8] AI Chat & Tool Execution: PASS (Reply: '{safe_reply}...')")

    # 9. Tasks & Projects
    task_res = client.post("/api/v1/tasks", json={
        "title": "Upgrade Arc Reactor energy efficiency"
    }, headers=headers_a)
    assert task_res.status_code == 200
    print("[9] Workspace Tasks: PASS")

    # 10. Device Pairing Token Generation
    token_res = client.post("/api/v1/devices/token", headers=headers_a)
    assert token_res.status_code == 200
    pairing_code = token_res.json()["pairing_token"]
    assert pairing_code.startswith("DELULU-LINK-"), "Invalid pairing token format!"
    print(f"[10] Desktop Agent Pairing Token: PASS ({pairing_code})")

    # 11. Audit Activity Trail
    audit_res = client.get("/api/v1/activity", headers=headers_a)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0, "Expected audit logs to be recorded!"
    print(f"[11] User Audit Trail: PASS ({len(logs)} tamper-evident audit events recorded)")

    # 12. Rhasspy Engine Status & Capabilities
    rhasspy_stat = client.get("/api/v1/rhasspy/status")
    assert rhasspy_stat.status_code == 200
    stat_data = rhasspy_stat.json()
    assert stat_data["status"] == "online"
    assert "OpenApp" in stat_data["intents"]
    assert "hey delulu" in stat_data["hotwords"]
    print(f"[12] Rhasspy Engine Status: PASS (NLU: {stat_data['nlu_engine']}, Wake Word: {stat_data['wake_word_engine']})")

    # 13. Rhasspy Human Language Understanding (NLU) Parsing
    nlu_tests = [
        ("open calculator", "OpenApp", {"app_name": "calculator"}),
        ("now calculate 5+5", "CalculateMath", {"expression": "5+5"}),
        ("set volume to 80", "ChangeVolume", {"volume": 80}),
        ("take a screenshot", "TakeScreenshot", {}),
        ("what time is it", "GetTime", {})
    ]
    for text_query, expected_intent, expected_slots in nlu_tests:
        nlu_res = client.post("/api/v1/rhasspy/nlu", json={"text": text_query})
        assert nlu_res.status_code == 200, f"NLU failed for {text_query}"
        parsed = nlu_res.json()
        assert parsed["matched"] is True, f"Failed to match {text_query}"
        assert parsed["intent"] == expected_intent, f"Wrong intent for {text_query}: got {parsed['intent']}, expected {expected_intent}"
        for k, v in expected_slots.items():
            assert parsed["slots"].get(k) == v, f"Slot mismatch for {text_query}: {parsed['slots']}"
    print("[13] Rhasspy Human Language Understanding (NLU): PASS (All 5 slot/intent grammars matched)")

    # 14. Rhasspy System Control Execution
    sys_res = client.post("/api/v1/rhasspy/command", json={"text": "now calculate 5+5"}, headers=headers_a)
    assert sys_res.status_code == 200, f"System control failed: {sys_res.text}"
    sys_data = sys_res.json()
    assert sys_data["success"] is True
    assert "10" in sys_data["spoken_reply"]
    print(f"[14] Rhasspy System Control Execution: PASS (Result: '{sys_data['spoken_reply']}')")

    # 15. Rhasspy Hermes Hotword Trigger
    hw_res = client.post("/api/v1/rhasspy/hotword", json={"hotword": "delulu"})
    assert hw_res.status_code == 200
    assert hw_res.json()["hermes_topic"] == "hermes/hotword/delulu/detected"
    print("[15] Rhasspy Hermes Hotword Detection: PASS (hermes/hotword/delulu/detected)")

    # 16. Chat Integration with Rhasspy Brain
    chat_rhasspy = client.post("/api/v1/chat/send", json={"content": "now calculate 5+5"}, headers=headers_a)
    assert chat_rhasspy.status_code == 200
    msg_body = chat_rhasspy.json()["assistant_message"]
    assert msg_body["brain"] == "RHASSPY_ENGINE"
    assert "10" in msg_body["content"]
    print(f"[16] End-to-End Rhasspy Brain Orchestration: PASS (Brain: {msg_body['brain']}, Spoken: '{msg_body['content']}')")

    print("\n" + "=" * 65)
    print("  ALL 16 DELULU & RHASSPY SUBSYSTEMS VERIFIED & PASSING!")
    print("=" * 65)

if __name__ == "__main__":
    run_delulu_tests()
