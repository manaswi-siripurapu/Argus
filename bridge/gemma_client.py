import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

JETSON_IP = os.getenv("JETSON_IP", "192.168.1.105")
GEMMA_PORT = os.getenv("JETSON_GEMMA_PORT", "8080")
MODEL_NAME = os.getenv("GEMMA_MODEL_NAME", "gemma")
MAX_TOKENS = int(os.getenv("GEMMA_MAX_TOKENS", "1024"))
TEMPERATURE = float(os.getenv("GEMMA_TEMPERATURE", "0.2"))
BASE_URL = f"http://{JETSON_IP}:{GEMMA_PORT}/v1/chat/completions"


def call_gemma(
    system_prompt: str,
    user_message: str,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        response = requests.post(BASE_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"Cannot reach Gemma server at {BASE_URL}. Ensure llama.cpp is running on the Jetson."
        ) from exc
    except (KeyError, IndexError) as exc:
        raw = response.text if "response" in locals() else "<no response>"
        raise ValueError(f"Malformed Gemma response: {exc}\nRaw: {raw}") from exc


def parse_json_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def check_gemma_health() -> bool:
    try:
        response = requests.get(f"http://{JETSON_IP}:{GEMMA_PORT}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False
