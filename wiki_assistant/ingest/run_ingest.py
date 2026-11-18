import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup

from wiki_assistant.ingest.confluence import ConfluenceCrawler, WikiPage
from wiki_assistant.ingest.image_descriptor import describe_image
from wiki_assistant.ingest.image_handler import download_page_images
from wiki_assistant.ingest.local_docs import ingest_local_pdfs
from wiki_assistant.ingest.run_ingest_website import ingest_website
from wiki_assistant.knowledge import get_wiki_knowledge

IMAGES_DIR = Path("data/images")
MAX_VISION_WORKERS = 8
# Some pages collect hundreds of screenshots: describing all of them is slow
# and adds noise. The biggest images are the ones that carry information.
MAX_IMAGES_PER_PAGE = 12


def _describe_safe(image_path: Path) -> str:
    """Describe an image, returning an empty string on failure."""
    try:
        return describe_image(image_path)
    except Exception as exc:
        print(f"  (image error {image_path}: {exc})")
        return ""


def _page_to_text(page: WikiPage) -> str:
    soup = BeautifulSoup(page.content_html, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    return text


def _build_anchor_url(page: WikiPage, heading_id: str) -> str:
    return f"{page.source_url}#{heading_id}"


def _chunk_and_insert(page: WikiPage, text: str):
    kb = get_wiki_knowledge()
    kb.insert(
        name=page.title,
        text_content=text,
        metadata={
            "source_url": page.source_url,
            "page_id": page.id,
            "space_key": page.space_key,
            "title": page.title,
            "version": page.version,
        },
        skip_if_exists=True,
    )


def _stored_version(kb, page_id: str):
    """Return the version of a page already stored in the vector DB, if any."""
    from sqlalchemy import select

    table = kb.vector_db.table
    try:
        with kb.vector_db.Session() as sess:
            rows = sess.execute(
                select(table.c.meta_data)
                .where(table.c.meta_data.contains({"page_id": page_id}))
                .limit(1)
            ).fetchall()
        if rows:
            return (rows[0][0] or {}).get("version")
    except Exception as exc:
        print(f"  (version check error: {exc})")
    return None


def _delete_page_vectors(kb, page_id: str):
    """Remove all vectors tied to a page before re-inserting an updated version."""
    try:
        kb.vector_db.delete_by_metadata({"page_id": page_id})
    except Exception as exc:
        print(f"  (delete error: {exc})")


def _has_image_descriptions(kb, page_id: str) -> bool:
    """True if the page already has at least one image description stored."""
    from sqlalchemy import func, select

    table = kb.vector_db.table
    try:
        with kb.vector_db.Session() as sess:
            count = sess.execute(
                select(func.count())
                .select_from(table)
                .where(table.c.meta_data.contains({"page_id": page_id, "type": "image_description"}))
            ).scalar()
        return bool(count)
    except Exception:
        return True


def ingest_all(pages_by_space: dict[str, list[WikiPage]], force: bool = False):
    total = sum(len(pages) for pages in pages_by_space.values())
    processed = 0
    updated = 0
    skipped = 0

    for space_key, pages in pages_by_space.items():
        print(f"\nIngesting space: {space_key} ({len(pages)} pages)")

        for page in pages:
            processed += 1
            print(f"  [{processed}/{total}] {page.title}... ", end="", flush=True)
            timings: dict[str, float] = {}

            try:
                kb = get_wiki_knowledge()
                t0 = time.time()
                stored_version = _stored_version(kb, page.id)
                timings["check"] = time.time() - t0

                page_changed = force
                if not force and stored_version is not None:
                    try:
                        if int(stored_version) >= int(page.version):
                            # The page is unchanged, but it may still be missing
                            # the descriptions of its images: in that case the
                            # page is processed again (the text is not duplicated).
                            if page.image_urls and not _has_image_descriptions(kb, page.id):
                                print("(immagini mancanti, rigenero)")
                            else:
                                print("up to date")
                                skipped += 1
                                continue
                        page_changed = True
                    except (TypeError, ValueError):
                        page_changed = True

                if page_changed and stored_version is not None:
                    t0 = time.time()
                    _delete_page_vectors(kb, page.id)
                    timings["delete"] = time.time() - t0

                t0 = time.time()
                text = _page_to_text(page)
                timings["text"] = time.time() - t0
                if not text.strip():
                    print("skipped (empty)")
                    continue

                t0 = time.time()
                _chunk_and_insert(page, text)
                timings["insert"] = time.time() - t0

                images_dir = IMAGES_DIR
                image_paths = []
                if page.image_urls:
                    t0 = time.time()
                    image_paths = download_page_images(crawler, page, images_dir)
                    timings["img_download"] = time.time() - t0

                if image_paths:
                    # keep the biggest images of the page
                    image_paths.sort(key=lambda item: item[0].stat().st_size, reverse=True)
                    image_paths = image_paths[:MAX_IMAGES_PER_PAGE]

                    t0 = time.time()
                    # The vision calls are the slowest step: run them in parallel.
                    with ThreadPoolExecutor(max_workers=MAX_VISION_WORKERS) as pool:
                        descriptions = list(
                            pool.map(lambda item: _describe_safe(item[0]), image_paths)
                        )
                    timings["vision"] = time.time() - t0

                    for (img_path, original_url), description in zip(image_paths, descriptions):
                        if not description:
                            continue
                        kb.insert(
                            name=f"{page.title} — {img_path.name}",
                            text_content=description,
                            metadata={
                                "source_url": page.source_url,
                                "page_id": page.id,
                                "image_url": original_url,
                                "type": "image_description",
                                "page_title": page.title,
                                "version": page.version,
                            },
                            skip_if_exists=True,
                        )

                updated += 1
                print("ok" + (" (updated)" if stored_version is not None else ""))
                slow = {k: round(v, 1) for k, v in timings.items() if v > 1}
                if slow:
                    print(f"      tempi: {slow}")
            except Exception as e:
                print(f"error: {e}")

    print(
        f"\nIngestion complete. {processed} pages processed "
        f"({updated} inserted/updated, {skipped} unchanged)."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Confluence wiki into knowledge base")
    parser.add_argument("--spaces", type=str, help="Comma-separated space keys (overrides env)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed every page even if its version is unchanged",
    )
    parser.add_argument(
        "--no-website",
        action="store_true",
        help="Skip the Nexxchange website crawl (only Confluence + local PDFs)",
    )
    args = parser.parse_args()

    if args.spaces:
        spaces = [s.strip() for s in args.spaces.split(",") if s.strip()]
    else:
        spaces = None

    crawler = ConfluenceCrawler(spaces=spaces)
    try:
        pages_by_space = crawler.get_all_pages_for_all_spaces()
        ingest_all(pages_by_space, force=args.force)
    finally:
        crawler.close()

    # Local PDFs in wiki_update/ are always included in a full run.
    ingest_local_pdfs(force=args.force)

    # The company website is included too, unless this is a partial space run
    # or explicitly skipped.
    if not args.spaces and not args.no_website:
        try:
            ingest_website(force=args.force)
        except Exception as exc:
            print(f"⚠️  Website ingest saltato: {exc}")
