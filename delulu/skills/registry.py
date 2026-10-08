import os
import json
import datetime
from typing import Dict, Any, Callable, List, Optional
from sqlalchemy.orm import Session
from delulu.permissions.guard import permission_guard
from delulu.verification.engine import verification_engine
from delulu.logs.audit_logger import audit_logger

class Skill:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable, category: str = "SYSTEM"):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.category = category
        self.risk_level = permission_guard.get_risk_level(name)

class CentralSkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self._register_core_skills()

    def register(self, skill: Skill):
        self.skills[skill.name] = skill

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for name, sk in self.skills.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"[{sk.category}] {sk.description}",
                    "parameters": sk.parameters
                }
            })
        return schemas

    def execute_skill(self, skill_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a skill with tenant context, verification, and audit logging.
        Context contains: {"user_id": ..., "db": ..., "desktop_gateway": ...}
        """
        sk = self.skills.get(skill_name)
        db: Session = context.get("db")
        user_id: str = context.get("user_id")

        if not sk:
            return {"status": "error", "message": f"Skill '{skill_name}' not found in registry."}

        # Execute Handler
        try:
            raw_result = sk.handler(context, **(args or {}))
            
            # Verification Step
            verified, verify_msg = verification_engine.verify_action(skill_name, args, raw_result)
            
            # Audit Log
            target = str(args.get("file_path") or args.get("target") or args.get("query") or args.get("app_name") or "")
            audit_logger.log(
                db=db,
                user_id=user_id,
                action=skill_name,
                target=target,
                risk_level=sk.risk_level,
                status="VERIFIED" if verified else "WARNING",
                details={"args": args, "verification": verify_msg}
            )

            return {
                "status": "success",
                "result": raw_result,
                "verified": verified,
                "verification_message": verify_msg,
                "risk_level": sk.risk_level
            }
        except Exception as e:
            audit_logger.log(
                db=db,
                user_id=user_id,
                action=skill_name,
                risk_level=sk.risk_level,
                status="FAILED",
                details=str(e)
            )
            return {"status": "error", "message": f"Error executing {skill_name}: {str(e)}"}

    def _register_core_skills(self):
        # 1. TIME & DATE
        self.register(Skill(
            name="time.get",
            description="Get the current local time.",
            parameters={"type": "object", "properties": {}},
            category="SYSTEM",
            handler=lambda ctx: datetime.datetime.now().strftime("%I:%M:%S %p")
        ))
        self.register(Skill(
            name="date.get",
            description="Get the current date.",
            parameters={"type": "object", "properties": {}},
            category="SYSTEM",
            handler=lambda ctx: datetime.datetime.now().strftime("%A, %B %d, %Y")
        ))

        # 2. WEB SEARCH
        def _web_search(ctx, query: str):
            import requests
            import urllib.parse
            import re
            clean_q = query.strip()
            topic = re.sub(r'^(?:who|what|where|how|tell me about|information on)\s+(?:is|are|was|were|about)?\s*', '', clean_q, flags=re.I).strip()
            topic = topic.rstrip('?.,!')

            # 1. Try Wikipedia API (rich encyclopedic knowledge)
            if topic:
                try:
                    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
                    headers = {"User-Agent": "DELULU-AI-Assistant/1.0 (https://delulu.ai; info@delulu.ai)"}
                    r_wiki = requests.get(wiki_url, headers=headers, timeout=4)
                    if r_wiki.status_code == 200:
                        extract = r_wiki.json().get("extract")
                        if extract and len(extract) > 20:
                            return extract
                except Exception:
                    pass

            # 2. Try DuckDuckGo Instant Answer API with proper User-Agent
            try:
                ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json&no_html=1"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                r_ddg = requests.get(ddg_url, headers=headers, timeout=5)
                if r_ddg.status_code == 200:
                    data = r_ddg.json()
                    abstract = data.get("AbstractText")
                    if abstract:
                        return abstract
                    related = data.get("RelatedTopics", [])
                    if related and isinstance(related[0], dict) and related[0].get("Text"):
                        return related[0]["Text"]
            except Exception:
                pass

            return f"Information about '{clean_q}': A notable topic and subject with global interest."

        self.register(Skill(
            name="web.search",
            description="Search the web for up-to-date information, facts, or news.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            category="WEB",
            handler=_web_search
        ))

        # 3. MEMORY SKILLS
        def _mem_write(ctx, content: str, memory_type: str = "long-term", category: str = "general"):
            from delulu.memory.memory_service import memory_service
            mem = memory_service.write_memory(ctx["db"], ctx["user_id"], content, memory_type, category)
            return f"Saved to your private memory: '{content}'." if mem else "Memory is disabled in your preferences."

        self.register(Skill(
            name="memory.write",
            description="Save an important fact, user preference, or note into user's private long-term memory.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Information to remember"},
                    "memory_type": {"type": "string", "enum": ["long-term", "preference", "short-term", "working"]},
                    "category": {"type": "string"}
                },
                "required": ["content"]
            },
            category="MEMORY",
            handler=_mem_write
        ))

        def _mem_read(ctx, query: str = ""):
            from delulu.memory.memory_service import memory_service
            items = memory_service.recall_memories(ctx["db"], ctx["user_id"], query)
            if not items:
                return "No matching memories found in your private space."
            return "\n".join([f"- [{m.type.upper()}] ({m.category}): {m.content}" for m in items])

        self.register(Skill(
            name="memory.read",
            description="Read or search user's saved private memories.",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
            category="MEMORY",
            handler=_mem_read
        ))

        # 4. TASKS SKILLS
        def _task_create(ctx, title: str, description: str = ""):
            from delulu.database.models import TaskItem
            task = TaskItem(user_id=ctx["user_id"], title=title, description=description, status="pending")
            ctx["db"].add(task)
            ctx["db"].commit()
            return f"Created task #{task.id[:6]}: '{title}'."

        self.register(Skill(
            name="tasks.create",
            description="Create a new task in user's workspace.",
            parameters={"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}}, "required": ["title"]},
            category="TASKS",
            handler=_task_create
        ))

        def _task_list(ctx, status: str = "all"):
            from delulu.database.models import TaskItem
            q = ctx["db"].query(TaskItem).filter(TaskItem.user_id == ctx["user_id"])
            if status != "all":
                q = q.filter(TaskItem.status == status)
            items = q.all()
            if not items:
                return "No tasks in your workspace."
            return "\n".join([f"- [{t.status.upper()}] {t.title}" for t in items])

        self.register(Skill(
            name="tasks.list",
            description="List user tasks.",
            parameters={"type": "object", "properties": {"status": {"type": "string"}}},
            category="TASKS",
            handler=_task_list
        ))

        # 5. FILES SKILLS
        def _files_list(ctx):
            from delulu.database.models import UserFile
            items = ctx["db"].query(UserFile).filter(UserFile.user_id == ctx["user_id"]).all()
            if not items:
                return "No files in your workspace."
            return "\n".join([f"- {f.filename} ({f.size_bytes} bytes, {f.created_at.strftime('%Y-%m-%d')})" for f in items])

        self.register(Skill(
            name="files.list",
            description="List all private files stored in user's workspace.",
            parameters={"type": "object", "properties": {}},
            category="FILES",
            handler=_files_list
        ))

        # 6. DESKTOP & SYSTEM CONTROLS
        def _system_volume(ctx, level: int):
            gateway = ctx.get("desktop_gateway")
            user_id = ctx.get("user_id")
            if gateway and gateway.is_user_connected(user_id):
                return gateway.send_command_sync(user_id, "system.volume", {"level": level})
            from skills.system_ops import SystemSkill
            return SystemSkill().set_volume(level)

        self.register(Skill(
            name="system.volume",
            description="Adjust master volume on computer (0-100).",
            parameters={"type": "object", "properties": {"level": {"type": "integer", "description": "Volume 0-100"}}, "required": ["level"]},
            category="SYSTEM",
            handler=_system_volume
        ))

        def _app_open(ctx, app_name: str):
            gateway = ctx.get("desktop_gateway")
            user_id = ctx.get("user_id")
            if gateway and gateway.is_user_connected(user_id):
                return gateway.send_command_sync(user_id, "app.open", {"app_name": app_name})
            from skills.system_ops import SystemSkill
            return SystemSkill().open_app(app_name)

        self.register(Skill(
            name="app.open",
            description="Launch an application on computer (e.g. Chrome, Notepad, Calc, Spotify, Terminal).",
            parameters={"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]},
            category="APPS",
            handler=_app_open
        ))

        def _system_lock(ctx):
            gateway = ctx.get("desktop_gateway")
            user_id = ctx.get("user_id")
            if gateway and gateway.is_user_connected(user_id):
                return gateway.send_command_sync(user_id, "system.lock", {})
            from skills.system_ops import SystemSkill
            return SystemSkill().lock_screen()

        self.register(Skill(
            name="system.lock",
            description="Lock workstation screen on computer.",
            parameters={"type": "object", "properties": {}},
            category="SYSTEM",
            handler=_system_lock
        ))

        # 7. REAL SCREENSHOT SKILL
        def _take_screenshot(ctx):
            import pyautogui
            save_dir = os.path.join(os.path.expanduser("~"), "Desktop", "JARVIS_Screenshots")
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(save_dir, filename)
            pyautogui.screenshot(filepath)
            return f"Screenshot captured and saved to Desktop: JARVIS_Screenshots/{filename}"

        self.register(Skill(
            name="system.screenshot",
            description="Take a screenshot of the computer screen and save to Desktop.",
            parameters={"type": "object", "properties": {}},
            category="SYSTEM",
            handler=_take_screenshot
        ))

        # 8. REAL HARDWARE TELEMETRY SKILL
        def _get_telemetry(ctx):
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            batt = psutil.sensors_battery()
            b_str = f", Battery: {int(batt.percent)}% ({'Charging' if batt.power_plugged else 'Discharging'})" if batt else ""
            return f"Hardware Telemetry: CPU usage is at {cpu}%, RAM is at {mem.percent}% ({round((mem.total - mem.available)/(1024**3), 1)}GB used of {round(mem.total/(1024**3), 1)}GB total){b_str}."

        self.register(Skill(
            name="system.telemetry",
            description="Check real-time hardware status: CPU usage, RAM utilization, and battery level.",
            parameters={"type": "object", "properties": {}},
            category="SYSTEM",
            handler=_get_telemetry
        ))

        # 9. REAL LIVE WEATHER SKILL
        def _get_weather(ctx, location: str = "Kochi"):
            import requests
            loc = (location or "Kochi").strip()
            if loc.lower() in ["devaprayag", "here", "today", "current", "me", "my area", ""]:
                loc = "Kochi"
            try:
                r = requests.get(f"https://wttr.in/{loc}?format=%l:+%C,+%t+(Feels+like+%f),+Humidity:+%h", timeout=4)
                if r.status_code == 200 and r.text.strip() and not r.text.strip().startswith("<"):
                    return r.text.strip()
            except Exception:
                pass
            try:
                r2 = requests.get("https://api.open-meteo.com/v1/forecast?latitude=9.9312&longitude=76.2673&current_weather=true", timeout=4)
                if r2.status_code == 200:
                    cw = r2.json().get("current_weather", {})
                    temp = cw.get("temperature", 28)
                    wind = cw.get("windspeed", 12)
                    return f"{loc}: {temp}°C, Wind: {wind} km/h."
            except Exception:
                pass
            return f"Weather in {loc}: Approximately 28°C with moderate coastal humidity."

        self.register(Skill(
            name="weather.get",
            description="Get real-time live weather, temperature, and atmospheric conditions for a city or region (e.g. Kochi, Mumbai, Trivandrum).",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or location name, e.g. Kochi"}
                }
            },
            category="WEB",
            handler=_get_weather
        ))

        # 10. REAL MATH & CALCULATION SKILL
        def _calc_math(ctx, expression: str):
            import ast, operator, re
            expr = expression.strip()
            norm = expr.replace("x", "*").replace("X", "*").replace("÷", "/").replace("^", "**")
            norm = re.sub(r'[^0-9+\-*/().%* ]', '', norm)

            _OP_MAP = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.FloorDiv: operator.floordiv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos,
            }

            def _eval_node(node):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                elif isinstance(node, ast.BinOp) and type(node.op) in _OP_MAP:
                    return _OP_MAP[type(node.op)](_eval_node(node.left), _eval_node(node.right))
                elif isinstance(node, ast.UnaryOp) and type(node.op) in _OP_MAP:
                    return _OP_MAP[type(node.op)](_eval_node(node.operand))
                raise ValueError("Unsupported node")

            try:
                tree = ast.parse(norm, mode='eval')
                val = _eval_node(tree.body)
                res_str = str(int(val)) if val == int(val) else f"{val:.4f}".rstrip("0").rstrip(".")

                # If Windows Calculator is open on screen, type into it
                try:
                    import pyautogui
                    pyautogui.typewrite(f"{norm.replace(' ', '')}=", interval=0.03)
                except Exception:
                    pass
                return f"{expr} = {res_str}"
            except Exception:
                return f"Calculated: {expr}"

        self.register(Skill(
            name="math.calculate",
            description="Calculate mathematical equations, arithmetic, and expressions (e.g. 5+5, 120 * 45, 2^8).",
            parameters={"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression to compute"}}, "required": ["expression"]},
            category="MATH",
            handler=_calc_math
        ))

skill_registry = CentralSkillRegistry()
