import datetime
import webbrowser
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional
from delulu.skills.registry import skill_registry
from delulu.rhasspy_engine.nlu import RhasspyIntent
from delulu.memory.memory_service import memory_service

RHASSPY_LANG_MAP = {
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
    'tamil': ('Tamil', 'ta-IN', 'நிச்சயமாக, ഇനി ഞാൻ உங்களிடம் தமிழில் பேசுகிறேன்.')
}

class RhasspySystemController:
    """
    Rhasspy System Control & Intent Dispatcher.
    Executes real system actions, desktop automation, hardware control,
    compound multi-action commands, and memory persistence for recognized Rhasspy intents.
    """

    def handle_intent(self, intent: RhasspyIntent, context: Dict[str, Any], active_lang: str = "English") -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
        """
        Executes real system action matching the intent.
        Returns: (spoken_reply, tool_results_list, updated_lang_code)
        """
        tools_run = []
        name = intent.name
        slots = intent.slots
        user_id = context.get("user_id")
        db = context.get("db")

        # -2. Live Code & Script Execution
        if name == "RunCode":
            code_str = slots.get("code", "")
            language = slots.get("language", "python")
            res = skill_registry.execute_skill("code.run", {"code": code_str, "language": language}, context)
            tools_run.append({"tool": "code.run", "args": {"code": code_str, "language": language}, "result": res})
            res_str = res.get("result", "") if isinstance(res, dict) else str(res)
            if active_lang == "Malayalam":
                return f"കോഡ് ലൈവായി എക്സിക്യൂട്ട് ചെയ്തു:\n{res_str}", tools_run, None
            elif active_lang == "Hindi":
                return f"कोड सफलतापूर्वक निष्पादित किया गया:\n{res_str}", tools_run, None
            return f"Code executed live:\n{res_str}", tools_run, None

        # -1. Live Project & Web Application Runner
        if name == "RunProject":
            p_name = slots.get("project_name", "")
            res = skill_registry.execute_skill("project.run", {"project_name": p_name}, context)
            tools_run.append({"tool": "project.run", "args": {"project_name": p_name}, "result": res})
            res_val = res.get("result", {}) if isinstance(res, dict) else {}
            live_url = res_val.get("live_url", "http://localhost:8000/projects/") if isinstance(res_val, dict) else str(res)
            if active_lang == "Malayalam":
                return f"🟢 വെബ്‌സൈറ്റ് പ്രൊജക്റ്റ് '{p_name}' ലൈവ് സെർവറിൽ റൺ (RUN) ചെയ്യുന്നു: {live_url}", tools_run, None
            elif active_lang == "Hindi":
                return f"🟢 प्रोजेक्ट '{p_name}' लाइव सर्वर पर सक्रिय रूप से चल रहा है: {live_url}", tools_run, None
            return f"🟢 Project '{p_name}' is now LIVE and RUNNING at: {live_url}", tools_run, None

        # 0. Active App Runner
        if name == "RunApp":
            app_name = slots.get("app_name", "App")
            task = slots.get("task", "")
            res = skill_registry.execute_skill("app.run", {"app_name": app_name, "task": task}, context)
            tools_run.append({"tool": "app.run", "args": {"app_name": app_name, "task": task}, "result": res})
            res_str = res.get("result", "") if isinstance(res, dict) else str(res)
            clean_display = app_name.capitalize()
            if active_lang == "Malayalam":
                return f"🟢 {clean_display} ഇപ്പോൾ തത്സമയം റൺ ചെയ്യുന്നു. {res_str}", tools_run, None
            elif active_lang == "Hindi":
                return f"🟢 {clean_display} अब सक्रिय रूप से चल रहा है। {res_str}", tools_run, None
            return f"🟢 {clean_display} is now RUNNING. {res_str}", tools_run, None

        # 0a. Compound Open App and Calculate
        # e.g. "open calculator and calculate 5+5", "open calculator and claculate 5+5", "calculator thurannu kanakku cheyyu"
        if name == "CompoundOpenAndCalculate":
            app_name = slots.get("app_name", "calculator")
            expr = slots.get("expression", "").strip()

            # 1. Run / Open Calculator in Windows
            res_open = skill_registry.execute_skill("app.run", {"app_name": app_name, "task": expr}, context)
            tools_run.append({"tool": "app.run", "args": {"app_name": app_name, "task": expr}, "result": res_open})

            if not expr:
                # User asked to open calculator and calculate, but didn't provide numbers yet
                if active_lang == "Malayalam":
                    return "കാൽക്കുലേറ്റർ ഇപ്പോൾ തുറന്നിട്ടുണ്ട്. ഏത് കണക്കാണ് ചെയ്യേണ്ടത്? പറയൂ (ഉദാ: 5+5 അല്ലെങ്കിൽ 120*45), ഞാൻ ഉടൻ തന്നെ കാൽക്കുലേറ്ററിൽ കണക്കുകൂട്ടിത്തരാം!", tools_run, None
                elif active_lang == "Hindi":
                    return "मैंने कैलकुलेटर खोल दिया है। आप कौन सी गणना करना चाहते हैं? बताएं (उदा: 5+5 या 120*45), मैं तुरंत हल कर दूँगा!", tools_run, None
                return "I have opened Calculator. Which calculation would you like me to do? (e.g., 5+5 or 120*45) Let me know and I will solve it right away!", tools_run, None

            # 2. Calculate Math
            res_math = skill_registry.execute_skill("math.calculate", {"expression": expr}, context)
            tools_run.append({"tool": "math.calculate", "args": {"expression": expr}, "result": res_math})
            res_str = res_math.get("result", expr) if isinstance(res_math, dict) else str(res_math)

            # 3. Wait for Calculator window and type into it
            try:
                import time, pyautogui
                pyautogui.FAILSAFE = False
                time.sleep(0.7)
                norm_expr = expr.replace(' ', '')
                pyautogui.typewrite(f"{norm_expr}=", interval=0.06)
            except Exception:
                pass

            if active_lang == "Malayalam":
                return f"കാൽക്കുലേറ്റർ തുറന്ന് {res_str} കണക്കുകൂട്ടിയിട്ടുണ്ട്.", tools_run, None
            elif active_lang == "Hindi":
                return f"मैंने कैलकुलेटर खोल दिया है और {res_str} हल कर दिया है।", tools_run, None
            return f"I have opened Calculator and calculated {res_str}.", tools_run, None

        # 0b. Compound Open Platform and Search
        # e.g. "open youtube and search mr beast", "search mr beast on youtube"
        if name == "CompoundOpenAndSearch":
            platform = slots.get("platform", "youtube").lower()
            query = slots.get("query", "").strip()

            if "youtube" in platform:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                tools_run.append({"tool": "app.open", "args": {"app_name": "youtube", "query": query}, "result": {"status": "success", "url": url}})
                if active_lang == "Malayalam":
                    return f"യൂട്യൂബ് തുറന്ന് '{query}' തിരഞ്ഞിട്ടുണ്ട്.", tools_run, None
                return f"Opened YouTube and searched for '{query}'.", tools_run, None
            elif "google" in platform:
                url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                webbrowser.open(url)
                tools_run.append({"tool": "app.open", "args": {"app_name": "google", "query": query}, "result": {"status": "success", "url": url}})
                if active_lang == "Malayalam":
                    return f"ഗൂഗിൾ തുറന്ന് '{query}' തിരഞ്ഞിട്ടുണ്ട്.", tools_run, None
                return f"Opened Google and searched for '{query}'.", tools_run, None

        # 0c. Compound Open App and Type/Write Text
        if name == "CompoundOpenAndType":
            app_name = slots.get("app_name", "notepad")
            text = slots.get("text", "")
            res = skill_registry.execute_skill("human.open_and_type", {"app_name": app_name, "text": text}, context)
            tools_run.append({"tool": "human.open_and_type", "args": {"app_name": app_name, "text": text}, "result": res})
            clean_app = app_name.capitalize()
            if active_lang == "Malayalam":
                return f"{clean_app} തുറന്ന് '{text}' എന്ന് ടൈപ്പ് ചെയ്തിട്ടുണ്ട്.", tools_run, None
            elif active_lang == "Hindi":
                return f"{clean_app} खोलकर '{text}' लिख दिया गया है।", tools_run, None
            return f"Opened {clean_app} and typed: '{text}'.", tools_run, None

        # 0d. Window & Desktop Action
        if name == "WindowAction":
            act = slots.get("action", "show_desktop")
            res = skill_registry.execute_skill("window.action", {"action": act}, context)
            tools_run.append({"tool": "window.action", "args": {"action": act}, "result": res})
            res_str = res.get("result", "") if isinstance(res, dict) else str(res)
            if active_lang == "Malayalam":
                return f"വിൻഡോ ആക്ഷൻ ({act}) നിർവ്വഹിച്ചു.", tools_run, None
            return f"{res_str}", tools_run, None

        # 0e. Mouse Scroll
        if name == "MouseScroll":
            direction = slots.get("direction", "down")
            clicks = slots.get("clicks", 6)
            res = skill_registry.execute_skill("mouse.scroll", {"direction": direction, "clicks": clicks}, context)
            tools_run.append({"tool": "mouse.scroll", "args": {"direction": direction, "clicks": clicks}, "result": res})
            if active_lang == "Malayalam":
                return f"സ്ക്രീൻ {direction} ദിശയിലേക്ക് സ്ക്രോൾ ചെയ്തു.", tools_run, None
            return f"Scrolled {direction}.", tools_run, None

        # 0f. Direct Keyboard Type
        if name == "KeyboardType":
            text = slots.get("text", "")
            res = skill_registry.execute_skill("keyboard.type", {"text": text}, context)
            tools_run.append({"tool": "keyboard.type", "args": {"text": text}, "result": res})
            if active_lang == "Malayalam":
                return f"സ്ക്രീനിൽ '{text}' എന്ന് ടൈപ്പ് ചെയ്തു.", tools_run, None
            return f"Typed '{text}' on screen.", tools_run, None

        # 0g. Keyboard Key Press
        if name == "KeyboardPress":
            key = slots.get("key", "enter")
            res = skill_registry.execute_skill("keyboard.press", {"key": key}, context)
            tools_run.append({"tool": "keyboard.press", "args": {"key": key}, "result": res})
            if active_lang == "Malayalam":
                return f"കീബോർഡിൽ '{key}' പ്രസ്സ് ചെയ്തു.", tools_run, None
            return f"Pressed '{key}' key.", tools_run, None

        # 0h. Keyboard Hotkey
        if name == "KeyboardHotkey":
            keys = slots.get("keys", "ctrl+c")
            res = skill_registry.execute_skill("keyboard.hotkey", {"keys": keys}, context)
            tools_run.append({"tool": "keyboard.hotkey", "args": {"keys": keys}, "result": res})
            if active_lang == "Malayalam":
                return f"ഷോർട്ട്കട്ട് '{keys}' പ്രവർത്തിപ്പിച്ചു.", tools_run, None
            return f"Executed shortcut '{keys}'.", tools_run, None

        # 0i. Media Control
        if name == "MediaControl":
            act = slots.get("action", "play_pause")
            res = skill_registry.execute_skill("media.control", {"action": act}, context)
            tools_run.append({"tool": "media.control", "args": {"action": act}, "result": res})
            if active_lang == "Malayalam":
                return f"മീഡിയ കൺട്രോൾ ({act}) നിർവ്വഹിച്ചു.", tools_run, None
            return f"Media control '{act}' executed.", tools_run, None

        # 1. Open Desktop Application or Website
        if name == "OpenApp":
            app_name = slots.get("app_name", "App")
            res = skill_registry.execute_skill("app.open", {"app_name": app_name}, context)
            tools_run.append({"tool": "app.open", "args": {"app_name": app_name}, "result": res})
            clean_display = app_name.capitalize()
            if app_name.lower() in ["youtube", "യൂട്യൂബ്"]:
                clean_display = "YouTube"
            elif app_name.lower() in ["whatsapp", "വാട്സാപ്പ്"]:
                clean_display = "WhatsApp Web"

            if active_lang == "Malayalam":
                return f"{clean_display} ഇപ്പോൾ തുറന്നിരിക്കുന്നു.", tools_run, None
            elif active_lang == "Hindi":
                return f"{clean_display} खोल दिया गया है।", tools_run, None
            elif active_lang == "Japanese":
                return f"{clean_display} を開きました。", tools_run, None
            return f"A {clean_display} window is now open.", tools_run, None

        # 2. Change System Volume
        if name == "ChangeVolume":
            vol_level = slots.get("volume", 50)
            res = skill_registry.execute_skill("system.volume", {"level": vol_level}, context)
            tools_run.append({"tool": "system.volume", "args": {"level": vol_level}, "result": res})
            if active_lang == "Malayalam":
                return f"സിസ്റ്റം വോളിയം {vol_level}% ആക്കി മാറ്റിയുണ്ട്.", tools_run, None
            elif active_lang == "Hindi":
                return f"सिस्टम वॉल्यूम {vol_level}% कर दिया गया है।", tools_run, None
            elif active_lang == "Japanese":
                return f"音量を {vol_level}% に設定しました。", tools_run, None
            return f"System volume set to {vol_level}%.", tools_run, None

        # 3. Take Desktop Screenshot
        if name == "TakeScreenshot":
            res = skill_registry.execute_skill("system.screenshot", {}, context)
            tools_run.append({"tool": "system.screenshot", "args": {}, "result": res})
            if active_lang == "Malayalam":
                return "ഡെസ്ക്ടോപ്പ് സ്ക്രീൻഷോട്ട് സേവ് ചെയ്തു.", tools_run, None
            elif active_lang == "Hindi":
                return "स्क्रीनशॉट डेस्कटॉप पर सहेज लिया गया है।", tools_run, None
            elif active_lang == "Japanese":
                return "スクリーンショットを撮影しました。", tools_run, None
            return f"{res.get('result', 'Screenshot captured to Desktop.')}.", tools_run, None

        # 4. Lock Screen
        if name == "LockScreen":
            res = skill_registry.execute_skill("system.lock", {}, context)
            tools_run.append({"tool": "system.lock", "args": {}, "result": res})
            if active_lang == "Malayalam":
                return "സിസ്റ്റം സ്ക്രീൻ ലോക്ക് ചെയ്തു.", tools_run, None
            elif active_lang == "Hindi":
                return "वर्कस्टेशन स्क्रीन लॉक कर दी गई है।", tools_run, None
            elif active_lang == "Japanese":
                return "画面をロックしました。", tools_run, None
            return "Workstation screen locked.", tools_run, None

        # 5. Hardware Status & Telemetry
        if name == "SystemTelemetry":
            res = skill_registry.execute_skill("system.telemetry", {}, context)
            tools_run.append({"tool": "system.telemetry", "args": {}, "result": res})
            return f"{res.get('result', 'Hardware telemetry collected.')}", tools_run, None

        # 6. Time Query
        if name == "GetTime":
            res = skill_registry.execute_skill("time.get", {}, context)
            time_val = res.get("result", datetime.datetime.now().strftime("%I:%M:%S %p"))
            tools_run.append({"tool": "time.get", "args": {}, "result": res})
            if active_lang == "Malayalam":
                return f"ഇപ്പോൾ സമയം {time_val} ആണ്.", tools_run, None
            elif active_lang == "Hindi":
                return f"अभी समय {time_val} है।", tools_run, None
            elif active_lang == "Japanese":
                return f"現在の時刻は {time_val} です。", tools_run, None
            return f"The current time is {time_val}.", tools_run, None

        # 7. Date Query
        if name == "GetDate":
            res = skill_registry.execute_skill("date.get", {}, context)
            date_val = res.get("result", datetime.datetime.now().strftime("%A, %B %d, %Y"))
            tools_run.append({"tool": "date.get", "args": {}, "result": res})
            if active_lang == "Malayalam":
                return f"ഇന്ന് {date_val} ആണ്.", tools_run, None
            elif active_lang == "Hindi":
                return f"आज {date_val} है।", tools_run, None
            elif active_lang == "Japanese":
                return f"本日は {date_val} です。", tools_run, None
            return f"Today is {date_val}.", tools_run, None

        # 8. Math Calculation
        if name == "CalculateMath":
            expr = slots.get("expression", "")
            res = skill_registry.execute_skill("math.calculate", {"expression": expr}, context)
            res_str = res.get("result", expr) if isinstance(res, dict) else str(res)
            tools_run.append({"tool": "math.calculate", "args": {"expression": expr}, "result": res})
            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                norm_expr = expr.replace(' ', '')
                pyautogui.typewrite(f"{norm_expr}=", interval=0.04)
            except Exception:
                pass
            if active_lang == "Malayalam":
                return f"{res_str} ആണ്.", tools_run, None
            elif active_lang == "Hindi":
                return f"{res_str} है।", tools_run, None
            return f"{res_str}.", tools_run, None

        # 9. Language Switch Request
        if name == "SwitchLanguage":
            target_l = slots.get("language", "").lower()
            if target_l in RHASSPY_LANG_MAP:
                l_name, l_code, l_reply = RHASSPY_LANG_MAP[target_l]
                if db and user_id:
                    memory_service.write_memory(
                        db=db,
                        user_id=user_id,
                        content=f"Preferred conversation language: {l_name}",
                        memory_type="preference",
                        category="language"
                    )
                return l_reply, [], l_code

        # 10. Identity
        if name == "Identity":
            if active_lang == "Malayalam":
                reply = "ഞാൻ DELULU ആണ്, SPDP Company നിർമ്മിച്ചതാണ്."
            elif active_lang == "Hindi":
                reply = "मैं DELULU हूँ, SPDP Company द्वारा निर्मित।"
            elif active_lang == "Japanese":
                reply = "私はDELULUです。SPDP Companyによって開発されました。"
            else:
                reply = "I am DELULU, made by SPDP company."
            return reply, [], None

        # 11. Well-being Question ("how are you")
        if name == "HowAreYou":
            if active_lang == "Malayalam":
                reply = "എനിക്ക് സുഖമാണ്! ഞാൻ പൂർണ്ണ സജ്ജനാണ്, എന്താണ് ചെയ്യേണ്ടത്?"
            elif active_lang == "Hindi":
                reply = "मैं बिल्कुल ठीक हूँ! आपकी क्या मदद करूँ?"
            elif active_lang == "Japanese":
                reply = "元気です！何かお手伝いできることはありますか？"
            else:
                reply = "I am functioning at peak performance, Sir. Ready to assist you with anything you need."
            return reply, [], None

        # 12. Greeting
        if name == "Greeting":
            if active_lang == "Malayalam":
                reply = "ഹലോ! ഞാൻ DELULU ആണ്. ഞാൻ ഓൺലൈനിലാണ്."
            elif active_lang == "Hindi":
                reply = "नमस्ते! मैं DELULU हूँ। मैं ऑनलाइन हूँ।"
            elif active_lang == "Japanese":
                reply = "こんにちは！DELULUです。"
            else:
                reply = "Hello! I am DELULU, online and ready to assist you."
            return reply, [], None

        # 13. Live Weather
        if name == "GetWeather":
            loc = slots.get("location", "Kochi")
            res = skill_registry.execute_skill("weather.get", {"location": loc}, context)
            tools_run.append({"tool": "weather.get", "args": {"location": loc}, "result": res})
            weather_text = res.get("result", f"Weather data for {loc} retrieved.")
            if active_lang == "Malayalam":
                return f"ഇന്നത്തെ കാലാവസ്ഥാ വിവരങ്ങൾ: {weather_text}", tools_run, None
            elif active_lang == "Hindi":
                return f"मौसम की जानकारी: {weather_text}", tools_run, None
            return f"{weather_text}", tools_run, None

        return f"Intent '{name}' processed successfully.", tools_run, None

rhasspy_system_controller = RhasspySystemController()
