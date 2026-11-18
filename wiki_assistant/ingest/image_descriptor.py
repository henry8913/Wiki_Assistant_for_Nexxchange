import base64
import io
from pathlib import Path

import httpx
from PIL import Image

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

# Icons, avatars and tiny logos do not carry useful information.
MIN_SIDE = 200
# Screenshots are sent downscaled: fewer image tokens, faster and cheaper.
MAX_SIDE = 1280
JPEG_QUALITY = 80


def describe_image(image_path: Path) -> str:
    """Describe an image of the wiki with a vision model.

    Returns an empty string when the image is too small to be meaningful.
    """
    prepared = _prepare_image(image_path)
    if prepared is None:
        return ""
    b64, mime = prepared

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
            # A short description does not need reasoning: it only slows the
            # call down and can eat the whole token budget.
            "thinking": {"type": "disabled"},
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": b64},
                        },
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


def _prepare_image(path: Path) -> tuple[str, str] | None:
    """Downscale the image and return (base64, mime); None if it is too small."""
    try:
        with Image.open(path) as img:
            width, height = img.size
            if width < MIN_SIDE and height < MIN_SIDE:
                return None

            if max(width, height) > MAX_SIDE:
                img = img.copy()
                img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P", "LA"):
                rgb = Image.new("RGB", img.size, (255, 255, 255))
                rgb.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
                img = rgb
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("utf-8"), "image/jpeg"
    except Exception:
        return None


def _extract_text(data: dict) -> str:
    """Read the answer from an OpenAI-style or Anthropic-style response."""
    choices = data.get("choices")
    if choices:
        return choices[0].get("message", {}).get("content", "") or ""

    blocks = data.get("content")
    if isinstance(blocks, list):
        return " ".join(block.get("text", "") for block in blocks if block.get("type") == "text")

    return ""
