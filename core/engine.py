import os
import json
import re
from typing import Optional, Dict, Any
from core.registry import SkillRegistry
from core.permission import PermissionGuard
from dotenv import load_dotenv

load_dotenv()

class JarvisEngine:
    """
    Multi-Brain Reasoning Engine for JARVIS.
    Orchestrates Groq (Primary), Google Gemini (Secondary/Multimodal),
    and Local Offline fallback brains with safety permission verification.
    """

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.permission_guard = PermissionGuard()

        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

        # Groq Client setup
        self.groq_client = None
        self.groq_model = "llama-3.3-70b-versatile"
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                print(f"[Engine] Groq initialization notice: {e}")

        # Gemini Client setup
        self.gemini_client = None
        self.gemini_model = "gemini-2.5-flash"
        if self.gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"[Engine] Gemini initialization notice: {e}")

        self.system_instruction = (
            "You are JARVIS (also called Delulu), an exceptionally advanced, loyal, and witty AI assistant. "
            "Address the user politely as Sir or Ma'am. "
            "Use the provided tools whenever an action (volume change, open app, weather check, file, camera, time, web search) is requested. "
            "Keep verbal responses concise, clear, and natural for speech synthesis. "
            "Output VALID JSON arguments only when invoking tools."
        )

    def run_conversation(self, user_prompt: str) -> str:
        """
        Executes query through Multi-Brain priority:
        1. Groq (Fastest LLM with function calling)
        2. Gemini (Multimodal & resilient reasoning)
        3. Local Offline Brain (Zero internet/API key dependency)
        """
        # Reload keys in case .env was edited at runtime
        if not self.groq_api_key:
            self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
            if self.groq_api_key and not self.groq_client:
                try:
                    from groq import Groq
                    self.groq_client = Groq(api_key=self.groq_api_key)
                except Exception:
                    pass

        if not self.gemini_api_key:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if self.gemini_api_key and not self.gemini_client:
                try:
                    from google import genai
                    self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                except Exception:
                    pass

        # 1. Try Groq Brain
        if self.groq_client:
            try:
                response = self._run_groq(user_prompt)
                if response:
                    return response
            except Exception as e:
                print(f"[Engine] Groq failed, switching to backup brain: {e}")

        # 2. Try Gemini Brain
        if self.gemini_client:
            try:
                response = self._run_gemini(user_prompt)
                if response:
                    return response
            except Exception as e:
                print(f"[Engine] Gemini failed, switching to local brain: {e}")

        # 3. Local Offline Brain Fallback
        return self._run_local_brain(user_prompt)

    def _execute_tool_with_permission(self, func_name: str, args: Dict[str, Any]) -> str:
        """Wraps tool execution with the permission guard."""
        func = self.registry.get_function(func_name)
        if not func:
            return f"Error: Tool '{func_name}' not found."

        # Check permission requirement
        is_sensitive, desc = self.permission_guard.is_sensitive(func_name, args)
        if is_sensitive:
            from core.voice import speak, listen
            authorized = self.permission_guard.request_permission(
                action_description=desc,
                voice_ask_fn=speak,
                voice_listen_fn=listen
            )
            if not authorized:
                return "Operation aborted. User authorization was not granted, Sir."

        try:
            res = func(**(args or {}))
            return str(res)
        except Exception as e:
            return f"Error executing {func_name}: {e}"

    def _run_groq(self, user_prompt: str) -> Optional[str]:
        messages = [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": user_prompt}
        ]

        tools_schema = self.registry.get_tools_schema()
        kwargs = {
            "model": self.groq_model,
            "messages": messages,
            "max_tokens": 300
        }
        if tools_schema:
            kwargs["tools"] = tools_schema
            kwargs["tool_choice"] = "auto"

        try:
            completion = self.groq_client.chat.completions.create(**kwargs)
        except Exception as e:
            err_str = str(e)
            if "tool_use_failed" in err_str:
                match = re.search(r"<function=(\w+)(?:.*?)(?=\{)(\{.*?\})<\/function>", err_str)
                if match:
                    func_name = match.group(1)
                    func_args = json.loads(match.group(2))
                    return self._execute_tool_with_permission(func_name, func_args)
            raise e

        msg = completion.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = {}
                try:
                    if tool_call.function.arguments:
                        fn_args = json.loads(tool_call.function.arguments)
                except Exception:
                    pass

                tool_result = self._execute_tool_with_permission(fn_name, fn_args)
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": tool_result
                })

            second = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                max_tokens=250
            )
            return second.choices[0].message.content

        return msg.content

    def _run_gemini(self, user_prompt: str) -> Optional[str]:
        if not self.gemini_api_key:
            return None
        import requests
        candidate_models = ["gemini-3.8-flash", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-flash"]
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"System Instruction: {self.system_instruction}\n\nUser: {user_prompt}"}]}
            ]
        }
        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
            try:
                r = requests.post(url, json=payload, timeout=12)
                if r.status_code == 200:
                    data = r.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
            except Exception:
                continue
        return None

    def _run_local_brain(self, prompt: str) -> str:
        """Offline rule-based brain for when internet or API keys are unavailable."""
        p = prompt.lower().strip()

        # Check for time/date
        if any(w in p for w in ["time", "clock"]):
            func = self.registry.get_function("get_current_time")
            if func:
                return f"Sir, the current time is {func()}."
            import datetime
            return f"Sir, the time is {datetime.datetime.now().strftime('%I:%M %p')}."

        if any(w in p for w in ["date", "day", "today"]):
            func = self.registry.get_function("get_current_date")
            if func:
                return f"Today is {func()}, Sir."
            import datetime
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}, Sir."

        # Check for volume control
        vol_match = re.search(r"(?:volume|sound).*?(\d+)", p)
        if vol_match:
            level = int(vol_match.group(1))
            res = self._execute_tool_with_permission("set_volume", {"level": level})
            return f"System volume adjusted to {level} percent, Sir."

        # Check for app opening
        app_match = re.search(r"open\s+([a-zA-Z0-9\s]+)", p)
        if app_match and not any(k in p for k in ["website", "url", "google", "camera"]):
            app_name = app_match.group(1).strip()
            res = self._execute_tool_with_permission("open_app", {"app_name": app_name})
            return f"Opening {app_name} for you now, Sir."

        # Check for camera / object detection
        if any(w in p for w in ["detect", "detection", "what do you see", "look"]):
            res = self._execute_tool_with_permission("detect_objects", {})
            return f"Visual scan results: {res}"

        if any(w in p for w in ["photo", "take picture", "camera"]):
            res = self._execute_tool_with_permission("take_photo", {})
            return f"Camera capture executed: {res}"

        # Check for screenshot
        if "screenshot" in p:
            res = self._execute_tool_with_permission("take_screenshot", {})
            return f"Screenshot captured: {res}"

        # Check for weather
        if "weather" in p:
            func = self.registry.get_function("get_current_location_weather")
            if func:
                return str(func())
            return "Weather skill is currently offline without an OpenWeatherMap API key, Sir."

        # Greetings & Status
        if any(w in p for w in ["hello", "hi", "hey"]):
            return "Greetings, Sir. Delulu is fully operational and awaiting your instructions."

        if any(w in p for w in ["status", "report", "system"]):
            return "All local subsystems are green, Sir. Standing by."

        if any(w in p for w in ["thank", "thanks"]):
            return "Always a pleasure to be of service, Sir."

        return (
            "I heard you, Sir. To enable advanced conversational intelligence, "
            "please add your GROQ_API_KEY or GEMINI_API_KEY to the .env file. "
            "All local skills and hardware controls remain fully active."
        )
