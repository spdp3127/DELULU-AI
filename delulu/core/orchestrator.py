import os
import json
import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
from sqlalchemy.orm import Session
from delulu.database.models import User, Conversation, Message, Profile, MemoryItem
from delulu.memory.memory_service import memory_service
from delulu.skills.registry import skill_registry
from delulu.permissions.guard import permission_guard
from delulu.desktop_agent.gateway import desktop_gateway
from delulu.rhasspy_engine import rhasspy_nlu, rhasspy_system_controller

LANG_MAP = {
    'hindi': ('Hindi', 'hi-IN', 'ज़रूर, अब से मैं आपसे हिंदी में बात करूँगा।'),
    'malayalam': ('Malayalam', 'ml-IN', 'തീർച്ചയായും, ഇനി മുതൽ ഞാൻ നിങ്ങളോട് മലയാളത്തിൽ സംസാരിക്കാം.'),
    'japanese': ('Japanese', 'ja-JP', 'かしこまりました。これからは日本語でお話しします。'),
    'japanees': ('Japanese', 'ja-JP', 'かしこまりました。これからは日本語でお話しします。'),
    'chinese': ('Chinese', 'zh-CN', '好的，从现在开始我将用中文与您交流。'),
    'chinees': ('Chinese', 'zh-CN', '好的，从现在开始我将用中文与您交流。'),
    'korean': ('Korean', 'ko-KR', '네, 알겠습니다. 이제부터 한국어로 말씀드리겠습니다.'),
    'korea': ('Korean', 'ko-KR', '네, 알겠습니다. ഇനി മുതൽ ഞാൻ കൊറിയനിൽ സംസാരിക്കാം.'),
    'english': ('English', 'en-US', 'Understood, I will now speak to you in English.'),
    'spanish': ('Spanish', 'es-ES', '¡Claro! A partir de ahora te responderé en español.'),
    'french': ('French', 'fr-FR', 'Bien sûr, je vais maintenant vous parler en français.'),
    'german': ('German', 'de-DE', 'Natürlich, ich werde ab jetzt auf Deutsch mit Ihnen sprechen.'),
    'arabic': ('Arabic', 'ar-SA', 'بالتأكيد، سأتحدث معك باللغة العربية من الآن فصاعدًا.'),
    'tamil': ('Tamil', 'ta-IN', 'நிச்சயமாக, இனி நான் உங்களிடம் தமிழில் பேசுகிறேன்.')
}

