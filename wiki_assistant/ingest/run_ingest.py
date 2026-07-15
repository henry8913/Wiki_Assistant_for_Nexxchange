import argparse
from pathlib import Path

from bs4 import BeautifulSoup

from wiki_assistant.ingest.confluence import ConfluenceCrawler, WikiPage
from wiki_assistant.ingest.image_descriptor import describe_image
from wiki_assistant.ingest.image_handler import download_page_images
from wiki_assistant.knowledge import get_wiki_knowledge

IMAGES_DIR = Path("data/images")


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


def ingest_all(pages_by_space: dict[str, list[WikiPage]]):
    total = sum(len(pages) for pages in pages_by_space.values())
    processed = 0

    for space_key, pages in pages_by_space.items():
        print(f"\nIngesting space: {space_key} ({len(pages)} pages)")

        for page in pages:
            processed += 1
            print(f"  [{processed}/{total}] {page.title}... ", end="", flush=True)

            try:
                text = _page_to_text(page)
                if not text.strip():
                    print("skipped (empty)")
                    continue

                _chunk_and_insert(page, text)

                images_dir = IMAGES_DIR
                image_paths = []
                if page.image_urls:
                    image_paths = download_page_images(crawler, page, images_dir)

                for img_path, original_url in image_paths:
                    try:
                        description = describe_image(img_path)
                        kb = get_wiki_knowledge()
                        kb.insert(
                            name=f"{page.title} — {img_path.name}",
                            text_content=description,
                            metadata={
                                "source_url": page.source_url,
                                "image_url": original_url,
                                "type": "image_description",
                                "page_title": page.title,
                            },
                            skip_if_exists=True,
                        )
                    except Exception as img_err:
                        print(f"  (image error: {img_err})")

                print("ok")
            except Exception as e:
                print(f"error: {e}")

    print(f"\nIngestion complete. {processed} pages processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Confluence wiki into knowledge base")
    parser.add_argument("--spaces", type=str, help="Comma-separated space keys (overrides env)")
    parser.add_argument("--skip-if-exists", action="store_true", default=True)
    args = parser.parse_args()

    if args.spaces:
        import os
        os.environ["WIKI_SPACES"] = args.spaces
        from wiki_assistant.config import WIKI_SPACES
        import importlib
        importlib.reload(__import__("wiki_assistant.config"))

    crawler = ConfluenceCrawler()
    try:
        pages_by_space = crawler.get_all_pages_for_all_spaces()
        ingest_all(pages_by_space)
    finally:
        crawler.close()
