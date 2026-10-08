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

APP_ALIASES = {
    "calculator": "calculator",
    "calc": "calculator",
    "കാൽക്കുലേറ്റർ": "calculator",
    "കൽക്കുലേറ്റർ": "calculator",
    "कैलकुलेटर": "calculator",
    "notepad": "notepad",
    "note": "notepad",
    "നോട്ട്പാഡ്": "notepad",
    "नोटपैड": "notepad",
    "chrome": "chrome",
    "browser": "chrome",
    "ക്രോം": "chrome",
    "ബ്രൗസർ": "chrome",
    "क्रोम": "chrome",
    "cmd": "cmd",
    "terminal": "terminal",
    "powershell": "powershell",
    "പവർഷെൽ": "powershell",
    "spotify": "spotify",
    "സ്പോട്ടിഫൈ": "spotify",
    "explorer": "explorer",
    "code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "settings": "settings",
    "സെറ്റിംഗ്സ്": "settings"
}

class RhasspyNLUEngine:
    """
    Rhasspy Natural Language Understanding (NLU) Engine.
    Parses human language into structured intents and slot entities
    using Rhasspy's JSGF grammar graph and high-performance multilingual matcher.
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

        # 1. Attempt strict Rhasspy Graph Recognition (only high-confidence full match)
        if self.graph:
            try:
                recognitions = rhasspynlu.recognize(q_lower, self.graph)
                if recognitions:
                    rec = recognitions[0]
                    # Verify positive confidence and full utterance coverage
                    if rec.intent.confidence > 0 and (rec.text == q_lower or abs(len(rec.text) - len(q_lower)) <= 2):
                        slots = {e.entity: e.value for e in rec.entities}
                        return RhasspyIntent(
                            name=rec.intent.name,
                            confidence=rec.intent.confidence,
                            slots=slots,
                            text=clean_text
                        )
            except Exception:
                pass

        # 2. Resilient Multilingual Slot & Intent Extraction
        # Strip wake word / greeting prefixes to parse inner intent: "hey delulu open calculator" -> "open calculator"
        q_cmd = re.sub(r'^(?:hey|hi|hello|hai|ok|okay)?\s*(?:delulu|jarvis|gemini)?[\s,:\.\?!]+', '', q_lower).strip()
        if not q_cmd:
            q_cmd = q_lower

        # A. Open Desktop App
        # English: "open calculator", "launch notepad", "start chrome"
        # Malayalam: "കാൽക്കുലേറ്റർ തുറക്കൂ", "നോട്ട്പാഡ് ഓപ്പൺ ചെയ്യൂ", "calculator thura", "open calc"
        # Hindi: "कैलकुलेटर खोलो", "नोटपैड खोलो"
        app_match = re.search(r'\b(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9\u0D00-\u0D7F\u0900-\u097F\s]+)', q_cmd)
        app_mal_match = re.search(r'([a-zA-Z0-9\u0D00-\u0D7F]+)\s+(?:തുറക്കൂ|തുറക്കുക|തുറന്ന്\s+തരൂ|തുറ|ഓപ്പൺ\s+ചെയ്യു|ഓപ്പൺ\s+ചെയ്യുക|thura|open\s+cheyyu|thuranu\s+tha)', q_cmd)
        app_hi_match = re.search(r'([a-zA-Z0-9\u0900-\u097F]+)\s+(?:खोलो|खोलिए|चालू\s+करो)', q_cmd)

        if (app_match or app_mal_match or app_hi_match) and not any(k in q_cmd for k in ["calculate", "math", "tab", "file"]):
            raw_app = (app_match.group(1) if app_match else (app_mal_match.group(1) if app_mal_match else app_hi_match.group(1))).strip()
            raw_app = re.sub(r'\s+app\b', '', raw_app).strip()
            canonical_app = APP_ALIASES.get(raw_app, raw_app)
            return RhasspyIntent(
                name="OpenApp",
                confidence=0.98,
                slots={"app_name": canonical_app},
                text=clean_text
            )

        # B. Change Volume
        vol_match = re.search(r'(?:volume|sound|ശബ്ദം|വോളിയം|आवाज़).*?(\d+)', q_cmd)
        if vol_match:
            vol_val = int(vol_match.group(1))
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.98,
                slots={"volume": vol_val},
                text=clean_text
            )
        if any(w in q_cmd for w in ["mute", "silence sound", "mute volume", "sound mute cheyyu", "മ്യൂട്ട്", "മ്യൂട്ട് ചെയ്യൂ", "म्यूट करो"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 0},
                text=clean_text
            )
        if any(w in q_cmd for w in ["volume kootu", "volume koottu", "sound koottu", "volume increase", "turn up volume", "വോളിയം കൂട്ടൂ", "ശബ്ദം കൂട്ടൂ", "आवाज़ बढ़ाओ"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 80},
                text=clean_text
            )
        if any(w in q_cmd for w in ["volume kura", "volume kurakku", "sound kurakku", "volume decrease", "turn down volume", "വോളിയം കുറയ്ക്കൂ", "ശബ്ദം കുറയ്ക്കൂ", "आवाज़ कम करो"]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.95,
                slots={"volume": 30},
                text=clean_text
            )

        # C. Take Screenshot
        if any(w in q_cmd for w in [
            "screenshot", "screen shot", "snapshot", "capture screen",
            "screenshot edukk", "screenshot eduthu tha", "സ്ക്രീൻഷോട്ട്", "സ്ക്രീൻഷോട്ട് എടുക്കൂ", "സ്ക്രീൻഷോട്ട് എടുക്കുക", "स्क्रीनशॉट लो"
        ]):
            return RhasspyIntent(
                name="TakeScreenshot",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # D. Lock Screen
        if any(w in q_cmd for w in [
            "lock screen", "lock the screen", "lock pc", "lock computer", "lock workstation",
            "screen lock cheyyu", "pc lock cheyyu", "സ്ക്രീൻ ലോക്ക് ചെയ്യൂ", "കമ്പ്യൂട്ടർ ലോക്ക് ചെയ്യൂ", "स्क्रीन लॉक करो"
        ]):
            return RhasspyIntent(
                name="LockScreen",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # E. System Telemetry
        if any(w in q_cmd for w in [
            "telemetry", "hardware status", "system status", "cpu usage", "ram usage", "battery level", "system info",
            "ഹാർഡ്വെയർ", "സിസ്റ്റം സ്റ്റാറ്റസ്"
        ]):
            return RhasspyIntent(
                name="SystemTelemetry",
                confidence=0.95,
                slots={},
                text=clean_text
            )

        # F. Get Time (English, Malayalam, Hindi)
        time_triggers = [
            "what time is it", "what is the time", "current time", "tell me the time",
            "samayam", "samayam ethrayayi", "samayam parayu", "ippol samayam",
            "സമയം", "ഇപ്പോൾ സമയം", "സമയം എത്രയായി", "സമയം എത്ര", "സമയം പറയൂ",
            "समय क्या है", "कितने बजे हैं"
        ]
        if any(t in q_cmd for t in time_triggers) or q_cmd in ['time', 'clock', 'what time']:
            return RhasspyIntent(
                name="GetTime",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # G. Get Date (English, Malayalam, Hindi)
        date_triggers = [
            "what date is it", "what is the date", "what is today", "today's date", "todays date",
            "theeyathi", "theeyathi parayu", "innathe theeyathi",
            "തീയതി", "ഇന്നത്തെ തീയതി", "തിയതി", "ഇന്ന് എന്ത് തീയതി",
            "तारीख क्या है", "आज कौन सी तारीख है"
        ]
        if any(d in q_cmd for d in date_triggers) or q_cmd in ['date', 'today']:
            return RhasspyIntent(
                name="GetDate",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # H. Math Calculation (Zero-latency offline arithmetic)
        # Examples: "calculate 5+5", "what is 100 * 25", "now calculate 5+5", "5+5", "5 + 5 എത്രയാണ്", "5+5 ethrayanu"
        math_regex = r'(?:(?:now\s+)?calculate|compute|solve|what\s+is|value\s+of)?\s*([0-9\.]+\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+(?:\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+)*)'
        norm_math = q_cmd.replace('times', '*').replace('plus', '+').replace('minus', '-').replace('divided by', '/')
        m_calc = re.search(math_regex, norm_math)
        if m_calc and not re.search(r'^\s*open\b', q_cmd):
            expr = m_calc.group(1).strip()
            if re.search(r'[\+\-\*\/\^xX÷%]', expr) and re.search(r'\d', expr):
                return RhasspyIntent(
                    name="CalculateMath",
                    confidence=0.98,
                    slots={"expression": expr},
                    text=clean_text
                )

        # I. Live Weather Query (Placed BEFORE Greeting/Identity)
        if any(w in q_cmd for w in ["weather", "temperature", "climate", "kalavastha", "kaalavastha", "mazha", "കാലാവസ്ഥ", "മഴ", "मौसम"]):
            loc = "Kochi"
            loc_match = re.search(r'\b(?:in|at|for|of)\s+([a-zA-Z\s]+)', q_cmd)
            mal_loc_match = re.search(r'([a-zA-Z\u0D00-\u0D7F]+)(?:യിലെ|ലെ)?\s*(?:കാലാവസ്ഥ|മഴ|weather)', q_cmd)
            if loc_match:
                cand = loc_match.group(1).replace("today", "").replace("now", "").strip()
                if cand and cand not in ["today", "now", "here"]:
                    loc = cand
            elif mal_loc_match:
                cand = mal_loc_match.group(1).strip()
                if cand and cand not in ["ഇന്നത്തെ", "ഇന്ന്", "ഇവിടെ"]:
                    loc = cand
            return RhasspyIntent(
                name="GetWeather",
                confidence=0.98,
                slots={"location": loc},
                text=clean_text
            )

        # J. Switch Language Request
        lang_keys = "hindi|malayalam|japanese|japanees|chinese|chinees|korean|korea|english|spanish|french|german|arabic|tamil"
        m_lang = re.search(rf'(?:anikk|enikku?)\s+({lang_keys})(?:il|yil|athil)?\s+(?:parannu?|paranju?)\s+tha', q_cmd) or \
                 re.search(rf'\b(?:speak|talk|reply|converse|switch|change|tell me)\s+(?:to\s+|in\s+)?({lang_keys})\b', q_cmd) or \
                 re.search(rf'\b({lang_keys})(?:il|yil|athil)?\s+(?:parayu|paranjolu|samsarikku|bolo)\b', q_cmd) or \
                 re.search(rf'\b({lang_keys})\s+me\s+bolo\b', q_cmd)
        if m_lang:
            target_l = m_lang.group(1)
            return RhasspyIntent(
                name="SwitchLanguage",
                confidence=0.99,
                slots={"language": target_l},
                text=clean_text
            )
        if "മലയാളത്തിൽ" in clean_text or "മലയാളം സംസാരിക്കൂ" in clean_text:
            return RhasspyIntent(name="SwitchLanguage", confidence=0.99, slots={"language": "malayalam"}, text=clean_text)
        if "ഇംഗ്ലീഷിൽ" in clean_text or "ഇംഗ്ലീഷ് സംസാരിക്കൂ" in clean_text:
            return RhasspyIntent(name="SwitchLanguage", confidence=0.99, slots={"language": "english"}, text=clean_text)
        if "ഹിന്ദിയിൽ" in clean_text or "हिंदी में" in clean_text:
            return RhasspyIntent(name="SwitchLanguage", confidence=0.99, slots={"language": "hindi"}, text=clean_text)

        # K. Identity (Identity check: Who made you?)
        identity_keys = [
            "who are you", "who made you", "who created you", "who is delulu", "what is your name",
            "aaranu nee", "nee aaranu", "ninne aara", "aara undakki", "undakkiyath", "undakkiyathu",
            "create cheytha", "ninne undakkiya", "ആരാണ് നീ", "നീ ആരാണ്", "ആരാണ് നിന്നെ ഉണ്ടാക്കിയത്",
            "तुम कौन हो", "किसने बनाया"
        ]
        if any(k in q_cmd for k in identity_keys) or any(k in clean_text for k in ["ആരാണ്", "ഉണ്ടാക്കിയത്"]):
            return RhasspyIntent(
                name="Identity",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # L. Pure Greeting (Strict: only matches when there is no substantive command/question)
        pure_greetings = [
            "hai", "hi", "hello", "hey", "hey delulu", "delulu", "jarvis",
            "good morning", "good afternoon", "good evening", "good day",
            "namaskaram", "namaste", "enthokkeyundu", "sugamano", "sughamano",
            "how are you", "what's up", "whats up",
            "ഹലോ", "ഹായ്", "നമസ്കാരം", "സുഖമാണോ", "എന്തൊക്കെയുണ്ട്",
            "नमस्ते", "नमस्कार", "कैसे हो"
        ]
        if q_cmd in pure_greetings or q_lower in pure_greetings:
            return RhasspyIntent(
                name="Greeting",
                confidence=0.99,
                slots={},
                text=clean_text
            )
        if re.match(r'^(?:hai|hi|hello|hey|yo|namaskaram|namaste)\s+(?:delulu|jarvis|there|friend|bro|buddy)?[\.!\?]*$', q_lower):
            return RhasspyIntent(
                name="Greeting",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # Not a system intent: return None so conversational brain / LLM answers
        return None

rhasspy_nlu = RhasspyNLUEngine()