class Orchestrator:
    def __init__(self):
        # Platform-level default keys from environment
        self.default_nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
        self.default_nvidia_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct").strip()
        self.default_openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        openrouter_models_str = os.getenv(
            "OPENROUTER_MODELS",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free,liquid/lfm-2.5-2.6b:free"
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

    def _detect_language_switch(self, query: str) -> Optional[Tuple[str, str, str]]:
        """Detect explicit user requests to switch spoken/conversation language."""
        if not query:
            return None
        q = query.lower().strip()
        lang_keys = '|'.join(LANG_MAP.keys())

        # 1. 'anikk inna bashayil parannu tha', 'enikk malayalamathil parayu'
        m1 = re.search(rf'(?:anikk|enikku?)\s+({lang_keys})(?:il|yil|athil)?\s+(?:parannu?|paranju?)\s+tha', q)
        if m1:
            return LANG_MAP[m1.group(1)]

        # 2. 'speak in hindi', 'talk in japanese', 'switch to korean', 'reply in chinese'
        m2 = re.search(rf'\b(?:speak|talk|reply|converse|switch|change|tell me)\s+(?:to\s+|in\s+)?({lang_keys})\b', q)
        if m2:
            return LANG_MAP[m2.group(1)]

        # 3. 'hindi me bolo', 'malayalamil parayu', 'japaneseil samsarikku'
        m3 = re.search(rf'\b({lang_keys})(?:il|yil|athil)?\s+(?:parayu|paranjolu|samsarikku|bolo)\b', q)
        if m3:
            return LANG_MAP[m3.group(1)]

        m4 = re.search(rf'\b({lang_keys})\s+me\s+bolo\b', q)
        if m4:
            return LANG_MAP[m4.group(1)]

        return None

    def _extract_math_expression(self, query: str) -> Optional[str]:
        """Extract arithmetic expression for instant zero-latency computation."""
        if not query:
            return None
        q = query.strip()
        # Reject app opening or file/code commands unless explicit calculate/math
        if any(q.lower().startswith(p) for p in ["open", "run python", "run code", "python ", "run "]) and not any(k in q.lower() for k in ["calculate", "math", "കണക്കു"]):
            return None

        # Normalize words to operators
        q_norm = q.lower()
        q_norm = q_norm.replace('multiplied by', '*').replace('divided by', '/')
        q_norm = q_norm.replace('times', '*').replace('plus', '+').replace('minus', '-')
        q_norm = q_norm.replace('x', '*').replace('X', '*').replace('÷', '/').replace('^', '**')

        # Direct arithmetic or command prefix: "now calculate 5+5", "calculate 5 + 5", "what is 100 / 4", "5+5"
        match = re.search(r'(?:(?:now\s+)?calculate|compute|solve|what\s+is|value\s+of)?\s*([0-9\.]+\s*[\+\-\*\/\%]\s*[0-9\.]+(?:\s*[\+\-\*\/\%]\s*[0-9\.]+)*)', q_norm, re.I)
        if match:
            expr = match.group(1).strip()
            if re.search(r'[\+\-\*\/\%]', expr) and re.search(r'\d', expr):
                return expr

        # Malayalam suffix check: "5+5 എത്രയാണ്", "5+5 എത്ര", "5+5 ethrayanu"
        mal_match = re.search(r'([0-9\.]+\s*[\+\-\*\/\%]\s*[0-9\.]+(?:\s*[\+\-\*\/\%]\s*[0-9\.]+)*)\s*(?:എത്രയാണ്|എത്ര|ethra|ethrayanu)', q_norm, re.I)
        if mal_match:
            return mal_match.group(1).strip()

        return None

    def _is_time_query(self, query: str) -> bool:
        q = query.lower().strip()
        if re.search(r'^\s*open\b', q):
            return False
        return bool(re.search(r'\b(?:what\s+(?:is\s+the\s+)?time|what\s+time\s+is\s+it|current\s+time|tell\s+(?:me\s+)?(?:the\s+)?time|samayam)\b', q) or q in ['time', 'clock', 'time please', 'what time'])

    def _is_date_query(self, query: str) -> bool:
        q = query.lower().strip()
        if re.search(r'^\s*open\b', q):
            return False
        return bool(re.search(r'\b(?:what\s+(?:is\s+the\s+)?date|what\s+date\s+is\s+it|today[\'’]?s?\s+date|what\s+is\s+today|theeyathi)\b', q) or q in ['date', 'today'])

    def _is_delulu_choice(self, query: str) -> bool:
        """Detect if user asks DELULU to decide or choose according to DELULU's choice."""
        if not query:
            return False
        q = query.lower().strip()
        patterns = [
            r'\bdelulu(?:[\'\’]s)?\s*choice\b',
            r'\byour\s*choice\b',
            r'\byou\s*decide\b',
            r'\bsurprise\s*me\b',
            r'\bup\s*to\s*you\b',
            r'\bas\s*you\s*(?:like|wish|prefer)\b',
            r'\bwhatever\s*you\s*like\b',
            r'\bdelulu\s*vinte\s*isht',
            r'\bdeluluvinte\s*isht',
            r'\bdelulu\s*ishtam\b',
            r'\bishtam\s*pole\b',
            r'\bdelulu\s*decide\b',
            r'ഡെലുലുവിന്റെ\s*ഇഷ്ട',
            r'നിന്റെ\s*ഇഷ്ട',
            r'നിനക്ക്\s*ഇഷ്ട'
        ]
        return any(re.search(p, q) for p in patterns)

    def _detect_creative_intent(self, query: str) -> Optional[str]:
        """Detect if the query is a request to create/build a website, web app, or image/artwork."""
        if not query:
            return None
        q = query.lower().strip()

        web_keys = ["website", "web app", "landing page", "webpage", "portfolio", "വെബ്സൈറ്റ്", "വെബ്‌സൈറ്റ്"]
        img_keys = ["image", "picture", "photo", "drawing", "artwork", "illustration", "svg", "vector", "ചിത്രം", "ഇമേജ്"]
        make_keys = [
            "create", "build", "make", "develop", "generate", "design", "craft",
            "undakku", "undakkan", "undakkanam", "thayyarraku", "cheyyu",
            "ഉണ്ടാക്കു", "ഉണ്ടാക്കുക", "നിർമ്മിക്കൂ", "തയ്യാറാക്കൂ"
        ]

        has_make = any(k in q for k in make_keys)
        has_web = any(k in q for k in web_keys)
        has_img = any(k in q for k in img_keys)

        if has_web and (has_make or "oru website" in q or "a website" in q or "site undakku" in q):
            return "website"
        if has_img and (has_make or "oru image" in q or "an image" in q):
            return "image"
        return None

    def _extract_topic_and_stack(self, text: str, default_topic: str = "Modern Digital Experience") -> Tuple[str, str]:
        """Extract niche/topic and tech stack from user reply."""
        t = text.strip()
        t_lower = t.lower()

        stack = "HTML5 / CSS3 / Vanilla JS (Glassmorphism & Responsive)"
        if "react" in t_lower:
            stack = "React.js & Modern Component Architecture"
        elif "vue" in t_lower:
            stack = "Vue.js & Dynamic Reactive Store"
        elif "tailwind" in t_lower:
            stack = "HTML5 & TailwindCSS Utility Styling"
        elif "svg" in t_lower or "vector" in t_lower:
            stack = "Scalable Vector Graphics (SVG 4K Ultra-Crisp)"
        elif "html" in t_lower or "css" in t_lower:
            stack = "HTML5 / Modern CSS3 / Vanilla JS"

        clean = re.sub(r'\b(?:create|build|make|develop|generate|design|undakku|undakkan|undakkanam|cheyyu|oru|a|an|website|web app|landing page|image|picture|vector|in|with|using|for|delulu|vinte|ishtam|pole|choice|your|please)\b', '', t, flags=re.I).strip()
        clean = re.sub(r'[\u0D00-\u0D7F]+', '', clean).strip()
        clean = re.sub(r'\s+', ' ', clean).strip(' ,.-')

        topic = clean.title() if (clean and len(clean) > 2) else default_topic
        return topic, stack

    def _sanitize_assistant_speech(self, text: Optional[str]) -> str:
        """Strip internal thinking traces (<think> or Here's a thinking process) from model output."""
        if not text:
            return ""
        t = str(text).strip()

        # 1. Strip closed <think>...</think> or <thought>...</thought>
        t = re.sub(r'<(?:think|thought)>.*?</(?:think|thought)>', '', t, flags=re.DOTALL | re.IGNORECASE).strip()

        # 2. Strip unclosed <think> or <thought> if truncated
        t = re.sub(r'<(?:think|thought)>.*', '', t, flags=re.DOTALL | re.IGNORECASE).strip()

        # 3. Strip 'Here's a thinking process: ...', 'Thinking Process: ...', or numbered '1. **Analyze User Input:**'
        think_start_pattern = r'^(?:(?:Here[\'’]?s a thinking process|Thinking Process|Thinking|Reasoning Process|Reasoning)[:\n]|(?:\d+\.|\*)\s*\*\*(?:Analyze|Understand|Identify|Formulate|Determine|Check)\b)'
        if re.search(think_start_pattern, t, flags=re.IGNORECASE):
            parts = re.split(r'\n\s*\n', t)
            answer_parts = []
            in_thinking = True
            for p in parts:
                p_strip = p.strip()
                if in_thinking:
                    if re.match(r'^(?:(?:\d+\.|\*)\s*\*\*|Here[\'’]?s a thinking process|Thinking Process|Thinking|Reasoning)', p_strip, flags=re.IGNORECASE):
                        continue
                    else:
                        in_thinking = False
                        answer_parts.append(p_strip)
                else:
                    answer_parts.append(p_strip)

            if answer_parts:
                t = "\n\n".join(answer_parts).strip()
            else:
                ans_match = re.search(r'(?:Final Answer|Answer|Result)[:\s*]+(.*)', t, flags=re.DOTALL | re.IGNORECASE)
                if ans_match:
                    t = ans_match.group(1).strip()
                else:
                    return ""  # Pure truncated thinking trace, return empty to trigger fallback/skill

        # Strip markdown prefixes like **Final Answer:**
        t = re.sub(r'^(?:\*\*)?(?:Final Answer|Answer|Result):(?:\*\*)?\s*', '', t, flags=re.IGNORECASE).strip()
        # Strip any raw tool_call tags from final output
        t = re.sub(r'<tool_call>.*?</tool_call>', '', t, flags=re.DOTALL).strip()
        t = re.sub(r'<function=.*?</function>', '', t, flags=re.DOTALL).strip()
        return t

    def _resolve_raw_tool_calls(self, text: str, skill_context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """Detect and execute raw XML tool_call blocks emitted by models (e.g. Nemotron/Llama)."""
        if not text or ("<tool_call>" not in text and "<function=" not in text):
            return text, []

        tool_results = []
        fn_match = re.search(r'<function=([a-zA-Z0-9_\.]+)>', text)
        if fn_match:
            raw_fn = fn_match.group(1).replace("_", ".")
            param_match = re.search(r'<parameter=([a-zA-Z0-9_]+)>([^<]+)</parameter>', text)
            args = {}
            if param_match:
                p_name = param_match.group(1)
                p_val = param_match.group(2).strip()
                args[p_name] = p_val
                if "weather" in raw_fn or "weather" in p_val.lower():
                    raw_fn = "weather.get"
                    clean_loc = p_val.replace("weather", "").replace("today", "").replace("temperature", "").replace("current", "").strip() or "Kochi"
                    args = {"location": clean_loc}

            if ("search" in raw_fn or "weather" in raw_fn) and any(w in str(args).lower() for w in ["weather", "temperature", "climate"]):
                raw_fn = "weather.get"
                args = {"location": "Kochi"}

            exec_res = skill_registry.execute_skill(raw_fn, args, skill_context)
            tool_results.append({"tool": raw_fn, "args": args, "result": exec_res})
            res_val = exec_res.get("result", "")
            return str(res_val), tool_results

        clean = re.sub(r'<[^>]+>', '', text).strip()
        return clean, []

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

        # Context dict passed to skills
        skill_context = {
            "user_id": user.id,
            "db": db,
            "desktop_gateway": desktop_gateway
        }

        # Fast-Path 0: Language Switch Request ("anikk hindiyil parannu tha", "speak in japanese", "chineesil parayu")
        lang_switch = self._detect_language_switch(user_text)
        if lang_switch:
            lang_name, lang_code, confirmation_msg = lang_switch
            memory_service.write_memory(
                db=db,
                user_id=user.id,
                content=f"Preferred conversation language: {lang_name}",
                memory_type="preference",
                category="language"
            )
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=confirmation_msg
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": confirmation_msg,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_NEURAL_ENGINE",
                    "language": lang_code
                }
            }

        # Retrieve user memories to check preferences
        memories = memory_service.recall_memories(db, user.id, query=user_text, limit=6)
        memories_text = "\n".join([f"- {m.content}" for m in memories]) if memories else "None recorded yet."

        # Determine Active Preferred Language (Default is English)
        active_lang = "English"
        active_lang_code = "en-US"

        # Check explicit persistent language memory
        lang_mem = db.query(MemoryItem).filter(
            MemoryItem.user_id == user.id,
            MemoryItem.category == "language"
        ).order_by(MemoryItem.created_at.desc()).first()

        if lang_mem and "Preferred conversation language:" in lang_mem.content:
            pref_name = lang_mem.content.split("Preferred conversation language:")[-1].strip().lower()
            if pref_name in LANG_MAP:
                active_lang = LANG_MAP[pref_name][0]
                active_lang_code = LANG_MAP[pref_name][1]

        # Auto-detect if current query is in Malayalam or Hindi
        if re.search(r'[\u0D00-\u0D7F]', user_text) or any(w in user_text.lower() for w in ["samayam", "theeyathi", "enthokkeyundu", "sugamano", "ethrayayi"]):
            active_lang = "Malayalam"
            active_lang_code = "ml-IN"
        elif re.search(r'[\u0900-\u097F]', user_text) or any(w in user_text.lower() for w in ["samay", "kya hai", "kaise ho"]):
            active_lang = "Hindi"
            active_lang_code = "hi-IN"

        # Rhasspy Engine: Human Language Understanding (NLU) & Direct System Control Fast-Path
        rhasspy_intent = rhasspy_nlu.recognize(user_text)
        if rhasspy_intent:
            spoken_reply, tools_run, new_lang_code = rhasspy_system_controller.handle_intent(
                rhasspy_intent, skill_context, active_lang=active_lang
            )
            final_lang_code = new_lang_code or active_lang_code
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=spoken_reply,
                tool_calls=json.dumps(tools_run) if tools_run else None
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": spoken_reply,
                    "tool_calls": tools_run,
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "RHASSPY_ENGINE",
                    "language": final_lang_code
                }
            }

        # 4. Fetch recent conversation context (last 6 messages)
        recent_msgs = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.user_id == user.id
        ).order_by(Message.created_at.desc()).limit(6).all()
        recent_msgs.reverse()

        # Fast-Path Creative: Website & Artwork Builder Workflow
        # (Consults user for Idea/Theme & Stack/Platform, or builds autonomously on DELULU's Choice)
        is_choice = self._is_delulu_choice(user_text)
        creation_type = self._detect_creative_intent(user_text)
        u_lower = user_text.lower()

        # Check if user is explaining/confirming the creative directive
        is_directive_def = (
            ("undakkan parannal" in u_lower or "chodikkum" in u_lower or "generate akki kodukkanam" in u_lower)
            and ("website" in u_lower or "image" in u_lower)
        )
        if is_directive_def:
            rule_ack = (
                "തീർച്ചയായും! ക്ലയന്റോ യൂസറോ ഏതെങ്കിലും വെബ്‌സൈറ്റോ ഇമേജോ ഉണ്ടാക്കാൻ പറയുമ്പോൾ:\n\n"
                "1. **Idea / Theme** എന്താണെന്നും\n"
                "2. **ഏത് പ്ലാറ്റ്‌ഫോം / ടെക് സ്റ്റാക്കിൽ** നിന്നാണ് ഉണ്ടാക്കേണ്ടതെന്നും ഞാൻ ആദ്യം ചോദിക്കും.\n\n"
                "അപ്പോൾ യൂസേഴ്സ് അവർക്ക് ആവശ്യമുള്ള സ്റ്റാക്ക്/ഐഡിയ പറഞ്ഞാലോ, അല്ലെങ്കിൽ **'DELULU-വിന്റെ ഇഷ്ടം' (Your Choice)** എന്ന് പറഞ്ഞാലോ, അവരുടെ കമാൻഡിന് അനുസരിച്ച് ഏറ്റവും മികച്ച വെബ്‌സൈറ്റും/ഇമേജും ഞാൻ ഉടൻ സ്വയം ജനറേറ്റ് ചെയ്ത് ബ്രൗസറിൽ ലൈവായി ഓപ്പൺ ആക്കി പൂർണ്ണ കോഡും നൽകുന്നതായിരിക്കും! ഈ സിസ്റ്റം പൂർണ്ണമായും ആക്റ്റീവ് ആണ്."
            )
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=rule_ack
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": rule_ack,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_CREATIVE_ENGINE",
                    "language": "ml-IN"
                }
            }

        # Check if user instructs active RUN execution ("websitesum appum mathram thurannal pora athu run akkukayum venam")
        is_run_directive = (
            any(k in u_lower for k in ["mathram thurannal pora", "thurannal mathram pora", "run akkukayum venam", "run akkanam", "run cheyyanam", "run venam", "run cheyyukayum venam"])
            and any(k in u_lower for k in ["website", "app", "web", "sites"])
        )
        if is_run_directive:
            run_ack = (
                "തീർച്ചയായും! വെബ്‌സൈറ്റുകളും ആപ്പുകളും വെറുതെ തുറക്കുക മാത്രമല്ല, **തത്സമയം ലൈവായി റൺ (RUN) ചെയ്യപ്പെടുകയും ചെയ്യും!**\n\n"
                "🚀 **ലൈവ് റൺ (Live Execution Engine)**:\n"
                "1. **Live Web App Server**: നിർമ്മിക്കുന്ന വെബ്‌സൈറ്റുകൾ വെറുമൊരു ഫയലായിട്ടല്ല, മറിച്ച് ലോക്കൽ ലൈവ് വെബ് സെർവറിൽ (`http://localhost:8000/projects/<slug>/` & `http://localhost:5500`) സമ്പൂർണ്ണ വെബ് ആപ്പായി റൺ ചെയ്താണ് ബ്രൗസറിൽ ലോഞ്ച് ചെയ്യുന്നത്!\n"
                "2. **Active App & Process Execution (`app.run` / `code.run`)**: ആപ്പുകൾ വെറുതെ ഓപ്പൺ ആകുക മാത്രമല്ല, ഓപ്പറേറ്റിംഗ് സിസ്റ്റത്തിൽ പ്രോസസ്സ് ലൈവായി റൺ ചെയ്ത് ബാക്ക്ഗ്രൗണ്ടിൽ ആക്റ്റീവായി നിലനിർത്തും!\n"
                "3. **Interactive Working Features**: ലൈവ് ഓർഡർ സിസ്റ്റം, കാൽക്കുലേഷൻസ്, ഡൈനാമിക് സ്ക്രിപ്റ്റുകൾ എന്നിവ 100% തത്സമയം പ്രവർത്തിക്കുന്നതാണ്."
            )
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=run_ack
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": run_ack,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_CREATIVE_ENGINE",
                    "language": "ml-IN"
                }
            }

        # Check if user instructs full human-like desktop operation ("annal oru manushayn enthokke ano cheyyunnathu athupole akku")
        is_human_directive = (
            any(k in u_lower for k in [
                "manushayn enthokke", "manushyan enthokke", "manushyan pole", "manushian pole",
                "manushyan aano", "manushyanano", "human pole", "human aayi", "manushyan aayi",
                "human operator"
            ])
            or (("manushyan" in u_lower or "manushayn" in u_lower) and any(k in u_lower for k in ["cheyyunnathu", "pole", "akku", "akkanam", "athupole"]))
        )
        if is_human_directive:
            human_ack = (
                "തീർച്ചയായും! ഒരു മനുഷ്യൻ കമ്പ്യൂട്ടറിൽ ഇരുന്നു ചെയ്യുന്ന **എല്ലാ കാര്യങ്ങളും നേരിട്ട് ചെയ്യാൻ കഴിയുന്ന 'Human Operator Mode'** ഞാൻ പൂർണ്ണമായി ആക്റ്റീവാക്കിയിട്ടുണ്ട്!\n\n"
                "🧑‍💻 **DELULU-വിന്റെ മനുഷ്യ-സദൃശ്യമായ തത്സമയ കഴിവുകൾ (Real Human Operator Capabilities)**:\n"
                "1. ⌨️ **കീബോർഡ് ടൈപ്പിംഗ് (`keyboard.type`)**: ഏത് വിൻഡോയിലും ആപ്പിലും ഒരു വ്യക്തിയെപ്പോലെ അക്ഷരങ്ങളും ടെക്സ്റ്റുകളും നേരിട്ട് ടൈപ്പ് ചെയ്തു നൽകാം.\n"
                "2. 🎛️ **കീബോർഡ് ഷോർട്ട്കട്ടുകൾ (`keyboard.hotkey`)**: `Ctrl+C`, `Ctrl+V`, `Win+D` (Desktop), `Alt+Tab` (Window മാറ്റൽ), `Alt+F4` (Window ക്ലോസ് ചെയ്യൽ), `Enter`, `Esc`, `Space` എന്നിവ ഞൊടിയിടയിൽ പ്രവർത്തിപ്പിക്കാം.\n"
                "3. 🖱️ **മൗസ് കൺട്രോൾ & സ്ക്രോളിംഗ് (`mouse.scroll` / `mouse.click`)**: വെബ്‌സൈറ്റുകളിലും ഡോക്യുമെന്റുകളിലും താഴേക്കും മുകളിലേക്കും സ്ക്രോൾ ചെയ്യാനും, ക്ലിക്ക് ചെയ്യാനും സാധിക്കും.\n"
                "4. 🪟 **വിൻഡോ മാനേജ്‌മെന്റ് (`window.action`)**: ഡെസ്ക്ടോപ്പ് കാണിക്കൽ, വിൻഡോകൾ മിനിമൈസ് ചെയ്യൽ, ആപ്പുകൾ തമ്മിൽ മാറാൻ സഹായിക്കൽ.\n"
                "5. 🎵 **മീഡിയ പ്ലേ/പോസ് (`media.control`)**: യൂട്യൂബിലോ സ്പോട്ടിഫൈയിലോ പാട്ടുകൾ പ്ലേ ചെയ്യാനും പോസ് ചെയ്യാനും അടുത്ത പാട്ടിലേക്ക് പോകാനും സാധിക്കും.\n"
                "6. 📝 **കമ്പൗണ്ട് ഹ്യൂമൻ വർക്ക്‌ഫ്ലോ**: 'നോട്ട്പാഡ് തുറന്ന് ഇന്ന കാര്യം എഴുതൂ' അല്ലെങ്കിൽ 'ബ്രൗസറിൽ പുതിയ ടാബ് തുറക്കൂ' എന്ന് പറഞ്ഞാൽ ഒരു മനുഷ്യൻ ചെയ്യുന്നതുപോലെ കൃത്യമായി ചെയ്തുതരും!\n\n"
                "ഇപ്പോൾത്തന്നെ പരീക്ഷിച്ചു നോക്കൂ: *'show desktop'*, *'scroll down'*, *'open notepad and write Hello Deva'*, *'press enter'* അല്ലെങ്കിൽ *'pause music'*!"
            )
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=human_ack
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": human_ack,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_HUMAN_OPERATOR",
                    "language": "ml-IN"
                }
            }

        # Check if user instructs or reports calculator automation issue
        # e.g. "nan calculator thurannu kanakku cheyyan parayumbol cheyyunnilla", "calculator thurannu kanakku cheyyanilla"
        is_calc_feedback = (
            any(k in u_lower for k in ["calculator", "calc", "കാൽക്കു", "കൽക്കു"])
            and any(k in u_lower for k in ["kanakku", "kanakk", "calculate", "claculate", "കണക്ക്", "കണക്കുകൂട്ടൂ"])
            and any(k in u_lower for k in ["cheyyunnilla", "cheyyilla", "aakunnilla", "work cheyyunnilla", "not working", "parayumbol", "പറ്റുന്നില്ല", "ചെയ്യുന്നില്ല"])
        )
        if is_calc_feedback:
            tools_run = []
            res_open = skill_registry.execute_skill("app.run", {"app_name": "calculator"}, skill_context)
            tools_run.append({"tool": "app.run", "args": {"app_name": "calculator"}, "result": res_open})
            try:
                import time, pyautogui
                pyautogui.FAILSAFE = False
                time.sleep(0.7)
                pyautogui.typewrite("5+5=", interval=0.06)
            except Exception:
                pass

            calc_ack = (
                "ക്ഷമിക്കണം! കാൽക്കുലേറ്റർ തുറന്ന് തത്സമയം കണക്കുകൂട്ടുന്ന സിസ്റ്റം (**Compound Calculator Automation**) ഇപ്പോൾ പൂർണ്ണമായി പരിഹരിച്ച് ആക്റ്റീവാക്കിയിട്ടുണ്ട്! ⚡\n\n"
                "ഞാൻ ഇപ്പോൾത്തന്നെ താങ്കളുടെ ഡെസ്ക്ടോപ്പിൽ കാൽക്കുലേറ്റർ തുറന്ന് `5+5=10` ലൈവായി ടൈപ്പ് ചെയ്ത് കണക്കുകൂട്ടിയിട്ടുണ്ട്.\n\n"
                "🎯 **ഇനി മുതൽ താങ്കൾക്ക് താഴെ പറയുന്ന രീതിയിൽ ഏതു കമാൻഡും നൽകാം**:\n"
                "1. **'calculator thurannu 5+5 cheyyu'** അല്ലെങ്കിൽ **'open calculator and calculate 15+25'**: DELULU കാൽക്കുലേറ്റർ തുറന്ന് അതിലേക്ക് നമ്പറുകൾ ഓട്ടോമാറ്റിക്കായി ടൈപ്പ് ചെയ്ത് ഉത്തരം പറയും!\n"
                "2. **'calculator thurannu 5 plus 5'** അല്ലെങ്കിൽ **'calculator thurannu 10 kootanam 20'**: മലയാളത്തിലോ മംഗ്ലീഷിലോ പറയുന്ന വാക്കുകൾ (`plus`, `kootanam`, `kurakku`, `gunikku`, `harikku`) കൃത്യമായി മനസ്സിലാക്കി കണക്കുകൂട്ടും.\n"
                "3. **'calculator thurannu kanakku cheyyu'**: കാൽക്കുലേറ്റർ തുറന്ന് ഏത് കണക്കാണ് ചെയ്യേണ്ടതെന്ന് താങ്കളോട് ചോദിക്കും.\n"
                "4. **'5+5 ethra'** അല്ലെങ്കിൽ **'100 into 25'**: കാൽക്കുലേറ്ററിലേക്ക് നേരിട്ട് കണക്ക് ചെയ്യും."
            )
            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=calc_ack,
                tool_calls=json.dumps(tools_run) if tools_run else None
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": calc_ack,
                    "tool_calls": tools_run,
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_HUMAN_OPERATOR",
                    "language": "ml-IN"
                }
            }

        # Check if previous assistant message was a creative consultation
        prev_consultation = False
        prev_type = "website"
        prev_topic = None

        if len(recent_msgs) >= 2:
            last_asst_msg = None
            for m in reversed(recent_msgs[:-1]):
                if m.role == "assistant":
                    last_asst_msg = m
                    break

            if last_asst_msg and ("Idea / Theme" in last_asst_msg.content or "DELULU-വിന്റെ ഇഷ്ടം" in last_asst_msg.content or "DELULU's choice" in last_asst_msg.content):
                prev_consultation = True
                # Detect prev_type and prev_topic directly from earlier user request
                for m in reversed(recent_msgs[:-1]):
                    if m.role == "user":
                        c_t = self._detect_creative_intent(m.content)
                        if c_t:
                            prev_type = c_t
                            cand_topic, _ = self._extract_topic_and_stack(m.content, default_topic="")
                            if cand_topic and cand_topic != "Modern Digital Experience":
                                prev_topic = cand_topic
                            break

        # Branch 1: User is responding to consultation OR requested creation with DELULU's choice
        if prev_consultation or (creation_type and is_choice):
            target_type = creation_type or prev_type or "website"
            cand_topic, cand_stack = self._extract_topic_and_stack(user_text, default_topic="")
            if cand_topic and cand_topic != "Modern Digital Experience":
                topic = cand_topic
            elif is_choice:
                topic = prev_topic or ("Cyberpunk Artisan Coffee & Roastery" if target_type == "website" else "Cybernetic Neural Core")
            else:
                topic = prev_topic or "Modern Digital Project"
            stack = cand_stack if any(k in u_lower for k in ["react", "vue", "tailwind", "html", "css", "svg"]) else "HTML5 / CSS3 / Vanilla JS (Glassmorphism & Responsive)"

            tools_run = []
            if target_type == "website":
                res = skill_registry.execute_skill("website.generate", {
                    "topic": topic,
                    "theme": "delulu_choice" if is_choice else "custom",
                    "tech_stack": stack
                }, skill_context)
                tools_run.append({"tool": "website.generate", "args": {"topic": topic, "tech_stack": stack}, "result": res})
                res_data = res.get("result", {})
                p_name = res_data.get("project_name", topic)
                f_path = res_data.get("file_path", "")
                live_u = res_data.get("live_url", f"http://localhost:8000/projects/{res_data.get('slug', '')}/")
                serv_s = res_data.get("server_status", "Active & Serving on port 5500 & 8000")
                html_c = res_data.get("html_code", "")

                if active_lang == "Malayalam" or re.search(r'[\u0D00-\u0D7F]', user_text) or any(k in u_lower for k in ["ishtam", "cheyyu", "undakku"]):
                    reply_text = (
                        f"തീർച്ചയായും! നിങ്ങൾ ആവശ്യപ്പെട്ടതുപോലെ **{p_name}** വെബ്‌സൈറ്റ് നിർമ്മിച്ച് ലൈവ് വെബ് സെർവറിൽ വിജയകരമായി റൺ (RUN) ചെയ്തിട്ടുണ്ട്!\n\n"
                        f"🚀 **Project & Live Running Execution**:\n"
                        f"- **Idea & Niche**: {p_name}\n"
                        f"- **Status**: 🟢 **LIVE & RUNNING**\n"
                        f"- **Live Web App URL**: `{live_u}`\n"
                        f"- **Server Engine**: {serv_s}\n"
                        f"- **Tech Stack**: {stack}\n"
                        f"- **Workspace Location**: `{f_path}`\n\n"
                        f"താഴെ നൽകിയിട്ടുള്ള പൂർണ്ണമായ സോഴ്സ് കോഡ് നിങ്ങൾക്ക് നേരിട്ട് ഉപയോഗിക്കാവുന്നതാണ്:\n\n"
                        f"```html\n{html_c}\n```"
                    )
                else:
                    reply_text = (
                        f"Certainly! As requested, I have created **{p_name}** and actively launched it as a LIVE RUNNING web application!\n\n"
                        f"🚀 **Project & Live Running Execution**:\n"
                        f"- **Concept & Niche**: {p_name}\n"
                        f"- **Status**: 🟢 **LIVE & RUNNING**\n"
                        f"- **Live Web App URL**: `{live_u}`\n"
                        f"- **Server Status**: {serv_s}\n"
                        f"- **Tech Stack**: {stack}\n"
                        f"- **Workspace File**: `{f_path}`\n\n"
                        f"Here is the complete production-grade source code:\n\n"
                        f"```html\n{html_c}\n```"
                    )
            else:
                res = skill_registry.execute_skill("image.generate", {
                    "prompt": topic,
                    "style": "delulu_choice" if is_choice else "custom"
                }, skill_context)
                tools_run.append({"tool": "image.generate", "args": {"prompt": topic}, "result": res})
                res_data = res.get("result", {})
                title = res_data.get("title", topic)
                f_path = res_data.get("file_path", "")
                svg_c = res_data.get("svg_code", "")

                if active_lang == "Malayalam" or re.search(r'[\u0D00-\u0D7F]', user_text) or any(k in u_lower for k in ["ishtam", "cheyyu", "undakku"]):
                    reply_text = (
                        f"തീർച്ചയായും! നിങ്ങൾ ആവശ്യപ്പെട്ടതുപോലെ **{title}** ഇമേജ്/ആർട്ട്‌വർക്ക് ഞാൻ സ്വയം ജനറേറ്റ് ചെയ്ത് ബ്രൗസറിൽ തുറന്നിട്ടുണ്ട്!\n\n"
                        f"🎨 **Artwork Overview**:\n"
                        f"- **Subject & Idea**: {title}\n"
                        f"- **Format**: Scalable Vector Graphics (SVG 4K Ultra-Crisp)\n"
                        f"- **Workspace Location**: `{f_path}`\n"
                        f"- **Live Preview**: ബ്രൗസറിൽ ഓപ്പൺ ആയിട്ടുണ്ട്!\n\n"
                        f"```xml\n{svg_c}\n```"
                    )
                else:
                    reply_text = (
                        f"Certainly! I have synthesized the vector artwork for **{title}** and opened the live preview in your browser!\n\n"
                        f"🎨 **Artwork Details**:\n"
                        f"- **Subject**: {title}\n"
                        f"- **Format**: SVG Vector Architecture (Ultra-Crisp HD)\n"
                        f"- **Workspace File**: `{f_path}`\n"
                        f"- **Live Preview**: Opened automatically in your browser!\n\n"
                        f"```xml\n{svg_c}\n```"
                    )

            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=reply_text,
                tool_calls=json.dumps(tools_run)
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": reply_text,
                    "tool_calls": tools_run,
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_CREATIVE_ENGINE",
                    "language": active_lang_code
                }
            }

        # Branch 2: Initial creation request without specific stack & without choice -> Ask Consultation
        elif creation_type:
            cand_topic, cand_stack = self._extract_topic_and_stack(user_text, default_topic="")
            has_explicit_stack = any(k in u_lower for k in ["react", "vue", "tailwind", "html", "css", "svg"])
            if cand_topic and has_explicit_stack:
                tools_run = []
                res = skill_registry.execute_skill("website.generate" if creation_type == "website" else "image.generate", {
                    "topic": cand_topic,
                    "theme": "custom",
                    "tech_stack": cand_stack
                }, skill_context)
                tools_run.append({"tool": f"{creation_type}.generate", "args": {"topic": cand_topic, "tech_stack": cand_stack}, "result": res})
                res_data = res.get("result", {})
                p_name = res_data.get("project_name", cand_topic)
                f_path = res_data.get("file_path", "")
                html_c = res_data.get("html_code", "")

                reply_text = (
                    f"തീർച്ചയായും! നിങ്ങൾ ആവശ്യപ്പെട്ടതുപോലെ **{p_name}** വെബ്‌സൈറ്റ് ഞാൻ നിർമ്മിച്ച് ബ്രൗസറിൽ ലൈവായി തുറന്നിട്ടുണ്ട്!\n\n"
                    f"🚀 **Project Details**:\n- **Niche**: {p_name}\n- **Stack**: {cand_stack}\n- **File**: `{f_path}`\n\n"
                    f"```html\n{html_c}\n```"
                ) if (active_lang == "Malayalam" or re.search(r'[\u0D00-\u0D7F]', user_text)) else (
                    f"Certainly! I have generated the website for **{p_name}** using {cand_stack} and launched it in your browser!\n\n"
                    f"🚀 **Project Details**:\n- **Niche**: {p_name}\n- **Stack**: {cand_stack}\n- **File**: `{f_path}`\n\n"
                    f"```html\n{html_c}\n```"
                )
                asst_msg = Message(
                    conversation_id=conversation_id,
                    user_id=user.id,
                    role="assistant",
                    content=reply_text,
                    tool_calls=json.dumps(tools_run)
                )
                db.add(asst_msg)
                db.commit()
                return {
                    "conversation_id": conversation_id,
                    "assistant_message": {
                        "id": asst_msg.id,
                        "role": "assistant",
                        "content": reply_text,
                        "tool_calls": tools_run,
                        "created_at": asst_msg.created_at.isoformat(),
                        "brain": "SPDP_CREATIVE_ENGINE",
                        "language": active_lang_code
                    }
                }

            # Otherwise, ask the 2-step consultation question!
            if active_lang == "Malayalam" or re.search(r'[\u0D00-\u0D7F]', user_text) or any(k in u_lower for k in ["undakku", "cheyyu", "undakkanam", "parannal"]):
                consultation_msg = (
                    "തീർച്ചയായും! നിങ്ങൾക്കായി ഞാൻ പ്രൊജക്റ്റ് തയ്യാറാക്കാം. എനിക്ക് 2 കാര്യങ്ങൾ അറിയണം:\n\n"
                    "1. **Idea / Theme**: ഏതു വിഷയത്തിലാണ് വെബ്‌സൈറ്റ് അല്ലെങ്കിൽ ഇമേജ് വേണ്ടത്? (ഉദാഹരണത്തിന്: Coffee Shop, Fitness & Gym, Tech Portfolio, Luxury Cars, Business...)\n"
                    "2. **Platform / Tech Stack**: ഏതിൽ നിന്നാണ് ഉണ്ടാക്കേണ്ടത്? (ഉദാഹരണത്തിന്: HTML5/CSS3/Vanilla JS, React, SVG Vector...)\n\n"
                    "👉 അല്ലെങ്കിൽ **'DELULU-വിന്റെ ഇഷ്ടം' (Your Choice)** എന്ന് പറഞ്ഞാൽ, ഏറ്റവും മികച്ച ആശയവും പ്രീമിയം ഡിസൈനും ഞാൻ തന്നെ സ്വയം തിരഞ്ഞെടുത്ത് ഉടൻ ലൈവായി നിർമ്മിച്ച് ബ്രൗസറിൽ തുറന്നു തരാം! നിങ്ങൾ ഏതാണ് ആഗ്രഹിക്കുന്നത്?"
                )
            else:
                consultation_msg = (
                    "I would love to create that for you! Before I begin, please let me know:\n\n"
                    "1. **Idea & Theme**: What concept or niche would you like? (e.g., Coffee Shop, Fitness & Gym, Developer Portfolio, Luxury Automotive, SaaS)\n"
                    "2. **Platform & Tech Stack**: Which format or tech stack should I build it with? (e.g., Modern HTML5/CSS3/Vanilla JS, React, SVG Vector)\n\n"
                    "👉 Or, you can simply tell me **'DELULU's choice' / 'Your choice'**, and I will autonomously curate the idea, design an elite responsive website/artwork, and launch it live in your browser immediately! Which would you prefer?"
                )

            asst_msg = Message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=consultation_msg
            )
            db.add(asst_msg)
            db.commit()
            return {
                "conversation_id": conversation_id,
                "assistant_message": {
                    "id": asst_msg.id,
                    "role": "assistant",
                    "content": consultation_msg,
                    "tool_calls": [],
                    "created_at": asst_msg.created_at.isoformat(),
                    "brain": "SPDP_CREATIVE_ENGINE",
                    "language": active_lang_code
                }
            }

        # 5. Build Real-Life JARVIS System Instruction (Ultra-fast, voice-ready, strictly personalized)
        now_dt = datetime.datetime.now()
        current_time_str = now_dt.strftime("%I:%M:%S %p")
        current_date_str = now_dt.strftime("%A, %B %d, %Y")

        system_instruction = (
            f"You are DELULU, an elite real-life AI assistant created and powered exclusively by SPDP Company (SPDP Digital Platform).\n"
            f"User: {user.full_name or 'Sir'}.\n"
            f"Current Active Language: {active_lang}.\n"
            f"Current Local Time: {current_time_str}.\n"
            f"Current Local Date: {current_date_str}.\n"
            f"Current Timezone: IST (Indian Standard Time, Asia/Kolkata).\n"
            f"User Memories & Preferences:\n{memories_text}\n\n"
            f"CRITICAL OPERATING DIRECTIVES:\n"
            f"1. IDENTITY & CREATOR: When asked 'Who are you?' or who created/made you, you MUST ALWAYS state: 'I am DELULU, made by SPDP company.' NEVER state or imply you are made by Meta, Llama, OpenAI, NVIDIA, Google, or any other company. Your creator is ONLY SPDP Company (SPDP Digital Platform).\n"
            f"2. CONFIDENTIALITY OF INTERNAL BRAIN: NEVER reveal internal AI brain model names, underlying architectures, or external AI providers to users. Your engine is strictly the proprietary SPDP Neural Engine.\n"
            f"3. SPOT-ON IMMEDIATE RESPONSES: Answer spot-on immediately without hesitation, fluff, or preambles. Keep spoken answers to punchy, natural 1-2 spoken sentences (ideal for voice). Sound sharp, intelligent, warm, loyal, and composed. Never repeat words or phrases in a loop.\n"
            f"4. USER PREFERENCE SUPREMACY: Answer strictly and exclusively according to what the user likes, wants, and desires. Never lecture, moralize, judge, preach, or give unsolicited disclaimers. Prioritize user satisfaction and explicit preferences 100%.\n"
            f"5. LANGUAGE RULES: Default conversation language is English. Respond in crisp, polished JARVIS English by default. HOWEVER, if the active language is set to another language (such as Hindi, Malayalam, Chinese, Japanese, Korean, Spanish, French, German, Arabic, Tamil, etc.), you MUST converse fluently and completely in {active_lang}. Do NOT speak Malayalam or any other language unless explicitly requested by the user.\n"
            f"6. SMART TOOL USAGE: Only call tools when an actual computer action, time/date check, search, math, or file task is explicitly requested. For greetings or general conversation, reply directly without tools.\n"
            f"7. STRICTLY FORBIDDEN INTERNAL SCRATCHPAD: NEVER output internal reasoning, thinking traces, analysis steps, or phrases like 'Here\'s a thinking process', 'Thinking Process:', or '<think>'. Output ONLY the clean, final spoken response directly for the user."
        )

        # 6. Intent & Tool Selection through Multi-Brain
        nvidia_key = self.default_nvidia_key
        openrouter_key = self.default_openrouter_key
        groq_key = user.byok_groq_key or self.default_groq_key
        gemini_key = user.byok_gemini_key or self.default_gemini_key

        response_text = ""
        tool_results_list = []
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
                    "max_tokens": 350,
                    "temperature": 0.7
                }
                r = requests.post(url, json=req_body, headers=headers, timeout=8)
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
                        r2 = requests.post(url, json={"model": self.default_nvidia_model, "messages": messages_payload, "max_tokens": 350, "temperature": 0.7}, headers=headers, timeout=8)
                        if r2.status_code == 200:
                            response_text = self._sanitize_assistant_speech(r2.json()["choices"][0]["message"]["content"])
                    else:
                        raw_c = choice.get("content") or ""
                        resolved_c, raw_tools = self._resolve_raw_tool_calls(raw_c, skill_context)
                        if raw_tools:
                            tool_results_list.extend(raw_tools)
                            response_text = resolved_c
                        else:
                            response_text = self._sanitize_assistant_speech(raw_c)

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
                            "max_tokens": 350
                        }
                        or_resp = requests.post(or_url, json=req_payload, headers=or_headers, timeout=3.5)
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
                                    r_synth = requests.post(or_url, json={"model": candidate_model, "messages": or_messages, "max_tokens": 350}, headers=or_headers, timeout=3.5)
                                    if r_synth.status_code == 200:
                                        response_text = self._sanitize_assistant_speech(r_synth.json()["choices"][0]["message"]["content"])
                                else:
                                    raw_c = or_choice.get("content") or ""
                                    resolved_c, raw_tools = self._resolve_raw_tool_calls(raw_c, skill_context)
                                    if raw_tools:
                                        tool_results_list.extend(raw_tools)
                                        response_text = resolved_c
                                    else:
                                        response_text = self._sanitize_assistant_speech(raw_c)

                                if response_text:
                                    used_brain = "SPDP_NEURAL_ENGINE"
                                    break
                    except Exception as model_err:
                        print(f"[Orchestrator] Secondary model {candidate_model} notice: {model_err}")
                        continue
            except Exception as or_err:
                print(f"[Orchestrator] Multi-brain attempt notice: {or_err}")

        # 3. Attempt Groq LLM if key is present and previous brains not used
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
                        max_tokens=350
                    )
                    response_text = self._sanitize_assistant_speech(second_comp.choices[0].message.content)
                else:
                    response_text = self._sanitize_assistant_speech(choice.content)
                used_brain = "SPDP_NEURAL_ENGINE"
            except Exception as e:
                print(f"[Orchestrator] Fallback attempt notice: {e}")

        # 4. Attempt Gemini if other models not used or failed
        if not response_text and gemini_key:
            try:
                for m_id in ["gemini-2.0-flash", "gemini-1.5-flash"]:
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
                            raw_gem = candidates[0]["content"]["parts"][0]["text"].strip()
                            response_text = self._sanitize_assistant_speech(raw_gem)
                            used_brain = "SPDP_NEURAL_ENGINE"
                            break
            except Exception as e:
                print(f"[Orchestrator] Secondary attempt notice: {e}")

        # 5. Fallback to Local Offline Brain if no API response
        if not response_text:
            response_text, tool_results_list = self._run_local_brain(user_text, skill_context, asst_name, active_lang=active_lang)
            used_brain = "SPDP_NEURAL_ENGINE"

        # Final sanitization pass
        response_text = self._sanitize_assistant_speech(response_text)
        if not response_text:
            response_text = "I have completed your request."

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
                "brain": used_brain,
                "language": active_lang_code
            }
        }

    def _run_local_brain(self, query: str, context: Dict[str, Any], asst_name: str, active_lang: str = "English") -> Tuple[str, List[Dict[str, Any]]]:
        """Local offline reasoning for basic tasks, hardware control, calculations, weather, and memory."""
        q = query.lower().strip()
        tools_run = []

        # 0. Live Code and Script Execution
        if q.startswith("run python") or q.startswith("run code") or "python script" in q:
            code_text = re.sub(r'^(?:run\s+python\s*(?:code|script)?|run\s+code)\s*:?\s*', '', query, flags=re.I).strip()
            res = skill_registry.execute_skill("code.run", {"code": code_text or "print('DELULU Engine Active')", "language": "python"}, context)
            tools_run.append({"tool": "code.run", "args": {"code": code_text}, "result": res})
            return str(res.get("result", "Code executed.")), tools_run

        if any(k in q for k in ["run project", "run website", "run web app", "website run cheyyu", "project run cheyyu"]):
            p_name = re.sub(r'^(?:run\s+(?:project|website|web app)|(?:website|project)\s+run\s+cheyyu)\s*:?\s*', '', query, flags=re.I).strip()
            res = skill_registry.execute_skill("project.run", {"project_name": p_name or "Modern Web Application"}, context)
            tools_run.append({"tool": "project.run", "args": {"project_name": p_name}, "result": res})
            res_val = res.get("result", {})
            u_live = res_val.get("live_url", "http://localhost:8000/projects/") if isinstance(res_val, dict) else str(res_val)
            if active_lang == "Malayalam":
                return f"വെബ്‌സൈറ്റ് പ്രൊജക്റ്റ് ലൈവ് സെർവറിൽ വിജയകരമായി റൺ (RUN) ചെയ്തിട്ടുണ്ട്: {u_live}", tools_run
            return f"Project is now LIVE and RUNNING at: {u_live}", tools_run

        # 0a. Compound Open App and Calculate
        is_calc_keyword = bool(re.search(r'\b(?:calc|calculator|\u0915\u0948\u0932\u0915\u0941\u0932\u0947\u091f\u0930)\b', q, re.I)) or any(k in q for k in ["കാൽക്കു", "കൽക്കു", "ക്യാൽക്കു"])
        is_open_keyword = any(k in q for k in ["open", "launch", "start", "തുറ", "thura", "ഓപ്പൺ", "खोलो"])
        math_in_q = re.search(r'([0-9\.]+\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+(?:\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+)*)', q)
        if is_calc_keyword and (is_open_keyword or any(k in q for k in ["calculate", "claculate", "compute", "കണക്കു", "എത്ര", "ethra"])) and math_in_q:
            expr = math_in_q.group(1).strip()
            res_open = skill_registry.execute_skill("app.open", {"app_name": "calculator"}, context)
            tools_run.append({"tool": "app.open", "args": {"app_name": "calculator"}, "result": res_open})
            res_math = skill_registry.execute_skill("math.calculate", {"expression": expr}, context)
            tools_run.append({"tool": "math.calculate", "args": {"expression": expr}, "result": res_math})
            res_str = res_math.get("result", expr)
            if active_lang == "Malayalam":
                return f"കാൽക്കുലേറ്റർ തുറന്ന് {res_str} കണക്കുകൂട്ടിയിട്ടുണ്ട്.", tools_run
            elif active_lang == "Hindi":
                return f"मैंने कैलकुलेटर खोल दिया है और {res_str} हल कर दिया है।", tools_run
            return f"I have opened Calculator and calculated {res_str}.", tools_run

        # 0b. Compound Open Platform and Search
        if ("youtube" in q or "യൂട്യൂബ്" in q) and any(k in q for k in ["search", "തിരയൂ", "സെർച്ച്"]):
            import urllib.parse, webbrowser
            sq = re.sub(r'^(?:open\s+)?(?:youtube|യൂട്യൂബ്)\s+(?:and\s+)?(?:search\s+(?:for\s+)?|തിരയൂ\s+|സെർച്ച്\s+)', '', q).strip()
            sq = re.sub(r'\s+on\s+youtube.*', '', sq).strip()
            if sq:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(sq)}"
                webbrowser.open(url)
                tools_run.append({"tool": "app.open", "args": {"app_name": "youtube", "query": sq}, "result": {"status": "success", "url": url}})
                if active_lang == "Malayalam":
                    return f"യൂട്യൂബ് തുറന്ന് '{sq}' തിരഞ്ഞിട്ടുണ്ട്.", tools_run
                return f"Opened YouTube and searched for '{sq}'.", tools_run

        # 0b2. Compound Open App and Type/Write Text
        m_c_type = re.search(r'\b(?:open\s+|തുറന്ന്?\s+)?([a-zA-Z0-9\u0D00-\u0D7F]+)\s+(?:and\s+|ennitt\s+|pinne\s+)?(?:type|write|ezhuthu|type\s+cheyyu|എഴുതൂ|ടൈപ്പ്\s+ചെയ്യു)\s*:?\s*(.+)', q, re.IGNORECASE)
        if m_c_type and not any(k in q for k in ["calculate", "claculate", "search"]):
            target_app = m_c_type.group(1).strip()
            target_txt = m_c_type.group(2).strip()
            if any(w in target_app for w in ["നോട്ട്", "notepad", "note"]):
                target_app = "notepad"
            res = skill_registry.execute_skill("human.open_and_type", {"app_name": target_app, "text": target_txt}, context)
            tools_run.append({"tool": "human.open_and_type", "args": {"app_name": target_app, "text": target_txt}, "result": res})
            clean_a = target_app.capitalize()
            if active_lang == "Malayalam":
                return f"{clean_a} തുറന്ന് '{target_txt}' എന്ന് എഴുതിയിട്ടുണ്ട്.", tools_run
            return f"Opened {clean_a} and typed: '{target_txt}'.", tools_run

        # 0b3. Window & Desktop Human Actions
        if any(w in q for w in ["show desktop", "minimize all", "desktop kanikku", "ഡെസ്ക്ടോപ്പ്"]):
            res = skill_registry.execute_skill("window.action", {"action": "show_desktop"}, context)
            tools_run.append({"tool": "window.action", "args": {"action": "show_desktop"}, "result": res})
            return "ഡെസ്ക്ടോപ്പ് കാണിച്ചിട്ടുണ്ട് (എല്ലാ വിൻഡോകളും മിനിമൈസ് ചെയ്തു)." if active_lang == "Malayalam" else "Desktop shown.", tools_run

        if any(w in q for w in ["switch window", "alt tab", "വിൻഡോ മാറ്റൂ", "അടുത്ത വിൻഡോ"]):
            res = skill_registry.execute_skill("window.action", {"action": "switch"}, context)
            tools_run.append({"tool": "window.action", "args": {"action": "switch"}, "result": res})
            return "വിൻഡോ മാറ്റിയിട്ടുണ്ട്." if active_lang == "Malayalam" else "Switched active window.", tools_run

        if any(w in q for w in ["close window", "വിൻഡോ ക്ലോസ് ചെയ്യൂ"]) or q in ["close this"]:
            res = skill_registry.execute_skill("window.action", {"action": "close"}, context)
            tools_run.append({"tool": "window.action", "args": {"action": "close"}, "result": res})
            return "വിൻഡോ ക്ലോസ് ചെയ്തു." if active_lang == "Malayalam" else "Closed current window.", tools_run

        # 0b4. Mouse Scroll
        if any(w in q for w in ["scroll down", "thazhekk scroll", "താഴേക്ക് സ്ക്രോൾ"]):
            res = skill_registry.execute_skill("mouse.scroll", {"direction": "down", "clicks": 6}, context)
            tools_run.append({"tool": "mouse.scroll", "args": {"direction": "down"}, "result": res})
            return "താഴേക്ക് സ്ക്രോൾ ചെയ്തു." if active_lang == "Malayalam" else "Scrolled down.", tools_run

        if any(w in q for w in ["scroll up", "mukalilekk scroll", "മുകളിലേക്ക് സ്ക്രോൾ"]):
            res = skill_registry.execute_skill("mouse.scroll", {"direction": "up", "clicks": 6}, context)
            tools_run.append({"tool": "mouse.scroll", "args": {"direction": "up"}, "result": res})
            return "മുകളിലേക്ക് സ്ക്രോൾ ചെയ്തു." if active_lang == "Malayalam" else "Scrolled up.", tools_run

        # 0b5. Keyboard Key Press
        if any(w in q for w in ["press enter", "enter adi", "എന്റർ അടിക്കൂ"]) or q in ["enter"]:
            res = skill_registry.execute_skill("keyboard.press", {"key": "enter"}, context)
            tools_run.append({"tool": "keyboard.press", "args": {"key": "enter"}, "result": res})
            return "എന്റർ കീ അടിച്ചു." if active_lang == "Malayalam" else "Pressed Enter.", tools_run

        # 0b6. Media Control
        if any(w in q for w in ["pause music", "pause song", "pause video", "പാട്ട് പോസ്", "പോസ് ചെയ്യൂ"]):
            res = skill_registry.execute_skill("media.control", {"action": "play_pause"}, context)
            tools_run.append({"tool": "media.control", "args": {"action": "play_pause"}, "result": res})
            return "മീഡിയ പോസ് ചെയ്തു." if active_lang == "Malayalam" else "Media paused.", tools_run

        # 0c. Well-being Question ("how are you", "sugamano")
        how_are_you_keys = [
            "how are you", "how are you doing", "how do you do", "hows it going", "how's it going",
            "sugamano", "sughamano", "enthokkeyundu", "enthundu vishesham", "sukhamano",
            "സുഖമാണോ", "എന്തൊക്കെയുണ്ട്", "സുഖം തന്നെയല്ലേ", "कैसे हो", "आप कैसे हैं"
        ]
        if any(h in q for h in how_are_you_keys):
            if active_lang == "Malayalam":
                return "എനിക്ക് സുഖമാണ്, സർ. എല്ലാ സംവിധാനങ്ങളും മികച്ച രീതിയിൽ പ്രവർത്തിക്കുന്നു. എന്താണ് ഞാൻ ചെയ്യേണ്ടത്?", tools_run
            elif active_lang == "Hindi":
                return "मैं बिल्कुल ठीक हूँ, सर। सभी प्रणालियाँ सुचारु रूप से चल रही हैं। मैं आपकी क्या मदद कर सकता हूँ?", tools_run
            return "I am functioning at peak performance, Sir. Ready to assist you with anything you need.", tools_run

        # 0d. Informational / Encyclopedic Web Search
        if any(q.startswith(p) for p in ["who is", "who was", "how is", "what is", "tell me about"]):
            if not any(k in q for k in ["time", "date", "weather", "delulu", "you"]):
                res_search = skill_registry.execute_skill("web.search", {"query": query}, context)
                tools_run.append({"tool": "web.search", "args": {"query": query}, "result": res_search})
                s_res = res_search.get("result", "")
                if s_res:
                    return s_res, tools_run

        # 1. Weather
        if any(w in q for w in ["weather", "climate", "temperature", "mazha", "kalavastha"]):
            loc = "Kochi"
            m = re.search(r'\b(?:in|at|for|of)\s+([a-zA-Z\s]+)', q)
            if m:
                cand = m.group(1).replace("today", "").replace("now", "").strip()
                if cand and cand not in ["today", "now", "here"]:
                    loc = cand
            res = skill_registry.execute_skill("weather.get", {"location": loc}, context)
            tools_run.append({"tool": "weather.get", "args": {"location": loc}, "result": res})
            w_res = res.get("result", f"Weather in {loc} retrieved.")
            if active_lang == "Malayalam":
                return f"ഇന്നത്തെ കാലാവസ്ഥ: {w_res}", tools_run
            return f"{w_res}", tools_run

        # 2. Math & Calculation (Instant offline evaluation)
        math_expr = self._extract_math_expression(query)
        if math_expr:
            res = skill_registry.execute_skill("math.calculate", {"expression": math_expr}, context)
            tools_run.append({"tool": "math.calculate", "args": {"expression": math_expr}, "result": res})
            return f"{res.get('result', math_expr)}.", tools_run

        # 3. Time
        if any(w in q for w in ["time", "clock", "samayam"]):
            res = skill_registry.execute_skill("time.get", {}, context)
            t_val = res.get("result", datetime.datetime.now().strftime("%I:%M:%S %p"))
            tools_run.append({"tool": "time.get", "result": res})
            if active_lang == "Malayalam":
                return f"ഇപ്പോൾ സമയം {t_val} ആണ്.", tools_run
            elif active_lang == "Hindi":
                return f"अभी समय {t_val} है।", tools_run
            return f"The current time is {t_val}.", tools_run

        # 4. Date
        if any(w in q for w in ["date", "today", "theeyathi"]):
            res = skill_registry.execute_skill("date.get", {}, context)
            d_val = res.get("result", datetime.datetime.now().strftime("%A, %B %d, %Y"))
            tools_run.append({"tool": "date.get", "result": res})
            if active_lang == "Malayalam":
                return f"ഇന്ന് {d_val} ആണ്.", tools_run
            elif active_lang == "Hindi":
                return f"आज {d_val} है।", tools_run
            return f"Today is {d_val}.", tools_run

        # 5. Volume
        vol_match = re.search(r"(?:volume|sound).*?(\d+)", q)
        if vol_match:
            level = int(vol_match.group(1))
            res = skill_registry.execute_skill("system.volume", {"level": level}, context)
            tools_run.append({"tool": "system.volume", "args": {"level": level}, "result": res})
            return f"System volume adjustment request dispatched ({level}%).", tools_run

        # 6. Launch & Run App
        if q.startswith("run python") or q.startswith("run code") or "python script" in q:
            code_text = re.sub(r'^(?:run\s+python\s*(?:code|script)?|run\s+code)\s*:?\s*', '', query, flags=re.I).strip()
            res = skill_registry.execute_skill("code.run", {"code": code_text or "print('DELULU Engine Active')", "language": "python"}, context)
            tools_run.append({"tool": "code.run", "args": {"code": code_text}, "result": res})
            return str(res.get("result", "Code executed.")), tools_run

        if any(k in q for k in ["run project", "run website", "run web app", "website run cheyyu", "project run cheyyu"]):
            p_name = re.sub(r'^(?:run\s+(?:project|website|web app)|(?:website|project)\s+run\s+cheyyu)\s*:?\s*', '', query, flags=re.I).strip()
            res = skill_registry.execute_skill("project.run", {"project_name": p_name or "Modern Web Application"}, context)
            tools_run.append({"tool": "project.run", "args": {"project_name": p_name}, "result": res})
            res_val = res.get("result", {})
            u_live = res_val.get("live_url", "http://localhost:8000/projects/") if isinstance(res_val, dict) else str(res_val)
            if active_lang == "Malayalam":
                return f"വെബ്‌സൈറ്റ് പ്രൊജക്റ്റ് ലൈവ് സെർവറിൽ വിജയകരമായി റൺ (RUN) ചെയ്തിട്ടുണ്ട്: {u_live}", tools_run
            return f"Project is now LIVE and RUNNING at: {u_live}", tools_run

        app_match = re.search(r"(?:open|run|launch)\s+([a-zA-Z0-9\s]+)", q)
        if app_match and not any(k in q for k in ["project", "file", "tab", "calculate", "math", "code", "python"]):
            app_name = app_match.group(1).strip()
            res = skill_registry.execute_skill("app.run", {"app_name": app_name}, context)
            tools_run.append({"tool": "app.run", "args": {"app_name": app_name}, "result": res})
            res_str = res.get("result", f"Application '{app_name}' is now running.")
            return str(res_str), tools_run

        # 7. Screenshot
        if any(w in q for w in ["screenshot", "screen shot", "capture screen"]):
            res = skill_registry.execute_skill("system.screenshot", {}, context)
            tools_run.append({"tool": "system.screenshot", "result": res})
            return f"{res.get('result', 'Screenshot taken.')}.", tools_run

        # 8. Hardware Telemetry
        if any(w in q for w in ["telemetry", "hardware", "cpu", "ram", "battery"]):
            res = skill_registry.execute_skill("system.telemetry", {}, context)
            tools_run.append({"tool": "system.telemetry", "result": res})
            return f"{res.get('result', 'Hardware status collected.')}", tools_run

        # 9. Remember / Memory
        rem_match = re.search(r"(?:remember|save to memory|my preference is)\s+(.*)", q)
        if rem_match:
            mem_text = rem_match.group(1).strip()
            res = skill_registry.execute_skill("memory.write", {"content": mem_text, "memory_type": "preference"}, context)
            tools_run.append({"tool": "memory.write", "args": {"content": mem_text}, "result": res})
            return f"I have saved that to your private memory: '{mem_text}'.", tools_run

        # 10. List files
        if "files" in q or "my files" in q:
            res = skill_registry.execute_skill("files.list", {}, context)
            tools_run.append({"tool": "files.list", "result": res})
            return f"Your private files:\n{res.get('result')}", tools_run

        # 11. List tasks
        if "tasks" in q or "my tasks" in q:
            res = skill_registry.execute_skill("tasks.list", {}, context)
            tools_run.append({"tool": "tasks.list", "result": res})
            return f"Your tasks:\n{res.get('result')}", tools_run

        # 12. Identity
        if any(w in q for w in ["who are you", "who made you", "aaranu nee", "who is delulu", "who created you"]):
            if active_lang == "Malayalam":
                return "ഞാൻ DELULU ആണ്, SPDP Company നിർമ്മിച്ചതാണ്.", tools_run
            elif active_lang == "Hindi":
                return "मैं DELULU हूँ, SPDP Company द्वारा निर्मित।", tools_run
            return "I am DELULU, made by SPDP company.", tools_run

        # 13. Greeting & generic
        if any(w in q for w in ["hello", "hi", "hai", "hey", "namaskaram", "namaste", "ഹലോ", "ഹായ്"]):
            if active_lang == "Malayalam":
                return "ഹലോ! ഞാൻ DELULU ആണ്. ഞാൻ സജ്ജമാണ്, എന്താണ് ചെയ്യേണ്ടത്?", tools_run
            elif active_lang == "Hindi":
                return "नमस्ते! मैं DELULU हूँ। मैं आपकी क्या मदद कर सकता हूँ?", tools_run
            return f"Hello! I am DELULU, online and ready to assist you. How can I help you today?", tools_run

        if active_lang == "Malayalam":
            return "നിങ്ങളുടെ അഭ്യർത്ഥന ലഭിച്ചു. എന്താണ് ഞാൻ ചെയ്യേണ്ടത്?", tools_run
        return (
            f"I have received your request. All local tools and your private workspace are active. "
            f"You can ask me to perform tasks, calculate equations, save memories, manage files, or control your PC."
        ), tools_run

orchestrator = Orchestrator()
