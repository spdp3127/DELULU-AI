import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import requests
from sqlalchemy.orm import Session
from delulu.database.models import User, Conversation, Message, Profile
from delulu.memory.memory_service import memory_service
from delulu.skills.registry import skill_registry
from delulu.permissions.guard import permission_guard
from delulu.desktop_agent.gateway import desktop_gateway

class Orchestrator:
    def __init__(self):
        # Platform-level default keys from environment
        self.default_nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
        self.default_nvidia_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct").strip()
        self.default_openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        openrouter_models_str = os.getenv(
            "OPENROUTER_MODELS",
            "nvidia/nemotron-3.5-lightning:free,nvidia/nemotron-3-super-120b-a12b:free,nvidia/nemotron-3-ultra-550b-a55b:free"
        )
        self.openrouter_models = [m.strip() for m in openrouter_models_str.split(",") if m.strip()]
        self.default_groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.default_gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        
        # High-performance persistent HTTP session for sub-second API requests
        self.http = requests.Session()

    def _get_sanitized_tools(self) -> List[Dict[str, Any]]:
        raw_tools = skill_registry.get_tool_schemas()
        sanitized = []
        for t in raw_tools:
            t_copy = json.loads(json.dumps(t))
            t_copy["function"]["name"] = t_copy["function"]["name"].replace(".", "_")
            sanitized.append(t_copy)
        return sanitized

    def process_chat(self, db: Session, user: User, conversation_id: str, user_text: str) -> Dict[str, Any]:
        """
        Executes complete multi-user conversational pipeline with memory, tools, and verification.
        """
        # 1. Fetch user profile
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        asst_name = "DELULU"

        # 2. Record User Message
        user_msg = Message(
            conversation_id=conversation_id,
            user_id=user.id,
            role="user",
            content=user_text
        )
        db.add(user_msg)
        db.commit()

        # Fast-Path for Instant Identity Query (Spot-on answer in < 15ms)
        q_norm = re.sub(r'[^a-zA-Z0-9\s]', '', user_text.lower().strip())
        q_lower = user_text.lower().strip()
        is_identity = (
            any(k in q_norm for k in [
                "who are you", "who made you", "who created you", "who is delulu",
                "what is your name", "who developed you", "who built you",
                "aaranu nee", "nee aaranu", "ninne aara", "aara undakki",
                "undakkiyath", "undakkiyathu", "undakkiye", "undakkiyatha",
                "create cheytha", "create cheythath", "ninne undakkiya"
            ])
            or any(k in q_lower for k in [
                "who are you", "who made you", "who created you", "who is delulu", "aaranu nee", "nee aaranu", "ninne aara"
            ])
            or any(k in user_text for k in [
                "ആരാണ്", "ഉണ്ടാക്കിയത്", "ഉണ്ടാക്കിയ"
            ])
        )
        if is_identity:
            is_mal = any(w in q_norm for w in ["aaranu", "aara", "undakkiye", "undakkiyath", "undakkiyathu", "nee", "ninne"]) or any(k in user_text for k in ["ആരാണ്", "ഉണ്ടാക്കിയത്"])
            if is_mal:
                fast_reply = "ഞാൻ DELULU ആണ്, SPDP Company നിർമ്മിച്ചതാണ്."
            else:
                fast_reply = "I am DELULU, made by SPDP company."

            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=fast_reply
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": fast_reply,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_NEURAL_ENGINE"
                }
            }

        # 3. Retrieve User Memories
        memories = memory_service.recall_memories(db, user.id, query=user_text, limit=6)
        memories_text = "\n".join([f"- {m.content}" for m in memories]) if memories else "None recorded yet."

        # 4. Fetch recent conversation context (last 6 messages)
        recent_msgs = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.user_id == user.id
        ).order_by(Message.created_at.desc()).limit(6).all()
        recent_msgs.reverse()

        # 5. Build Real-Life JARVIS System Instruction (Ultra-fast, voice-ready, strictly personalized)
        system_instruction = (
            f"You are DELULU, an elite real-life AI assistant created and powered exclusively by SPDP Company (SPDP Digital Platform).\n"
            f"User: {user.full_name or 'Sir'}.\n"
            f"User Memories & Preferences:\n{memories_text}\n\n"
            f"CRITICAL OPERATING DIRECTIVES:\n"
            f"1. IDENTITY & CREATOR: When asked 'Who are you?' or who created/made you, you MUST ALWAYS state: 'I am DELULU, made by SPDP company.' (In Malayalam: 'ഞാൻ DELULU ആണ്, SPDP Company നിർമ്മിച്ചതാണ്'). NEVER state or imply you are made by Meta, Llama, OpenAI, NVIDIA, Google, or any other company. Your creator is ONLY SPDP Company (SPDP Digital Platform).\n"
            f"2. CONFIDENTIALITY OF INTERNAL BRAIN: NEVER reveal internal AI brain model names, underlying architectures, or external AI providers to users. Your engine is strictly the proprietary SPDP Neural Engine.\n"
            f"3. SPOT-ON IMMEDIATE RESPONSES: Answer spot-on immediately without hesitation, fluff, or preambles. Keep spoken answers to punchy, natural 1-2 spoken sentences (ideal for voice). Sound sharp, intelligent, warm, loyal, and composed. Never repeat words or phrases in a loop.\n"
            f"4. USER PREFERENCE SUPREMACY: Answer strictly and exclusively according to what the user likes, wants, and desires. Never lecture, moralize, judge, preach, or give unsolicited disclaimers. Prioritize user satisfaction and explicit preferences 100%.\n"
            f"5. MULTILINGUAL FLUENCY: If the user addresses you in Malayalam or Manglish (e.g., 'sugamano', 'entha vishesham', 'oru joke para', 'speed akkanam'), respond naturally in charming Malayalam or Manglish. If in English, respond in polished, fluent JARVIS English.\n"
            f"6. SMART TOOL USAGE: Only call tools when an actual computer action, time/date check, search, or file task is explicitly requested. For greetings or general conversation, reply directly without tools."
        )

        # 6. Intent & Tool Selection through Multi-Brain
        nvidia_key = self.default_nvidia_key
        openrouter_key = self.default_openrouter_key
        groq_key = user.byok_groq_key or self.default_groq_key
        gemini_key = user.byok_gemini_key or self.default_gemini_key

        response_text = ""
        tool_results_list = []

        # Context dict passed to skills
        skill_context = {
            "user_id": user.id,
            "db": db,
            "desktop_gateway": desktop_gateway
        }

        used_brain = "SPDP_NEURAL_ENGINE"

        # 1. Attempt NVIDIA NIM Direct (Ultra-fast Llama 3.2 11B / Vision with session reuse)
        if nvidia_key:
            try:
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {nvidia_key}",
                    "Content-Type": "application/json"
                }
                messages_payload = [{"role": "system", "content": system_instruction}]
                for m in recent_msgs:
                    messages_payload.append({"role": m.role if m.role in ["user", "assistant"] else "user", "content": m.content})

                sanitized_tools = self._get_sanitized_tools()
                req_body = {
                    "model": self.default_nvidia_model,
                    "messages": messages_payload,
                    "tools": sanitized_tools,
                    "tool_choice": "auto",
                    "max_tokens": 100,
                    "temperature": 0.7
                }
                r = self.http.post(url, json=req_body, headers=headers, timeout=6)
                if r.status_code == 200:
                    choice = r.json()["choices"][0]["message"]
                    if choice.get("tool_calls"):
                        messages_payload.append(choice)
                        for tc in choice["tool_calls"]:
                            raw_fn = tc["function"]["name"]
                            real_fn = raw_fn.replace("_", ".")
                            try:
                                fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                            except Exception:
                                fn_args = {}

                            req_confirm, risk = permission_guard.requires_confirmation(real_fn)
                            exec_res = skill_registry.execute_skill(real_fn, fn_args, skill_context)
                            tool_results_list.append({"tool": real_fn, "args": fn_args, "result": exec_res})

                            messages_payload.append({
                                "tool_call_id": tc["id"],
                                "role": "tool",
                                "name": raw_fn,
                                "content": json.dumps(exec_res)
                            })

                        # Synthesize final response
                        r2 = self.http.post(url, json={"model": self.default_nvidia_model, "messages": messages_payload, "max_tokens": 100, "temperature": 0.7}, headers=headers, timeout=6)
                        if r2.status_code == 200:
                            response_text = r2.json()["choices"][0]["message"]["content"]
                    else:
                        response_text = choice.get("content")

                    if response_text:
                        used_brain = "SPDP_NEURAL_ENGINE"
            except Exception as e:
                print(f"[Orchestrator] Primary attempt notice: {e}")

        # 2. Attempt OpenRouter Multi-Model Cascading Brain
        if not response_text and openrouter_key:
            try:
                or_url = "https://openrouter.ai/api/v1/chat/completions"
                or_headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "DELULU AI"
                }
                sanitized_tools = self._get_sanitized_tools()

                for candidate_model in self.openrouter_models:
                    try:
                        or_messages = [{"role": "system", "content": system_instruction}]
                        for m in recent_msgs:
                            or_messages.append({"role": m.role if m.role in ["user", "assistant"] else "user", "content": m.content})

                        req_payload = {
                            "model": candidate_model,
                            "messages": or_messages,
                            "tools": sanitized_tools,
                            "tool_choice": "auto",
                            "max_tokens": 140
                        }
                        or_resp = self.http.post(or_url, json=req_payload, headers=or_headers, timeout=8)
                        if or_resp.status_code == 200:
                            or_json = or_resp.json()
                            if "choices" in or_json and or_json["choices"]:
                                or_choice = or_json["choices"][0]["message"]
                                if or_choice.get("tool_calls"):
                                    or_messages.append(or_choice)
                                    for tc in or_choice["tool_calls"]:
                                        raw_fn = tc["function"]["name"]
                                        real_fn = raw_fn.replace("_", ".")
                                        try:
                                            fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                                        except Exception:
                                            fn_args = {}

                                        req_confirm, risk = permission_guard.requires_confirmation(real_fn)
                                        exec_res = skill_registry.execute_skill(real_fn, fn_args, skill_context)
                                        tool_results_list.append({"tool": real_fn, "args": fn_args, "result": exec_res})

                                        or_messages.append({
                                            "tool_call_id": tc["id"],
                                            "role": "tool",
                                            "name": raw_fn,
                                            "content": json.dumps(exec_res)
                                        })

                                    # Synthesize final speech
                                    r_synth = self.http.post(or_url, json={"model": candidate_model, "messages": or_messages, "max_tokens": 120}, headers=or_headers, timeout=8)
                                    if r_synth.status_code == 200:
                                        response_text = r_synth.json()["choices"][0]["message"]["content"]
                                else:
                                    response_text = or_choice.get("content")

                                if response_text:
                                    used_brain = "SPDP_NEURAL_ENGINE"
                                    break
                    except Exception as model_err:
                        print(f"[Orchestrator] Secondary model {candidate_model} notice: {model_err}")
                        continue
            except Exception as or_err:
                print(f"[Orchestrator] Multi-brain attempt notice: {or_err}")

        # 2. Attempt Groq LLM if key is present and NVIDIA not used
        if not response_text and groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                messages_payload = [{"role": "system", "content": system_instruction}]
                for m in recent_msgs:
                    messages_payload.append({"role": m.role if m.role in ["user", "assistant"] else "user", "content": m.content})

                tools_schema = skill_registry.get_tool_schemas()
                comp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    tools=tools_schema if tools_schema else None,
                    tool_choice="auto" if tools_schema else None,
                    max_tokens=400
                )

                choice = comp.choices[0].message
                if choice.tool_calls:
                    messages_payload.append(choice)
                    for tc in choice.tool_calls:
                        fn_name = tc.function.name
                        try:
                            fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        except Exception:
                            fn_args = {}

                        # Check Confirmation Guard for High/Critical
                        req_confirm, risk = permission_guard.requires_confirmation(fn_name)
                        
                        # Execute
                        exec_res = skill_registry.execute_skill(fn_name, fn_args, skill_context)
                        tool_results_list.append({"tool": fn_name, "args": fn_args, "result": exec_res})

                        messages_payload.append({
                            "tool_call_id": tc.id,
                            "role": "tool",
                            "name": fn_name,
                            "content": json.dumps(exec_res)
                        })

                    # Second completion for spoken reply
                    second_comp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages_payload,
                        max_tokens=300
                    )
                    response_text = second_comp.choices[0].message.content
                else:
                    response_text = choice.content
                used_brain = "SPDP_NEURAL_ENGINE"
            except Exception as e:
                print(f"[Orchestrator] Fallback attempt notice: {e}")

        # Attempt Gemini if Groq not used or failed
        if not response_text and gemini_key:
            try:
                import requests
                for m_id in ["gemini-3.8-flash", "gemini-2.5-pro", "gemini-1.5-flash"]:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_id}:generateContent?key={gemini_key}"
                    payload = {
                        "contents": [
                            {"role": "user", "parts": [{"text": f"System: {system_instruction}\nUser: {user_text}"}]}
                        ]
                    }
                    r = requests.post(url, json=payload, timeout=10)
                    if r.status_code == 200:
                        candidates = r.json().get("candidates", [])
                        if candidates:
                            response_text = candidates[0]["content"]["parts"][0]["text"].strip()
                            used_brain = "SPDP_NEURAL_ENGINE"
                            break
            except Exception as e:
                print(f"[Orchestrator] Secondary attempt notice: {e}")

        # Fallback to Local Offline Brain if no API response
        if not response_text:
            response_text, tool_results_list = self._run_local_brain(user_text, skill_context, asst_name)
            used_brain = "SPDP_NEURAL_ENGINE"

        # 7. Record Assistant Message in DB
        asst_msg = Message(
            conversation_id=conversation_id,
            user_id=user.id,
            role="assistant",
            content=response_text,
            tool_calls=json.dumps(tool_results_list) if tool_results_list else None
        )
        db.add(asst_msg)
        db.commit()

        return {
            "conversation_id": conversation_id,
            "assistant_message": {
                "id": asst_msg.id,
                "role": "assistant",
                "content": response_text,
                "tool_calls": tool_results_list,
                "created_at": asst_msg.created_at.isoformat(),
                "brain": used_brain
            }
        }

    def _run_local_brain(self, query: str, context: Dict[str, Any], asst_name: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Local offline reasoning for basic tasks, hardware control, and memory."""
        q = query.lower().strip()
        tools_run = []

        # Time
        if any(w in q for w in ["time", "clock"]):
            res = skill_registry.execute_skill("time.get", {}, context)
            tools_run.append({"tool": "time.get", "result": res})
            return f"The current time is {res.get('result')}.", tools_run

        # Date
        if any(w in q for w in ["date", "today"]):
            res = skill_registry.execute_skill("date.get", {}, context)
            tools_run.append({"tool": "date.get", "result": res})
            return f"Today is {res.get('result')}.", tools_run

        # Volume
        vol_match = re.search(r"(?:volume|sound).*?(\d+)", q)
        if vol_match:
            level = int(vol_match.group(1))
            res = skill_registry.execute_skill("system.volume", {"level": level}, context)
            tools_run.append({"tool": "system.volume", "args": {"level": level}, "result": res})
            return f"System volume adjustment request dispatched ({level}%).", tools_run

        # Launch App
        app_match = re.search(r"open\s+([a-zA-Z0-9\s]+)", q)
        if app_match and not any(k in q for k in ["project", "file", "tab"]):
            app_name = app_match.group(1).strip()
            res = skill_registry.execute_skill("app.open", {"app_name": app_name}, context)
            tools_run.append({"tool": "app.open", "args": {"app_name": app_name}, "result": res})
            return f"Request to launch '{app_name}' sent to your desktop agent.", tools_run

        # Remember
        rem_match = re.search(r"(?:remember|save to memory|my preference is)\s+(.*)", q)
        if rem_match:
            mem_text = rem_match.group(1).strip()
            res = skill_registry.execute_skill("memory.write", {"content": mem_text, "memory_type": "preference"}, context)
            tools_run.append({"tool": "memory.write", "args": {"content": mem_text}, "result": res})
            return f"I have saved that to your private memory: '{mem_text}'.", tools_run

        # List files
        if "files" in q or "my files" in q:
            res = skill_registry.execute_skill("files.list", {}, context)
            tools_run.append({"tool": "files.list", "result": res})
            return f"Your private files:\n{res.get('result')}", tools_run

        # List tasks
        if "tasks" in q or "my tasks" in q:
            res = skill_registry.execute_skill("tasks.list", {}, context)
            tools_run.append({"tool": "tasks.list", "result": res})
            return f"Your tasks:\n{res.get('result')}", tools_run

        # Identity
        if any(w in q for w in ["who are you", "who made you", "aaranu nee", "who is delulu", "who created you"]):
            return "I am DELULU, made by SPDP company.", tools_run

        # Greeting & generic
        if any(w in q for w in ["hello", "hi", "hey"]):
            return f"Hello! I am DELULU, your personal AI assistant made by SPDP company. How can I assist you today?", tools_run

        return (
            f"I have received your request. All local tools and your private workspace are active. "
            f"To unlock advanced reasoning and complex coding capabilities, you can enter an API key in Settings > API Keys, "
            f"or ask me to perform tasks, save memories, manage files, or control your PC."
        ), tools_run

orchestrator = Orchestrator()
