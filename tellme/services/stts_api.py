"""
stts HTTP API wrapper — exposes voice I/O as a REST service (headless mode).

In Docker, audio devices aren't available, so this provides:
  - /health — service status
  - /transcribe — POST a WAV file, get text back (via stts STT providers)
  - /speak — POST text, get WAV audio back (via stts TTS providers)
  - /providers — list available STT/TTS providers
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("tellme.stts")

app = FastAPI(title="stts API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded shell instance
_shell = None


def _get_shell():
    """Lazy-init VoiceShell (only if stts_core is available)."""
    global _shell
    if _shell is not None:
        return _shell
    try:
        from stts_core.shell import VoiceShell
        _shell = VoiceShell.__new__(VoiceShell)
        return _shell
    except ImportError:
        return None


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    language: str = Field(default="pl", description="Language code")


@app.get("/health")
async def health():
    has_stts = False
    try:
        import stts_core  # noqa: F401
        has_stts = True
    except ImportError:
        pass
    return {"status": "healthy", "service": "stts", "stts_core": has_stts}


@app.get("/providers")
async def list_providers():
    """List available STT/TTS providers."""
    try:
        from stts_core.registry import build_stt_providers, build_tts_providers
        from stts_core.providers.stt import picovoice, vosk, whisper_cpp, faster_whisper, deepgram, coqui as coqui_stt
        from stts_core.providers.tts import piper, espeak, festival, flite, rhvoice, coqui as coqui_tts, kokoro, say, spd_say

        stt_list = [
            {"name": "vosk", "available": vosk.VoskSTT.is_available()[0]},
            {"name": "whisper_cpp", "available": whisper_cpp.WhisperCppSTT.is_available()[0]},
            {"name": "faster_whisper", "available": faster_whisper.FasterWhisperSTT.is_available()[0]},
            {"name": "deepgram", "available": deepgram.DeepgramSTT.is_available()[0]},
        ]
        tts_list = [
            {"name": "espeak", "available": espeak.EspeakTTS.is_available()[0]},
            {"name": "piper", "available": piper.PiperTTS.is_available()[0]},
        ]
        return {"stt": stt_list, "tts": tts_list}
    except ImportError:
        return {"stt": [], "tts": [], "error": "stts_core not installed"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe a WAV file to text."""
    try:
        from stts_core.providers.stt.whisper_cpp import WhisperCppSTT
        from stts_core.providers.stt.vosk import VoskSTT
    except ImportError:
        raise HTTPException(status_code=503, detail="stts_core not installed")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Try whisper_cpp first, then vosk
        for ProviderClass in [WhisperCppSTT, VoskSTT]:
            available, _ = ProviderClass.is_available()
            if available:
                provider = ProviderClass()
                text = provider.transcribe(Path(tmp_path))
                return {"text": text, "provider": ProviderClass.__name__}

        raise HTTPException(status_code=503, detail="No STT provider available")
    finally:
        os.unlink(tmp_path)


@app.post("/speak")
async def speak(req: SpeakRequest):
    """Synthesize text to speech, return WAV file."""
    try:
        from stts_core.providers.tts.espeak import EspeakTTS
        from stts_core.providers.tts.piper import PiperTTS
    except ImportError:
        raise HTTPException(status_code=503, detail="stts_core not installed")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        for ProviderClass in [PiperTTS, EspeakTTS]:
            available, _ = ProviderClass.is_available()
            if available:
                provider = ProviderClass()
                provider.speak(req.text, output_file=tmp_path)
                return FileResponse(
                    tmp_path,
                    media_type="audio/wav",
                    filename="speech.wav",
                    headers={"X-Provider": ProviderClass.__name__},
                )

        raise HTTPException(status_code=503, detail="No TTS provider available")
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("STTS_PORT", "8200"))
    logger.info(f"Starting stts API on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
