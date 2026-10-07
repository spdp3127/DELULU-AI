import os
import io
import re
import httpx
import edge_tts
from fastapi import APIRouter, Query, HTTPException, Response

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Engine"])

MALAYALAM_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID_MALAYALAM", "Unkn6jPAqw7ltVslVduh")

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
            print(f"[ElevenLabs Voice] Response status {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"[ElevenLabs Voice] Synthesis error: {e}")
    return None

async def _synthesize_edge_tts(text: str, voice: str, rate: str = "+5%") -> bytes:
    """Fallback neural synthesis using Edge-TTS."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
    return audio_stream.getvalue()

@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query("auto", description="Voice identifier"),
    rate: str = Query("+5%", description="Speech playback rate")
):
    clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # Auto-detect language if auto: Malayalam or English
    has_malayalam = bool(re.search(r'[\u0D00-\u0D7F]', clean_text))
    
    # Check if Malayalam synthesis is requested
    is_malayalam = has_malayalam or voice in ["malayalam", "ml-IN-MidhunNeural", MALAYALAM_VOICE_ID]

    audio_bytes = None

    if is_malayalam:
        eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        voice_id = MALAYALAM_VOICE_ID if (voice in ["auto", "malayalam", "ml-IN-MidhunNeural"] or not voice) else voice

        # 1. Try ElevenLabs Mahendran J (Unkn6jPAqw7ltVslVduh)
        if eleven_key:
            audio_bytes = await _synthesize_elevenlabs(clean_text, voice_id, eleven_key)
        
        # 2. Fallback to Microsoft Neural Malayalam (ml-IN-MidhunNeural)
        if not audio_bytes:
            try:
                audio_bytes = await _synthesize_edge_tts(clean_text, "ml-IN-MidhunNeural", rate=rate)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")

    else:
        # English voice
        selected_voice = "en-GB-RyanNeural" if voice in ["auto", "en-GB-RyanNeural"] else voice
        try:
            audio_bytes = await _synthesize_edge_tts(clean_text, selected_voice, rate=rate)
        except Exception as e:
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
