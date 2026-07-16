import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from wiki_assistant.knowledge import get_wiki_knowledge

BASE_URL = "https://www.nexxchange.com"
VISITED = set()
MAX_PAGES = 30


def _extract_text(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text
    except Exception as e:
        print(f"  ⚠ errore: {e}")
        return None


def _crawl(start_url: str, base_domain: str, max_pages: int):
    to_visit = [start_url]
    pages = []

    while to_visit and len(pages) < max_pages:
        url = to_visit.pop(0)
        if url in VISITED:
            continue
        VISITED.add(url)

        print(f"  [{len(pages) + 1}/{max_pages}] {url}... ", end="", flush=True)
        text = _extract_text(url)
        if not text or len(text.strip()) < 100:
            print("skipped")
            continue

        pages.append((url, text))
        print(f"ok ({len(text)} chars)")

        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full = href if href.startswith("http") else f"{base_domain}{href}" if href.startswith("/") else None
                if full and base_domain in full and full not in VISITED and "#" not in full:
                    to_visit.append(full)
        except Exception:
            pass

    return pages


def _insert_into_kb(pages: list):
    kb = get_wiki_knowledge()
    for url, text in pages:
        title = url.replace(BASE_URL, "").strip("/").replace("/", " — ") or "Home"
        kb.insert(
            name=f"Nexxchange — {title}",
            text_content=text,
            metadata={
                "source_url": url,
                "title": title,
                "type": "website",
                "domain": "nexxchange.com",
            },
            skip_if_exists=True,
        )


def main():
    print(f"=== Crawl Nexxchange website (max {MAX_PAGES} pages) ===\n")
    pages = _crawl(BASE_URL, BASE_URL, MAX_PAGES)
    print(f"\nCrawled {len(pages)} pages, inserting into knowledge base...")
    _insert_into_kb(pages)
    print(f"\n✅ Done. {len(pages)} pages ingested from nexxchange.com")


if __name__ == "__main__":
    main()
