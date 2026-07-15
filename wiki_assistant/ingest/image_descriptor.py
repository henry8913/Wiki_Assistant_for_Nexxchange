import base64
from pathlib import Path

import httpx

from wiki_assistant.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

MODEL = "openai/gpt-4o"
SYSTEM_PROMPT = "Descrivi brevemente questa immagine del manuale GolfSuite di Nexxchange, spiegando cosa mostra e a cosa serve. Rispondi in italiano."


def describe_image(image_path: Path) -> str:
    image_bytes = image_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    mime = _guess_mime(image_path)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            },
        ],
    }

    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


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
