import os
import sys
import time
import json
import uuid
import tempfile
import asyncio
import threading
import ctypes
from typing import List, Optional
from dotenv import load_dotenv
import requests

load_dotenv()

# Windows MCI audio player for seamless MP3/WAV playback
winmm = None
if sys.platform == "win32":
    try:
        winmm = ctypes.windll.winmm
    except Exception as e:
        print(f"[Voice] winmm load warning: {e}")

# Global flags
is_speaking = False
_sapi_engine = None

def play_audio_file(file_path: str):
    """Plays an MP3 or WAV audio file on Windows using winmm MCI or system fallback."""
    if not os.path.exists(file_path):
        return

    if sys.platform == "win32" and winmm:
        alias = f"jarvis_audio_{uuid.uuid4().hex[:8]}"
        try:
            # Open media
            open_cmd = f'open "{file_path}" type mpegvideo alias {alias}'
            ret = winmm.mciSendStringW(open_cmd, None, 0, 0)
            if ret != 0:
                # Try generic open if mpegvideo fails
                winmm.mciSendStringW(f'open "{file_path}" alias {alias}', None, 0, 0)
            
            # Play and wait until finished
            winmm.mciSendStringW(f"play {alias} wait", None, 0, 0)
            winmm.mciSendStringW(f"close {alias}", None, 0, 0)
            return
        except Exception as e:
            print(f"[Voice] MCI playback failed: {e}")
            try:
                winmm.mciSendStringW(f"close {alias}", None, 0, 0)
            except Exception:
                pass

    # Fallback to macOS 'afplay' or Linux 'aplay'
    if sys.platform == "darwin":
        os.system(f'afplay "{file_path}"')
    elif sys.platform == "linux":
        os.system(f'aplay "{file_path}" 2>/dev/null || mpg123 "{file_path}" 2>/dev/null')

def _speak_elevenlabs(text: str, api_key: str, voice_id: str) -> bool:
    """Attempt ElevenLabs TTS using custom voice."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
                f.write(response.content)
            play_audio_file(temp_path)
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return True
        else:
            print(f"[Voice] ElevenLabs API status {response.status_code}: {response.text[:120]}")
            return False
    except Exception as e:
        print(f"[Voice] ElevenLabs error: {e}")
        return False

def _speak_edge_tts(text: str) -> bool:
    """Synthesizes voice using Edge-TTS neural voice (Ryan or Christopher)."""
    try:
        import edge_tts
        voice_name = "en-GB-RyanNeural" # Paul Bettany / British JARVIS vibe
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        async def _gen():
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(temp_path)

        asyncio.run(_gen())
        play_audio_file(temp_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[Voice] Edge-TTS error: {e}")
        return False

def _speak_pyttsx3(text: str) -> bool:
    """Thread-safe Windows SAPI5 / pyttsx3 fallback."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass

    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Prefer deep male voice
        voices = engine.getProperty('voices')
        for voice in voices:
            if "david" in voice.name.lower() or "male" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 170)
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"[Voice] Pyttsx3 error: {e}")
        return False

def speak(text: str):
    """
    Main TTS entrypoint.
    Executes tiered fallback: ElevenLabs -> Edge-TTS -> SAPI5 (pyttsx3).
    """
    global is_speaking
    if not text:
        return

    # Clean text if it contains JSON payloads
    if "{" in text and "}" in text and "status" in text:
        text = "Task completed, Sir."

    print(f"JARVIS: {text}")
    is_speaking = True

    try:
        # 1. Try ElevenLabs
        eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        voice_id = os.getenv("ELEVENLABS_VOICE_ID_PRIMARY", "OPggdAvz9vtogYnK5Ge4").strip()
        voice_id_alt = os.getenv("ELEVENLABS_VOICE_ID_SECONDARY", "9375G6zswFk7v9bKTVQF").strip()

        if eleven_key:
            # Try custom voices first
            if _speak_elevenlabs(text, eleven_key, voice_id):
                return
            if voice_id_alt and _speak_elevenlabs(text, eleven_key, voice_id_alt):
                return
            # Fallback to premade ElevenLabs voices supported on all plans
            for premade_id in ["JBFqnCBsd6RMkjVDRZzb", "pNInz6obpgDQGcFmaJgB"]:
                if _speak_elevenlabs(text, eleven_key, premade_id):
                    return

        # 2. Try Edge-TTS (Jarvis-styled British Neural voice)
        if _speak_edge_tts(text):
            return

        # 3. Try Windows SAPI5 pyttsx3
        if _speak_pyttsx3(text):
            return

    finally:
        is_speaking = False

def get_wake_words() -> List[str]:
    """Returns configured wake words from environment."""
    env_words = os.getenv("WAKE_WORDS", "delulu,hey delulu,jarvis")
    words = [w.strip().lower() for w in env_words.split(",") if w.strip()]
    if "delulu" not in words:
        words.append("delulu")
    return words

def listen() -> str:
    """
    Listens to microphone input and converts speech to text.
    Handles sounddevice / speech_recognition seamlessly.
    """
    global is_speaking
    if is_speaking:
        return "none"

    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        r.pause_threshold = 0.8

        # Try standard microphone
        try:
            with sr.Microphone() as source:
                print("[Listening]...")
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
                print("[Recognizing speech]...")
                query = r.recognize_google(audio)
                return query.lower()
        except (AttributeError, Exception) as mic_err:
            # If PyAudio is missing, use sounddevice recording directly
            pass

        # Sounddevice fallback recording
        try:
            import sounddevice as sd
            import numpy as np
            sample_rate = 16000
            duration = 4.0 # record 4 second snippet
            print("[Listening via SoundDevice]...")
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            raw_data = recording.tobytes()
            audio_data = sr.AudioData(raw_data, sample_rate, 2)
            query = r.recognize_google(audio_data)
            return query.lower()
        except Exception:
            return "none"

    except Exception as e:
        return "none"
