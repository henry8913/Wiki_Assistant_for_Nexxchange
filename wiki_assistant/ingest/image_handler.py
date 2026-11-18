from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from wiki_assistant.ingest.confluence import ConfluenceCrawler, WikiPage

MAX_WORKERS = 8


def download_page_images(
    crawler: ConfluenceCrawler,
    page: WikiPage,
    base_dir: Path,
) -> list[tuple[Path, str]]:
    """Download all images of a page, in parallel.

    Atlassian is slow at serving attachments one by one, so the downloads are
    issued concurrently and the order of the results is preserved.
    """
    page_dir = base_dir / page.space_key / page.id
    page_dir.mkdir(parents=True, exist_ok=True)

    urls = list(page.image_urls)
    for att in crawler.get_page_attachments(page.id):
        if _is_image(att.get("media_type", "")):
            urls.append(att["download_url"])

    # keep the first occurrence of every url
    unique_urls = list(dict.fromkeys(urls))

    if not unique_urls:
        return []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        paths = list(pool.map(lambda u: crawler.download_image(u, page_dir), unique_urls))

    return [(path, url) for path, url in zip(paths, unique_urls) if path]


def _is_image(media_type: str) -> bool:
    return media_type.startswith("image/")


def get_image_markdown(image_path: Path) -> Optional[str]:
    if image_path.exists():
        return f"![{image_path.name}]({image_path})"
    return None
