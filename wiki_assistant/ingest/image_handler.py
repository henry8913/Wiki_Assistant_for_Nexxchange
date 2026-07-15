from pathlib import Path
from typing import Optional

from wiki_assistant.ingest.confluence import ConfluenceCrawler, WikiPage


def download_page_images(
    crawler: ConfluenceCrawler,
    page: WikiPage,
    base_dir: Path,
) -> list[tuple[Path, str]]:
    page_dir = base_dir / page.space_key / page.id
    page_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[tuple[Path, str]] = []

    for img_url in page.image_urls:
        path = crawler.download_image(img_url, page_dir)
        if path:
            downloaded.append((path, img_url))

    attachments = crawler.get_page_attachments(page.id)
    for att in attachments:
        download_url = att["download_url"]
        if _is_image(att.get("media_type", "")):
            path = crawler.download_image(download_url, page_dir)
            if path:
                downloaded.append((path, download_url))

    return downloaded


def _is_image(media_type: str) -> bool:
    return media_type.startswith("image/")


def get_image_markdown(image_path: Path) -> Optional[str]:
    if image_path.exists():
        return f"![{image_path.name}]({image_path})"
    return None
