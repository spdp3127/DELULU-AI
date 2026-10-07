import os
import io
import re
import httpx
import edge_tts
from fastapi import APIRouter, Query, HTTPException, Response

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Engine"])

MALAYALAM_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID_MALAYALAM", "Unkn6jPAqw7ltVslVduh")

VOICE_MAP = {
    "en": "en-GB-RyanNeural",
    "hi": "hi-IN-MadhurNeural",
    "ml": "ml-IN-MidhunNeural",
    "ja": "ja-JP-KeitaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ko": "ko-KR-HyunsuMultilingualNeural",
    "es": "es-ES-XimenaNeural",
    "fr": "fr-FR-VivienneMultilingualNeural",
    "de": "de-DE-SeraphinaMultilingualNeural",
    "ar": "ar-SA-HamedNeural",
    "ta": "ta-IN-ValluvarNeural"
}

def detect_text_language(text: str) -> str:
    """Detect language based on Unicode script."""
    if re.search(r'[\u0D00-\u0D7F]', text):
        return "ml"
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    if re.search(r'[\u3040-\u30FF]', text):
        return "ja"
    if re.search(r'[\uAC00-\uD7AF\u1100-\u11FF]', text):
        return "ko"
    if re.search(r'[\u4E00-\u9FFF]', text):
        return "zh"
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "ta"
    return "en"

async def _synthesize_elevenlabs(text: str, voice_id: str, api_key: str) -> bytes | None:
    """Attempts to synthesize audio using ElevenLabs Multilingual V2."""
    if not api_key or not api_key.strip():
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key.strip()
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.82,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    try:
        async with httpx.AsyncClient(timeout=14.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200 and len(resp.content) > 100:
                return resp.content
    except Exception as e:
        print(f"[ElevenLabs Voice] Synthesis error: {e}")
    return None

async def _synthesize_edge_tts(text: str, voice: str, rate: str = "+5%") -> bytes:
    """Neural synthesis using Microsoft Edge-TTS."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
    return audio_stream.getvalue()

@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query("auto", description="Voice identifier or language"),
    rate: str = Query("+5%", description="Speech playback rate")
):
    clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # 1. Determine language code
    lang = "en"
    voice_lower = (voice or "").lower().strip()
    
    # Check explicit voice/language query
    if voice_lower in VOICE_MAP:
        lang = voice_lower
    elif "hindi" in voice_lower:
        lang = "hi"
    elif "malayalam" in voice_lower:
        lang = "ml"
    elif "japanese" in voice_lower or "japan" in voice_lower:
        lang = "ja"
    elif "chinese" in voice_lower or "china" in voice_lower:
        lang = "zh"
    elif "korean" in voice_lower or "korea" in voice_lower:
        lang = "ko"
    elif "spanish" in voice_lower:
        lang = "es"
    elif "french" in voice_lower:
        lang = "fr"
    elif "german" in voice_lower:
        lang = "de"
    elif "arabic" in voice_lower:
        lang = "ar"
    elif "tamil" in voice_lower:
        lang = "ta"
    elif voice_lower in ["auto", ""] or "neural" not in voice_lower:
        lang = detect_text_language(clean_text)

    # 2. Select neural voice
    selected_neural_voice = VOICE_MAP.get(lang, "en-GB-RyanNeural")
    if "neural" in voice_lower:
        selected_neural_voice = voice

    audio_bytes = None

    # If Malayalam with ElevenLabs configured
    if lang == "ml":
        eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if eleven_key:
            audio_bytes = await _synthesize_elevenlabs(clean_text, MALAYALAM_VOICE_ID, eleven_key)

    # High-quality Edge-TTS synthesis
    if not audio_bytes:
        try:
            audio_bytes = await _synthesize_edge_tts(clean_text, selected_neural_voice, rate=rate)
        except Exception as e:
            # Fallback to English voice if specified language voice had transient error
            try:
                audio_bytes = await _synthesize_edge_tts(clean_text, "en-GB-RyanNeural", rate=rate)
            except Exception:
                raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(audio_bytes)),
            "Cache-Control": "public, max-age=3600"
        }
    )
