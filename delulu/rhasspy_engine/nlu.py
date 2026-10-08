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
    # Websites
    "youtube": "youtube",
    "യൂട്യൂബ്": "youtube",
    "google": "google",
    "ഗൂഗിൾ": "google",
    "whatsapp": "whatsapp",
    "വാട്ട്സ്ആപ്പ്": "whatsapp",
    "വാട്സാപ്പ്": "whatsapp",
    "gmail": "gmail",
    "github": "github",
    "chatgpt": "chatgpt",
    "instagram": "instagram",
    "twitter": "twitter",
    "x": "x",
    "reddit": "reddit",
    "netflix": "netflix",
    "amazon": "amazon",
    # Applications
    "calculator": "calculator",
    "calc": "calculator",
    "കാൽക്കുലേറ്റർ": "calculator",
    "കൽക്കുലേറ്റർ": "calculator",
    "कैलकुलेटर": "calculator",
    "notepad": "notepad",
    "note": "notepad",
    "notes": "notepad",
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
    "files": "explorer",
    "code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "settings": "settings",
    "സെറ്റിംഗ്സ്": "settings",
    "paint": "paint",
    "camera": "camera"
}

class RhasspyNLUEngine:
    """
    Rhasspy Natural Language Understanding (NLU) Engine.
    Parses human language into structured intents, compound actions, and slot entities
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

        # --- CODE & SCRIPT EXECUTION INTENTS ---
        # e.g. "run python print(500 * 2)", "run code print('hello')", "python -c 'print(1+1)'", "run powershell Get-Process"
        # Malayalam: "പൈത്തൺ റൺ ചെയ്യൂ print(500*2)", "കോഡ് റൺ ചെയ്യൂ"
        m_code = re.search(r'^\s*(?:run|execute)\s+(?:python|py|code|script|powershell)\s+(.+)', q_cmd, re.DOTALL | re.IGNORECASE) or \
                 re.search(r'^\s*python(?:\s+-c|\s+code)?\s+(.+)', q_cmd, re.DOTALL | re.IGNORECASE) or \
                 re.search(r'(?:പൈത്തൺ|കോഡ്)\s+(?:റൺ\s+ചെയ്യു|റൺ\s+ചെയ്യുക|എക്സിക്യൂട്ട്\s+ചെയ്യു)(?:\s+|:\s*)(.+)', q_cmd, re.DOTALL | re.IGNORECASE)
        if m_code:
            code_body = m_code.group(1).strip()
            if (code_body.startswith('"') and code_body.endswith('"')) or (code_body.startswith("'") and code_body.endswith("'")):
                code_body = code_body[1:-1].strip()
            lang = "powershell" if "powershell" in q_cmd.lower() else "python"
            return RhasspyIntent(
                name="RunCode",
                confidence=0.99,
                slots={"code": code_body, "language": lang},
                text=clean_text
            )

        # --- LIVE PROJECT / WEB APP RUN INTENT ---
        # e.g. "run project coffee-shop", "run website luxury-cars", "launch project my-site"
        # Malayalam: "പ്രോജക്റ്റ് റൺ ചെയ്യൂ", "വെബ്‌സൈറ്റ് റൺ ചെയ്യൂ"
        m_proj = re.search(r'^\s*(?:run|start|launch)\s+(?:project|website|site|web\s+app)\s+([a-zA-Z0-9_\-]+)', q_cmd, re.IGNORECASE) or \
                 re.search(r'(?:പ്രോജക്റ്റ്|വെബ്‌സൈറ്റ്|വെബ്സൈറ്റ്)\s+റൺ\s+ചെയ്യു(?:\s+|:\s*)([a-zA-Z0-9_\-]+)', q_cmd, re.IGNORECASE)
        if m_proj:
            return RhasspyIntent(
                name="RunProject",
                confidence=0.99,
                slots={"project_name": m_proj.group(1).strip()},
                text=clean_text
            )

        # --- COMPOUND INTENTS (MULTI-ACTION COMMANDS) ---
        # 1. Compound Open App and Calculate Math:
        # e.g. "open calculator and calculate 5+5", "open calculator and claculate 5+5", "open calc and 5+5"
        # Malayalam: "കാൽക്കുലേറ്റർ തുറന്ന് 5+5 കണക്കുകൂട്ടൂ", "കാൽക്കുലേറ്റർ തുറന്ന് 5+5 എത്രയാണ്", "calculator thurannu 5+5 calculate cheyyu"
        # Manglish: "calculator thurannu kanakku cheyyu", "calculator thurannu 5 plus 5", "calculator thura 10+20"
        is_negative_report = any(neg in q_cmd for neg in [
            "cheyyunnilla", "cheyyilla", "aakunnilla", "work aavunnilla", "not working", "working alla", 
            "പറ്റുന്നില്ല", "ചെയ്യുന്നില്ല", "ആകുന്നില്ല", "പ്രവർത്തിക്കുന്നില്ല", "parayumbol"
        ])
        
        is_calc_keyword = bool(re.search(r'\b(?:calc|calculator|\u0915\u0948\u0932\u0915\u0941\u0932\u0947\u091f\u0930)\b', q_cmd, re.I)) or any(k in q_cmd for k in ["കാൽക്കു", "കൽക്കു", "ക്യാൽക്കു"])
        is_open_keyword = any(k in q_cmd for k in [
            "open", "launch", "start", "run", "തുറ", "തുറന്ന്", "തുറക്കൂ", "thura", "thurannu", "thurann", "ഓപ്പൺ", "खोलो"
        ])
        is_calc_action = any(k in q_cmd for k in [
            "calculate", "claculate", "compute", "solve", "math", "arithmetic", 
            "kanakku", "kanakk", "kootu", "kootanam", "kurakku", "gunikku", "harikku",
            "കണക്കു", "കണക്കുകൂട്ടൂ", "കണക്കുകൂട്ടുക", "കണക്കുകൂട്ട്", "കൂട്ടുക", "കുറയ്ക്കുക", "ഗുണിക്കുക", "ഹരിക്കുക", "എത്ര", "ethra"
        ])

        if not is_negative_report and is_calc_keyword and (is_open_keyword or is_calc_action):
            # Normalize math expressions from text (words to symbols)
            norm_c = q_cmd
            norm_c = re.sub(r'\b(?:plus|kootanam|kootu|cherkku|add)\b|കൂട്ടുക|കൂട്ടണം|കൂട്ട്|പ്ലസ്', ' + ', norm_c)
            norm_c = re.sub(r'\b(?:minus|kurakkanam|kurakku|subtract)\b|കുറയ്ക്കുക|കുറയ്ക്കണം|കുറയ്ക്ക്|മൈനസ്', ' - ', norm_c)
            norm_c = re.sub(r'\b(?:into|times|multiply|gunikku|gunikkanam|gunanam)\b|ഗുണിക്കുക|ഗുണിക്കണം|ഗുണിക്ക്|ഇന്റു', ' * ', norm_c)
            norm_c = re.sub(r'\b(?:divided\s+by|divide|harikku|harikkanam|bhagikku)\b|ഹരിക്കുക|ഹരിക്കണം|ഹരിക്ക്|ഡിവൈഡ്', ' / ', norm_c)

            math_expr_match = re.search(r'([0-9\.]+\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+(?:\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+)*)', norm_c)
            calc_expr = math_expr_match.group(1).strip() if math_expr_match else ""

            return RhasspyIntent(
                name="CompoundOpenAndCalculate",
                confidence=0.99,
                slots={"app_name": "calculator", "expression": calc_expr},
                text=clean_text
            )

        # 2. Compound Open Platform and Search Query / Music Listening:
        # e.g. "open youtube and search mr beast", "search mr beast on youtube", "oru paatu kelkanam", "mohanlal mass scenes youtubeil kanikku"
        # Malayalam: "യൂട്യൂബ് തുറന്ന് mr beast തിരയൂ", "യൂട്യൂബിൽ mr beast സെർച്ച് ചെയ്യൂ", "ഒരു പാട്ട് കേൾക്കണം"
        
        # Human music intent: "oru paatu kelkanam", "paatu idu", "song vekku", "play music", "ഒരു പാട്ട് വെയ്ക്കൂ"
        m_music_generic = re.search(r'\b(?:oru\s+)?(?:paatu|paattu|song|music|gana)\s+(?:kelkanam|kelkkanam|kelkkan|idu|vekku|vekk|play|കേൾക്കണം|വെയ്ക്കൂ|പാടൂ)\b', q_cmd)
        if m_music_generic:
            prefix = re.sub(r'\b(?:oru\s+)?(?:paatu|paattu|song|music|gana)\s+.*', '', q_cmd).strip()
            search_q = f"{prefix} song" if prefix and len(prefix) > 2 else "trending Malayalam and English songs"
            return RhasspyIntent(
                name="CompoundOpenAndSearch",
                confidence=0.99,
                slots={"platform": "youtube", "query": search_q},
                text=clean_text
            )

        # Colloquial YouTube query: "mohanlal mass scenes youtubeil kanikku", "youtubeil search cheyyu python"
        m_yt_colloquial = re.search(r'(?:youtubeil|യൂട്യൂബിൽ|youtube\s+il)\s+(?:onnu\s+)?(?:search\s+cheyyu|nokku|kaanikku|kanikku|തിരയൂ|കാണിക്കൂ|നോക്കൂ)\s+(.*)', q_cmd) or \
                          re.search(r'(.*?)\s+(?:youtubeil|യൂട്യൂബിൽ|youtube\s+il)\s+(?:onnu\s+)?(?:search\s+cheyyu|nokku|kaanikku|kanikku|തിരയൂ|കാണിക്കൂ|നോക്കൂ|kaananam)', q_cmd)
        if m_yt_colloquial:
            search_q = re.sub(r'^(?:for|about)\s+', '', m_yt_colloquial.group(1)).strip()
            if search_q:
                return RhasspyIntent(
                    name="CompoundOpenAndSearch",
                    confidence=0.99,
                    slots={"platform": "youtube", "query": search_q},
                    text=clean_text
                )

        # Colloquial Google query: "googleil search cheyyu python tutorial", "python tutorial googleil nokku"
        m_g_colloquial = re.search(r'(?:googleil|ഗൂഗിളിൽ|google\s+il)\s+(?:onnu\s+)?(?:search\s+cheyyu|nokku|thirayu|തിരയൂ|നോക്കൂ)\s+(.*)', q_cmd) or \
                         re.search(r'(.*?)\s+(?:googleil|ഗൂഗിളിൽ|google\s+il)\s+(?:onnu\s+)?(?:search\s+cheyyu|nokku|thirayu|തിരയൂ|നോക്കൂ)', q_cmd)
        if m_g_colloquial:
            search_q = re.sub(r'^(?:for|about)\s+', '', m_g_colloquial.group(1)).strip()
            if search_q:
                return RhasspyIntent(
                    name="CompoundOpenAndSearch",
                    confidence=0.99,
                    slots={"platform": "google", "query": search_q},
                    text=clean_text
                )

        m_comp_search = re.search(r'\b(?:open\s+|തുറന്ന്?\s+)?(youtube|google|യൂട്യൂബ്|യൂറ്റ്യൂബ്|ഗൂഗിൾ)\s+(?:and\s+|pinne\s+|ennitt\s+)?(?:search|തിരയൂ|സെർച്ച്\s+ചെയ്യു|സെർച്ച്)\s+(?:for\s+)?(.*)', q_cmd)
        m_search_on = re.search(r'\b(?:search|തിരയൂ|സെർച്ച്)\s+(?:for\s+)?(.*?)\s+(?:on|in|യിൽ|ഇൽ)\s+(youtube|google|യൂട്യൂബ്|യൂറ്റ്യൂബ്|ഗൂഗിൾ)\b', q_cmd)
        if m_comp_search or m_search_on:
            raw_plat = m_comp_search.group(1) if m_comp_search else m_search_on.group(2)
            search_q = (m_comp_search.group(2) if m_comp_search else m_search_on.group(1)).strip()
            plat_canonical = "youtube" if any(k in raw_plat for k in ["youtube", "യൂട്യൂബ്", "യൂറ്റ്യൂബ്"]) else "google"
            return RhasspyIntent(
                name="CompoundOpenAndSearch",
                confidence=0.99,
                slots={"platform": plat_canonical, "query": search_q},
                text=clean_text
            )

        # 3. Compound Open App and Type/Write Text:
        # e.g. "open notepad and write hello world", "notepadil my name is deva ennu ezhuthu", "notepad eduthu hello world type cheyyu"
        m_comp_type_colloquial = re.search(r'\b(?:notepadil|notepad\s+eduthu|നോട്ട്പാഡിൽ)\s+(?:onnu\s+)?(?:type\s+cheyyu|write|ezhuthu|type|എഴുതൂ|ടൈപ്പ്\s+ചെയ്യു)?\s*:?\s*(.*?)(?:\s+ennu\s+ezhuthu|\s+ezhuthu|\s+type\s+cheyyu)?$', q_cmd, re.IGNORECASE)
        if m_comp_type_colloquial and m_comp_type_colloquial.group(1).strip():
            t_text = m_comp_type_colloquial.group(1).strip()
            t_text = re.sub(r'^(?:ith|this)\s+', '', t_text).strip()
            if t_text:
                return RhasspyIntent(
                    name="CompoundOpenAndType",
                    confidence=0.99,
                    slots={"app_name": "notepad", "text": t_text},
                    text=clean_text
                )

        m_comp_type = re.search(r'\b(?:open\s+|തുറന്ന്?\s+)?([a-zA-Z0-9\u0D00-\u0D7F]+)\s+(?:and\s+|ennitt\s+|pinne\s+)?(?:type|write|ezhuthu|type\s+cheyyu|എഴുതൂ|ടൈപ്പ്\s+ചെയ്യു)\s*:?\s*(.+)', q_cmd, re.IGNORECASE)
        if m_comp_type and not any(k in q_cmd for k in ["calculate", "claculate", "search"]):
            t_app = m_comp_type.group(1).strip()
            t_text = m_comp_type.group(2).strip()
            if any(w in t_app for w in ["നോട്ട്", "notepad", "note"]):
                t_app = "notepad"
            return RhasspyIntent(
                name="CompoundOpenAndType",
                confidence=0.99,
                slots={"app_name": t_app, "text": t_text},
                text=clean_text
            )

        # --- HUMAN OPERATOR ACTIONS ---
        # A. Desktop & Window Management
        # "show desktop", "desktopilekk poku", "ellam minimize cheyyu", "desktop kanikku", "ഡെസ്ക്ടോപ്പ് കാണിക്ക്", "ഡെസ്ക്ടോപ്പിലേക്ക് പോകൂ"
        if any(w in q_cmd for w in [
            "show desktop", "minimize all", "go to desktop", "desktopilekk poku", "desktopilek poku",
            "ellam minimize cheyyu", "desktop kanikku", "desktop kaanikku", "ഡെസ്ക്ടോപ്പ്", "ഡെസ്ക്ടോപ്പ് കാണിക്ക്", "ഡെസ്ക്ടോപ്പ് കാണിക്കൂ", "ഡെസ്ക്ടോപ്പിലേക്ക് പോകൂ"
        ]):
            return RhasspyIntent(name="WindowAction", confidence=0.99, slots={"action": "show_desktop"}, text=clean_text)

        # "switch window", "alt tab", "window mathu", "window maathu", "adutha window", "വിൻഡോ മാറ്റൂ", "അടുത്ത വിൻഡോ"
        if any(w in q_cmd for w in ["switch window", "alt tab", "next window", "window mathu", "window maathu", "adutha window", "വിൻഡോ മാറ്റൂ", "അടുത്ത വിൻഡോ"]):
            return RhasspyIntent(name="WindowAction", confidence=0.98, slots={"action": "switch"}, text=clean_text)

        # "close window", "ithonnu adachu vekku", "window adakku", "ith adakku", "ith adachu vekku", "വിൻഡോ ക്ലോസ് ചെയ്യൂ", "വിൻഡോ അടയ്ക്കൂ"
        if any(w in q_cmd for w in [
            "close window", "close this window", "close active window", "window close cheyyu",
            "ithonnu adachu vekku", "window adakku", "ith adakku", "ith adachu vekku", "close aakku",
            "വിൻഡോ ക്ലോസ് ചെയ്യൂ", "വിൻഡോ അടയ്ക്കൂ", "ഇത് അടയ്ക്കൂ", "ഇത് ക്ലോസ് ചെയ്യൂ"
        ]) or q_cmd in ["close this", "close it", "അടയ്ക്കൂ"]:
            return RhasspyIntent(name="WindowAction", confidence=0.98, slots={"action": "close"}, text=clean_text)

        # "new tab", "puthiya tab edukk", "fresh tab edukk", "new tab thura", "പുതിയ ടാബ്"
        if any(w in q_cmd for w in ["new tab", "open new tab", "puthiya tab edukk", "fresh tab edukk", "new tab thura", "പുതിയ ടാബ്", "പുതിയ ടാബ് തുറക്കൂ"]):
            return RhasspyIntent(name="WindowAction", confidence=0.98, slots={"action": "new_tab"}, text=clean_text)

        # "close tab", "tab close cheyyu", "tab adakku", "ടാബ് ക്ലോസ് ചെയ്യൂ", "ടാബ് അടയ്ക്കൂ"
        if any(w in q_cmd for w in ["close tab", "close this tab", "tab close cheyyu", "tab adakku", "ടാബ് ക്ലോസ് ചെയ്യൂ", "ടാബ് അടയ്ക്കൂ"]):
            return RhasspyIntent(name="WindowAction", confidence=0.98, slots={"action": "close_tab"}, text=clean_text)

        # B. Mouse Scrolling & Clicking
        # "scroll down", "thazhekk poku", "thazhekk scroll cheyyu", "താഴേക്ക് സ്ക്രോൾ ചെയ്യൂ"
        if any(w in q_cmd for w in ["scroll down", "thazhekk scroll", "thazhekk poku", "താഴേക്ക് സ്ക്രോൾ", "താഴേക്ക് പോകൂ", "സ്ക്രോൾ ഡൗൺ"]):
            return RhasspyIntent(name="MouseScroll", confidence=0.99, slots={"direction": "down", "clicks": 6}, text=clean_text)
        # "scroll up", "mukalilekk poku", "mukalilekk scroll cheyyu", "മുകളിലേക്ക് സ്ക്രോൾ ചെയ്യൂ"
        if any(w in q_cmd for w in ["scroll up", "mukalilekk scroll", "mukalilekk poku", "മുകളിലേക്ക് സ്ക്രോൾ", "മുകളിലേക്ക് പോകൂ", "സ്ക്രോൾ അപ്പ്"]):
            return RhasspyIntent(name="MouseScroll", confidence=0.99, slots={"direction": "up", "clicks": 6}, text=clean_text)

        # C. Direct Keyboard Typing
        # "type <text>", "write <text>", "ith type cheyyu <text>", "ടൈപ്പ് ചെയ്യൂ <text>"
        m_type = re.search(r'^\s*(?:type|write|ith\s+type\s+cheyyu|type\s+cheyyu|ടൈപ്പ്\s+ചെയ്യു|ടൈപ്പ്\s+ചെയ്യുക|എഴുതൂ)\s*:?\s*(.+)', q_cmd, re.IGNORECASE)
        if m_type and not any(k in q_cmd for k in ["python", "code", "script", "website", "project", "notepad", "and"]):
            return RhasspyIntent(name="KeyboardType", confidence=0.98, slots={"text": m_type.group(1).strip()}, text=clean_text)

        # D. Keyboard Keys & Hotkeys
        # "press enter", "enter adi", "enter adikk", "എന്റർ അടിക്കൂ"
        if any(w in q_cmd for w in ["press enter", "enter adi", "enter adikk", "hit enter", "എന്റർ", "എന്റർ അടിക്കൂ"]) or q_cmd in ["enter"]:
            return RhasspyIntent(name="KeyboardPress", confidence=0.99, slots={"key": "enter"}, text=clean_text)
        # "press escape", "escape adikk", "എസ്കേപ്പ്"
        if any(w in q_cmd for w in ["press escape", "press esc", "escape adikk", "എസ്കേപ്പ്"]) or q_cmd in ["escape", "esc"]:
            return RhasspyIntent(name="KeyboardPress", confidence=0.99, slots={"key": "escape"}, text=clean_text)
        # "press space", "space bar"
        if any(w in q_cmd for w in ["press space", "space bar", "സ്പേസ്"]):
            return RhasspyIntent(name="KeyboardPress", confidence=0.99, slots={"key": "space"}, text=clean_text)
        # Hotkeys: "copy this", "ctrl c", "paste this", "ctrl v", "select all", "ctrl a"
        if any(w in q_cmd for w in ["copy this", "copy cheyyu", "ctrl c", "കോപ്പി ചെയ്യൂ"]):
            return RhasspyIntent(name="KeyboardHotkey", confidence=0.98, slots={"keys": "ctrl+c"}, text=clean_text)
        if any(w in q_cmd for w in ["paste this", "paste cheyyu", "ctrl v", "പേസ്റ്റ് ചെയ്യൂ"]):
            return RhasspyIntent(name="KeyboardHotkey", confidence=0.98, slots={"keys": "ctrl+v"}, text=clean_text)
        if any(w in q_cmd for w in ["select all", "ctrl a", "എല്ലാം സെലക്ട് ചെയ്യൂ"]):
            return RhasspyIntent(name="KeyboardHotkey", confidence=0.98, slots={"keys": "ctrl+a"}, text=clean_text)

        # E. Media Play / Pause
        if any(w in q_cmd for w in ["pause music", "pause song", "pause video", "pause playback", "മ്യൂസിക് പോസ്", "പാട്ട് പോസ്", "പോസ് ചെയ്യൂ"]) or q_cmd in ["pause", "പോസ്"]:
            return RhasspyIntent(name="MediaControl", confidence=0.99, slots={"action": "play_pause"}, text=clean_text)
        if any(w in q_cmd for w in ["play music", "play song", "play video", "resume music", "മ്യൂസിക് പ്ലേ", "പാട്ട് പ്ലേ", "റെസ്യൂം ചെയ്യൂ"]) or q_cmd in ["resume", "റെസ്യൂം"]:
            return RhasspyIntent(name="MediaControl", confidence=0.99, slots={"action": "play_pause"}, text=clean_text)
        if any(w in q_cmd for w in ["next song", "next track", "skip song", "അടുത്ത പാട്ട്", "സ്കിപ്പ് ചെയ്യൂ"]):
            return RhasspyIntent(name="MediaControl", confidence=0.99, slots={"action": "next"}, text=clean_text)

        # --- SINGLE HARDWARE & DESKTOP INTENTS ---
        # A. Open or Run Desktop App or Website
        # English: "open calculator", "run calculator", "launch notepad", "start chrome", "run chrome"
        # Malayalam: "കാൽക്കുലേറ്റർ തുറക്കൂ", "കാൽക്കുലേറ്റർ റൺ ചെയ്യൂ", "യൂട്യൂബ് തുറക്കൂ", "നോട്ട്പാഡ് ഓപ്പൺ ചെയ്യൂ"
        # Hindi: "कैलकुलेटर खोलो", "यूट्यूब खोलो", "नोटपैड खोलो"
        app_match = re.search(r'\b(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9\u0D00-\u0D7F\u0900-\u097F\s\.]+)', q_cmd)
        app_mal_match = re.search(r'([a-zA-Z0-9\u0D00-\u0D7F]+)\s+(?:തുറക്കൂ|തുറക്കുക|തുറന്ന്\s+തരൂ|തുറ|ഓപ്പൺ\s+ചെയ്യു|ഓപ്പൺ\s+ചെയ്യുക|thura|open\s+cheyyu|thuranu\s+tha|റൺ\s+ചെയ്യു|റൺ\s+ചെയ്യുക|റൺ)', q_cmd)
        app_hi_match = re.search(r'([a-zA-Z0-9\u0900-\u097F]+)\s+(?:खोलो|खोलिए|चालू\s+करो|रन\s+करो)', q_cmd)

        if (app_match or app_mal_match or app_hi_match) and not any(k in q_cmd for k in [
            "python", "script", "project", "website", "calculate", "claculate", "compute", "math", "tab", "file",
            "+", "-", "*", "/", "കണക്കു", "kanakku", "kanakk", "kootu", "kootanam", "gunikku", "harikku", "ethra",
            "cheyyunnilla", "cheyyilla", "aakunnilla", "work aavunnilla", "not working", "working alla", "parayumbol",
            "പറ്റുന്നില്ല", "ചെയ്യുന്നില്ല", "ആകുന്നില്ല"
        ]):
            raw_app = (app_match.group(1) if app_match else (app_mal_match.group(1) if app_mal_match else app_hi_match.group(1))).strip()
            # Strip accidental conjunctions or trailing words
            raw_app = re.sub(r'\s+(?:and|please|now|app|window)\b.*', '', raw_app).strip()
            raw_app = re.sub(r'^(?:the|a)\s+', '', raw_app).strip()

            # Canonicalize app or website name
            canonical_app = APP_ALIASES.get(raw_app, raw_app)
            if any(w in raw_app for w in ["കാൽക്കു", "കൽക്കു", "ക്യാൽക്കു", "calculator", "calc", "कैलकुलेटर"]):
                canonical_app = "calculator"
            elif any(w in raw_app for w in ["യൂട്യൂബ്", "youtube"]):
                canonical_app = "youtube"
            elif any(w in raw_app for w in ["ഗൂഗിൾ", "google"]):
                canonical_app = "google"
            elif any(w in raw_app for w in ["വാട്ട്സ്", "വാട്സാ", "whatsapp"]):
                canonical_app = "whatsapp"
            elif any(w in raw_app for w in ["നോട്ട്", "notepad", "note", "नोटपैड"]):
                canonical_app = "notepad"
            elif any(w in raw_app for w in ["ക്രോം", "ബ്രൗസർ", "chrome", "browser", "क्रोम"]):
                canonical_app = "chrome"

            is_run_action = bool(re.search(r'\b(?:run|റൺ|रन)\b', q_cmd))
            return RhasspyIntent(
                name="RunApp" if is_run_action else "OpenApp",
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
        if any(w in q_cmd for w in [
            "mute", "silence sound", "mute volume", "sound mute cheyyu", "sound mute aakku", "mute aakku", "mute cheyyu",
            "shabdam off aakku", "ശബ്ദം ഓഫ് ചെയ്യൂ", "മ്യൂട്ട്", "മ്യൂട്ട് ചെയ്യൂ", "म्यूट करो"
        ]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.98,
                slots={"volume": 0},
                text=clean_text
            )
        if any(w in q_cmd for w in [
            "volume kootu", "volume koottu", "sound koottu", "sound kootu",
            "sound onnu kootu", "sound onnu kootitharaamo", "sound kurachu kootu", "sound kurach kootu",
            "volume increase", "turn up volume", "raise sound", "വോളിയം കൂട്ടൂ", "ശബ്ദം കൂട്ടൂ", "ആവാസ് ബഢാവോ", "आवाज़ बढ़ाओ"
        ]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.98,
                slots={"volume": 80},
                text=clean_text
            )
        if any(w in q_cmd for w in [
            "volume kura", "volume kurakku", "sound kurakku", "sound onnu kurakko", "sound onnu kura", "sound kurakko",
            "shabdam kooduthalanu kurakku", "shabdam kurakku", "volume decrease", "turn down volume", "lower sound",
            "വോളിയം കുറയ്ക്കൂ", "ശബ്ദം കുറയ്ക്കൂ", "ആവാസ് കം കരോ", "आवाज़ कम करो"
        ]):
            return RhasspyIntent(
                name="ChangeVolume",
                confidence=0.98,
                slots={"volume": 30},
                text=clean_text
            )

        # C. Take Screenshot
        if any(w in q_cmd for w in [
            "screenshot", "screen shot", "snapshot", "capture screen",
            "oru screenshot edukk", "screenshot edukk", "screenshot eduthu tha", "screen capture cheyyu", "photo edukk",
            "സ്ക്രീൻഷോട്ട്", "സ്ക്രീൻഷോട്ട് എടുക്കൂ", "സ്ക്രീൻഷോട്ട് എടുക്കുക", "സ്ക്രീൻഷോട്ട് എടുക്ക്", "स्क्रीनशॉट लो"
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
            "screen onnu lock aakku", "screen lock cheyyu", "pc lock cheyyu", "pc poottu", "system lock cheyyu",
            "സ്ക്രീൻ ലോക്ക് ചെയ്യൂ", "കമ്പ്യൂട്ടർ ലോക്ക് ചെയ്യൂ", "സ്ക്രീൻ പൂട്ട്", "കമ്പ്യൂട്ടർ പൂട്ട്", "स्क्रीन लॉक करो"
        ]):
            return RhasspyIntent(
                name="LockScreen",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # E. System Telemetry
        if any(w in q_cmd for w in [
            "telemetry", "hardware status", "system status", "cpu usage", "ram usage", "battery level",
            "battery ethra und", "ente systemil ethra battery und", "battery status nokku", "battery percentage",
            "system info", "ഹാർഡ്വെയർ", "സിസ്റ്റം സ്റ്റാറ്റസ്", "ബാറ്ററി എത്രയുണ്ട്"
        ]):
            return RhasspyIntent(
                name="SystemTelemetry",
                confidence=0.98,
                slots={},
                text=clean_text
            )

        # F. Get Time (English, Malayalam, Hindi)
        time_triggers = [
            "what time is it", "what is the time", "current time", "tell me the time",
            "samayam", "samayam ethrayayi", "samayam enthayi", "ippo ethra samayam aayi", "time parayu", "ippol samayam",
            "സമയം", "ഇപ്പോൾ സമയം", "സമയം എത്രയായി", "സമയം എത്ര", "സമയം പറയൂ", "സമയം എന്തായി",
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
            "theeyathi", "theeyathi parayu", "theeyathi entha", "innu enthu theeyathi", "innathe theeyathi",
            "തീയതി", "ഇന്നത്തെ തീയതി", "തിയതി", "ഇന്ന് എന്ത് തീയതി", "തീയതി പറയൂ",
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
        norm_math = q_cmd
        norm_math = re.sub(r'\b(?:plus|kootanam|kootu|cherkku|add)\b|കൂട്ടുക|കൂട്ടണം|കൂട്ട്|പ്ലസ്', ' + ', norm_math)
        norm_math = re.sub(r'\b(?:minus|kurakkanam|kurakku|subtract)\b|കുറയ്ക്കുക|കുറയ്ക്കണം|കുറയ്ക്ക്|മൈനസ്', ' - ', norm_math)
        norm_math = re.sub(r'\b(?:into|times|multiply|gunikku|gunikkanam|gunanam)\b|ഗുണിക്കുക|ഗുണിക്കണം|ഗുണിക്ക്|ഇന്റു', ' * ', norm_math)
        norm_math = re.sub(r'\b(?:divided\s+by|divide|harikku|harikkanam|bhagikku)\b|ഹരിക്കുക|ഹരിക്കണം|ഹരിക്ക്|ഡിവൈഡ്', ' / ', norm_math)

        math_regex = r'(?:(?:now\s+)?c[al]{2}culate|compute|solve|what\s+is|value\s+of|kanakku\s+kootu|kanakku\s+cheyyu|കണക്കുകൂട്ടൂ|എത്രയാണ്|എത്ര|ethra)?\s*([0-9\.]+\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+(?:\s*[\+\-\*\/\^xX÷%]\s*[0-9\.]+)*)'
        m_calc = re.search(math_regex, norm_math)
        if m_calc and not re.search(r'^\s*(?:open|run|python|execute|code|script|powershell|thurannu|തുറ)\b', q_cmd):
            expr = m_calc.group(1).strip()
            if re.search(r'[\+\-\*\/\^xX÷%]', expr) and re.search(r'\d', expr):
                return RhasspyIntent(
                    name="CalculateMath",
                    confidence=0.98,
                    slots={"expression": expr},
                    text=clean_text
                )

        # I. Live Weather Query (Placed BEFORE Greeting/Identity)
        if any(w in q_cmd for w in ["weather", "temperature", "climate", "kalavastha", "kaalavastha", "mazha", "mazha peyyumo", "veyl undo", "weather enganeyund", "കാലാവസ്ഥ", "മഴ", "മഴ പെയ്യുമോ", "കാലാവസ്ഥ എങ്ങനെയുണ്ട്", "मौसम"]):
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

        # L. Well-being Question ("how are you")
        how_are_you_patterns = [
            "how are you", "how are you doing", "how do you do", "hows it going", "how's it going",
            "how are you delulu", "how are you jarvis", "are you okay", "are you fine",
            "sugamano", "sughamano", "enthokkeyundu", "enthundu vishesham", "sukhamano",
            "സുഖമാണോ", "എന്തൊക്കെയുണ്ട്", "സുഖം തന്നെയല്ലേ",
            "कैसे हो", "आप कैसे हैं", "क्या हाल है"
        ]
        if any(h == q_cmd or q_cmd.startswith(h + " ") or q_cmd.endswith(" " + h) for h in how_are_you_patterns):
            return RhasspyIntent(
                name="HowAreYou",
                confidence=0.99,
                slots={},
                text=clean_text
            )

        # M. Pure Greeting (Strict: only matches when there is no substantive command/question)
        pure_greetings = [
            "hai", "hi", "hello", "hey", "hey delulu", "delulu", "jarvis",
            "good morning", "good afternoon", "good evening", "good day",
            "namaskaram", "namaste",
            "ഹലോ", "ഹായ്", "നമസ്കാരം",
            "नमस्ते", "नमस्कार"
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
