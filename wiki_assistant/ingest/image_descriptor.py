import base64
from pathlib import Path

import httpx

from wiki_assistant.config import (
    OPENCODE_API_KEY,
    OPENCODE_BASE_URL,
    OPENCODE_SESSION_ID,
    OPENCODE_USER_AGENT,
    VISION_MODEL,
)

SYSTEM_PROMPT = (
    "Descrivi brevemente questa immagine del manuale GolfSuite di Nexxchange, "
    "spiegando cosa mostra e a cosa serve. Rispondi in italiano."
)


def describe_image(image_path: Path) -> str:
    """Describe an image of the wiki with a vision model."""
    image_bytes = image_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = _guess_mime(image_path)

    headers = {
        "Authorization": f"Bearer {OPENCODE_API_KEY}",
        "x-opencode-session": OPENCODE_SESSION_ID,
        "User-Agent": OPENCODE_USER_AGENT,
        "Content-Type": "application/json",
    }

    if VISION_MODEL.startswith("claude"):
        url = f"{OPENCODE_BASE_URL.replace('/openai/v1', '')}/anthropic/v1/messages"
        payload = {
            "model": VISION_MODEL,
            "max_tokens": 400,
            "system": SYSTEM_PROMPT,
            # A short description does not need reasoning: it only slows the
            # call down and can eat the whole token budget.
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                        {"type": "text", "text": "Descrivi l'immagine."},
                    ],
                }
            ],
        }
    else:
        url = f"{OPENCODE_BASE_URL}/chat/completions"
        payload = {
            "model": VISION_MODEL,
            "max_tokens": 400,
            "reasoning_effort": "none",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                },
            ],
        }

    with httpx.Client(timeout=180) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return _extract_text(resp.json()).strip()


def _extract_text(data: dict) -> str:
    """Read the answer from an OpenAI-style or Anthropic-style response."""
    content = data.get("choices")
    if content:
        return content[0].get("message", {}).get("content", "")

    blocks = data.get("content")
    if isinstance(blocks, list):
        return " ".join(block.get("text", "") for block in blocks if block.get("type") == "text")

    return ""


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")
