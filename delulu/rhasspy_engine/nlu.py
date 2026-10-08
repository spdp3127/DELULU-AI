import os
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import rhasspynlu

@dataclass
class RhasspyEntity:
    name: str
    value: Any

@dataclass
class RhasspyIntent:
    name: str
    confidence: float
    slots: Dict[str, Any] = field(default_factory=dict)
    text: str = ""

class RhasspyNLUEngine:
    """
    Rhasspy Natural Language Understanding (NLU) Engine.
    Parses human language into structured intents and slot entities
    using Rhasspy's JSGF grammar graph and fuzzy matcher.
    """
    def __init__(self, ini_path: Optional[str] = None):
        self.ini_path = ini_path or os.path.join(os.path.dirname(__file__), "sentences.ini")
        self.graph = None
        self._load_grammar()

    def _load_grammar(self):
        try:
            if os.path.exists(self.ini_path):
                with open(self.ini_path, "r", encoding="utf-8") as f:
                    ini_content = f.read()
                intents = rhasspynlu.parse_ini(ini_content)
                self.graph = rhasspynlu.intents_to_graph(intents)
        except Exception as e:
            print(f"[RhasspyNLU] Warning loading grammar graph: {e}")

    def recognize(self, text: str) -> Optional[RhasspyIntent]:
        """
        Recognize intent and extract slot entities from human input.
        Returns RhasspyIntent if matched, otherwise None.
        """
        if not text:
            return None

        clean_text = text.strip()
        q_lower = clean_text.lower()

        # 1. Attempt strict Rhasspy Graph Recognition
        if self.graph:
            try:
                recognitions = rhasspynlu.recognize(q_lower, self.graph)
                if recognitions:
                    rec = recognitions[0]
                    slots = {e.entity: e.value for e in rec.entities}
                    return RhasspyIntent(
                        name=rec.intent.name,
                        confidence=1.0,
                        slots=slots,
                        text=clean_text
                    )
            except Exception:
                pass

        # 2. Resilient Rhasspy Fuzzy / Pattern Matching Fallback
        # A. Open App
        app_match = re.search(r'\b(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9\s]+)', q_lower)
        app_malayalam_match = re.search(r'\b([a-zA-Z0-9]+)\s+(?:thura|open\s+cheyyu|thuranu\s+tha)\b', q_lower)
        if (app_match or app_malayalam_match) and not any(k in q_lower for k in ["calculate", "math", "tab", "file"]):
            app_name = (app_match.group(1) if app_match else app_malayalam_match.group(1)).strip()
            # Clean app name
            app_name = re.sub(r'\s+app\b', '', app_name)
            return RhasspyIntent(
                name="OpenApp",
                confidence=0.95,
                slots={"app_name": app_name},
                text=clean_text
            )

        # B. Change Volume
        vol_match = re.search(r'(?:volume|sound).*?(\d+)', q_lower)
        if vol_match:
            vol_val = int(vol_match.group(1))
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.98,
                slots={"volume": vol_val},
                text=clean_text
            )
        if any(w in q_lower for w in ["mute", "silence sound", "mute volume", "sound mute cheyyu", "volume mute cheyyu"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 0},
                text=clean_text
            )
        if any(w in q_lower for w in ["volume kootu", "volume koottu", "sound koottu", "volume increase", "turn up volume"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 80},
                text=clean_text
            )
        if any(w in q_lower for w in ["volume kura", "volume kurakku", "sound kurakku", "volume decrease", "turn down volume"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 30},
                text=clean_text
            )

        # C. Take Screenshot
        if any(w in q_lower for w in ["screenshot", "screen shot", "snapshot", "capture screen", "screenshot edukk", "screenshot eduthu tha"]):
            return RhasspyIntent(
                name="TakeScreenshot",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # D. Lock Screen
        if any(w in q_lower for w in ["lock screen", "lock the screen", "lock pc", "lock computer", "lock workstation", "screen lock cheyyu", "pc lock cheyyu"]):
            return RhasspyIntent(
                name="LockScreen",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # E. System Telemetry
        if any(w in q_lower for w in ["telemetry", "hardware status", "system status", "cpu usage", "ram usage", "battery level", "system info"]):
            return RhasspyIntent(
                name="SystemTelemetry",
                confidence=0.95,
                slots={},
                text=clean_text
            )

        # F. Get Time
        if bool(re.search(r'\b(?:what\s+(?:is\s+)?(?:the\s+)?time|what\s+time\s+is\s+it|current\s+time|tell\s+(?:me\s+)?(?:the\s+)?time|samayam\s+parayu|ippol\s+samayam|samayam)\b', q_lower)) or q_lower in ['time', 'clock', 'what time']:
            return RhasspyIntent(
                name="GetTime",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # G. Get Date
        if bool(re.search(r'\b(?:what\s+(?:is\s+)?(?:the\s+)?date|what\s+date\s+is\s+it|today[\'’]?s?\s+date|what\s+is\s+today|theeyathi\s+parayu|innathe\s+theeyathi|theeyathi)\b', q_lower)) or q_lower in ['date', 'today']:
            return RhasspyIntent(
                name="GetDate",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # H. Math Calculation
        # Examples: "calculate 5+5", "what is 100 * 25", "now calculate 5+5", "5+5", "5 + 5 എത്രയാണ്", "5+5 ethrayanu"
        math_regex = r'(?:(?:now\s+)?calculate|compute|solve|what\s+is|value\s+of)?\s*([0-9\.]+\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+(?:\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+)*)'
        norm_math = q_lower.replace('times', '*').replace('plus', '+').replace('minus', '-').replace('divided by', '/')
        m_calc = re.search(math_regex, norm_math)
        if m_calc and not re.search(r'^\s*open\b', q_lower):
            expr = m_calc.group(1).strip()
            if re.search(r'[\+\-\*\/\^xX÷%]', expr) and re.search(r'\d', expr):
                return RhasspyIntent(
                    name="CalculateMath",
                    confidence=0.98,
                    slots={"expression": expr},
                    text=clean_text
                )

        # I. Switch Language
        lang_keys = "hindi|malayalam|japanese|japanees|chinese|chinees|korean|korea|english|spanish|french|german|arabic|tamil"
        m_lang = re.search(rf'(?:anikk|enikku?)\s+({lang_keys})(?:il|yil|athil)?\s+(?:parannu?|paranju?)\s+tha', q_lower) or \
                 re.search(rf'\b(?:speak|talk|reply|converse|switch|change|tell me)\s+(?:to\s+|in\s+)?({lang_keys})\b', q_lower) or \
                 re.search(rf'\b({lang_keys})(?:il|yil|athil)?\s+(?:parayu|paranjolu|samsarikku|bolo)\b', q_lower) or \
                 re.search(rf'\b({lang_keys})\s+me\s+bolo\b', q_lower)
        if m_lang:
            target_l = m_lang.group(1)
            return RhasspyIntent(
                name="SwitchLanguage",
                confidence=0.99,
                slots={"language": target_l},
                text=clean_text
            )

        # J. Identity
        identity_keys = [
            "who are you", "who made you", "who created you", "who is delulu", "what is your name",
            "aaranu nee", "nee aaranu", "ninne aara", "aara undakki", "undakkiyath", "undakkiyathu",
            "create cheytha", "ninne undakkiya"
        ]
        if any(k in q_lower for k in identity_keys) or any(k in clean_text for k in ["ആരാണ്", "ഉണ്ടാക്കിയത്", "ഉണ്ടാക്കിയ"]):
            return RhasspyIntent(
                name="Identity",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        return None

rhasspy_nlu = RhasspyNLUEngine()
