import os
import tempfile
import wave

import pyaudio
import whisper
from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
LANGUAGE = os.getenv("WHISPER_LANGUAGE", "hi")
RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "6"))

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

_model = None


def _load_model():
    global _model
    if _model is None:
        print(f"[voice] Loading Whisper {WHISPER_MODEL} model...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("[voice] Whisper ready")
    return _model


def record_and_transcribe(seconds: int = RECORD_SECONDS) -> str:
    model = _load_model()
    pyaudio_client = pyaudio.PyAudio()
    try:
        stream = pyaudio_client.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
    except OSError as exc:
        pyaudio_client.terminate()
        print(f"[voice] Microphone unavailable: {exc}. Use keyboard mode instead.")
        return ""

    print(f"[voice] Recording {seconds}s - speak now...")
    frames = []
    for _ in range(int(RATE / CHUNK * seconds)):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))
    stream.stop_stream()
    stream.close()
    print("[voice] Recording done - transcribing...")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        with wave.open(tmp.name, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(pyaudio_client.get_sample_size(FORMAT))
            wav_file.setframerate(RATE)
            wav_file.writeframes(b"".join(frames))
        result = model.transcribe(tmp.name, language=LANGUAGE)
    finally:
        pyaudio_client.terminate()
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    transcript = result["text"].strip()
    print(f"[voice] Transcript: {transcript}")
    return transcript
