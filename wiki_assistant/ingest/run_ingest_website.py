import hashlib
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


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _stored_hash(kb, url: str):
    from sqlalchemy import select

    table = kb.vector_db.table
    try:
        with kb.vector_db.Session() as sess:
            rows = sess.execute(
                select(table.c.meta_data)
                .where(table.c.meta_data.contains({"type": "website", "source_url": url}))
                .limit(1)
            ).fetchall()
        if rows:
            return (rows[0][0] or {}).get("content_hash")
    except Exception:
        pass
    return None


def _insert_into_kb(pages: list, force: bool = False) -> int:
    kb = get_wiki_knowledge()
    inserted = 0
    for url, text in pages:
        title = url.replace(BASE_URL, "").strip("/").replace("/", " — ") or "Home"
        content_hash = _text_hash(text)

        if not force and _stored_hash(kb, url) == content_hash:
            print(f"  ✓ {url} — già aggiornato")
            continue

        try:
            kb.vector_db.delete_by_metadata({"type": "website", "source_url": url})
        except Exception:
            pass

        kb.insert(
            name=f"Nexxchange — {title}",
            text_content=text,
            metadata={
                "source_url": url,
                "title": title,
                "type": "website",
                "domain": "nexxchange.com",
                "content_hash": content_hash,
            },
            skip_if_exists=True,
        )
        inserted += 1
    return inserted


def ingest_website(force: bool = False) -> int:
    print(f"\n=== Crawl Nexxchange website (max {MAX_PAGES} pages) ===\n")
    pages = _crawl(BASE_URL, BASE_URL, MAX_PAGES)
    print(f"\nCrawled {len(pages)} pages, inserting into knowledge base...")
    inserted = _insert_into_kb(pages, force=force)
    print(f"\n✅ Website: {inserted} pagine aggiornate/inserite su {len(pages)}.")
    return inserted


def main():
    ingest_website()


if __name__ == "__main__":
    main()
