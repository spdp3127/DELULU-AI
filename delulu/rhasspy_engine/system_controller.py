import datetime
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
    'tamil': ('Tamil', 'ta-IN', 'நிச்சயமாக, இனி நான் உங்களிடம் தமிழில் பேசுகிறேன்.')
}

class RhasspySystemController:
    """
    Rhasspy System Control & Intent Dispatcher.
    Executes real system actions, desktop automation, hardware control,
    and memory persistence for recognized Rhasspy intents.
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

        # 1. Open Desktop Application
        if name == "OpenApp":
            app_name = slots.get("app_name", "App")
            res = skill_registry.execute_skill("app.open", {"app_name": app_name}, context)
            tools_run.append({"tool": "app.open", "args": {"app_name": app_name}, "result": res})
            if active_lang == "Malayalam":
                return f"{app_name} ഇപ്പോൾ തുറന്നിരിക്കുന്നു.", tools_run, None
            elif active_lang == "Hindi":
                return f"{app_name} खोल दिया गया है।", tools_run, None
            elif active_lang == "Japanese":
                return f"{app_name} を開きました。", tools_run, None
            return f"A {app_name} window is now open.", tools_run, None

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
            res_str = res.get("result", expr)
            tools_run.append({"tool": "math.calculate", "args": {"expression": expr}, "result": res})
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

        # 11. Greeting
        if name == "Greeting":
            if active_lang == "Malayalam":
                reply = "ഹലോ! ഞാൻ DELULU ആണ്. ഞാൻ സജ്ജമാണ്, എന്ത് സഹായമാണ് വേണ്ടത്?"
            elif active_lang == "Hindi":
                reply = "नमस्ते! मैं DELULU हूँ। मैं आपकी क्या मदद कर सकता हूँ?"
            elif active_lang == "Japanese":
                reply = "こんにちは！DELULUです。何かお手伝いできることはありますか？"
            else:
                reply = "Hello! I am DELULU. I am online and ready to assist you."
            return reply, [], None

        # 12. Live Weather
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
