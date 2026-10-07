# DELULU - Production-Ready Public AI Personal Assistant Platform

**DELULU** is a multi-user AI personal operating layer designed for public deployment. Each registered user receives their own private, strictly isolated AI workspace with persistent memory, file storage, multi-turn conversations, projects, tasks, skill registry, and safe computer control via a paired Windows Desktop Agent.

---

## 🌟 Architecture & Core Highlights

- **Multi-Tenant Isolation**: Strict user-ownership at Database (SQLAlchemy), Storage (`storage/users/{user_id}/`), Memory, and Tool Execution levels.
- **Enterprise Authentication**: User registration, login, JWT access & refresh tokens, password hashing (PBKDF2-SHA256), and session control.
- **Cyber Glassmorphic Public Dashboard**:
  - **Home**: Overview HUD, active tasks, storage usage, memory count, live device status.
  - **Chat**: Real-time conversational interface with streaming tool badges, voice recognition (Web Speech API), and multi-turn context.
  - **Memory**: Multi-tier personal memory (working, short-term, long-term, preferences, semantic) with privacy clear controls.
  - **Projects**: Workspace management for files, tasks, and documentation.
  - **Tasks**: Interactive task tracker for personal and AI actions.
  - **Files**: Isolated per-user file explorer with upload, download, and deletion.
  - **Skills**: Central registry cataloging 22+ active capabilities across system, files, browser, coding, and web.
  - **Desktop Agent**: Secure token pairing (`DELULU-LINK-XXXX`) for Windows machine control.
  - **Activity**: Tamper-evident user audit trail.
  - **Settings**: Custom assistant persona, voice selection, optional BYOK API keys, Data Export (GDPR ZIP), and account deletion.
- **Safe Computer Control**:
  - The public cloud server **never** executes raw OS commands on client PCs.
  - Commands are routed over authenticated, encrypted WebSockets to the user's paired local Desktop Agent with local permission validation.
- **Multi-Brain Reasoning**:
  - Server-provided Groq (`llama-3.3-70b-versatile`) + Google Gemini (`gemini-3.8-flash` / `gemini-2.5-pro`) + Local Offline Brain failover.
  - Optional user BYOK API key overrides.
- **Verification Engine**:
  - Validates execution (`verify.file`, `verify.output`, `verify.ui`) before reporting success to prevent hallucinated results.

---

## 🚀 Quick Start (Running DELULU Platform)

### 1. Launch Platform Server
Double-click [`run_delulu_platform.bat`](file:///c:/Users/Devaprayag/Desktop/jarvis/run_delulu_platform.bat) or run in terminal:
```powershell
python delulu/backend/main.py
```
Open **[http://localhost:8000](http://localhost:8000)** in any modern web browser or mobile browser!

### 2. Create Your Personal Account
1. Open [http://localhost:8000](http://localhost:8000).
2. Click **CREATE ACCOUNT** and register with your email and password.
3. Your private isolated workspace is immediately generated!

### 3. (Optional) Connect Your Windows PC
1. Navigate to the **Desktop Agent** tab in the dashboard.
2. Click **Generate Pairing Token** to get your one-time link token (e.g. `DELULU-LINK-XXXX`).
3. In a separate terminal on your PC, run:
   ```powershell
   python delulu/desktop_agent/agent.py --token YOUR_TOKEN
   ```
4. Your PC is now paired! You can ask DELULU to adjust volume, open apps, or lock your screen safely!

---

## 🧪 Automated Test Verification

Run the comprehensive multi-user platform test suite anytime:
```powershell
python test_delulu_platform.py
python test_desktop_agent.py
```
Both test suites verify:
- User A and User B registration & authentication.
- Strict multi-tenant isolation: User B cannot access User A's memories or files.
- AI chat, memory retrieval, tool execution, and audit logging.
- Desktop Agent pairing and WebSocket gateway communication.

---

## 📂 Project Directory Structure

```
delulu/
├── frontend/             # Responsive Cyber Glassmorphic SPA (HTML5/CSS3/Vanilla JS)
├── backend/              # FastAPI Application & Versioned Routers (/api/v1/...)
├── auth/                 # Password hashing, JWT tokens, tenant dependency injection
├── database/             # SQLAlchemy engine & models (Users, Memories, Files, Tasks, Logs)
├── core/                 # Multi-brain orchestrator & intent planner
├── memory/               # Personal multi-tier memory service
├── storage/              # Per-user isolated storage (/storage/users/{user_id}/)
├── permissions/          # Permission guard, risk levels, confirmation cards
├── verification/         # Action verification engine
├── desktop_agent/        # Windows Desktop Agent client & WebSocket gateway
├── skills/               # Central skill registry (22+ capabilities)
└── logs/                 # Structured audit logger
```
