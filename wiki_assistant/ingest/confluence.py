import base64
import mimetypes
import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from wiki_assistant.config import WIKI_API_TOKEN, WIKI_BASE_URL, WIKI_EMAIL, WIKI_SPACES


@dataclass
class WikiPage:
    id: str
    title: str
    space_key: str
    content_html: str
    source_url: str
    version: int
    headings: list[dict] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


class ConfluenceCrawler:
    def __init__(self, spaces: Optional[list[str]] = None):
        self.base_url = WIKI_BASE_URL.rstrip("/")
        self.spaces = spaces if spaces else WIKI_SPACES
        auth_str = f"{WIKI_EMAIL}:{WIKI_API_TOKEN}"
        self.auth_header = {
            "Authorization": f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        }
        self.api_base = f"{self.base_url}/rest/api"
        self.client = httpx.Client(
            headers={
                **self.auth_header,
                "Accept": "application/json",
            },
            # Atlassian redirects image downloads to api.media.atlassian.com
            follow_redirects=True,
            # Default httpx timeout is 5s: too short for big attachments.
            timeout=httpx.Timeout(60.0, connect=15.0),
        )

    def get_all_pages(self, space_key: str) -> list[WikiPage]:
        pages: list[WikiPage] = []
        start = 0
        limit = 50

        while True:
            resp = self.client.get(
                f"{self.api_base}/content",
                params={
                    "spaceKey": space_key,
                    "expand": "body.storage,version",
                    "limit": limit,
                    "start": start,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("results", []):
                page = self._parse_page(result, space_key)
                if page:
                    pages.append(page)

            if len(data.get("results", [])) < limit:
                break
            start += limit

        return pages

    def get_child_pages(self, parent_id: str, space_key: str) -> list[WikiPage]:
        pages: list[WikiPage] = []
        start = 0
        limit = 50

        while True:
            resp = self.client.get(
                f"{self.api_base}/content/{parent_id}/child/page",
                params={
                    "expand": "body.storage,version",
                    "limit": limit,
                    "start": start,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("results", []):
                page = self._parse_page(result, space_key)
                if page:
                    pages.append(page)
                    child_pages = self.get_child_pages(page.id, space_key)
                    pages.extend(child_pages)

            if len(data.get("results", [])) < limit:
                break
            start += limit

        return pages

    def _parse_page(self, result: dict, space_key: str) -> Optional[WikiPage]:
        page_id = result.get("id")
        title = result.get("title", "")
        body = result.get("body", {})
        storage = body.get("storage", {})
        content_html = storage.get("value", "")
        version = result.get("version", {}).get("number", 1)

        if not content_html:
            return None

        source_url = f"{self.base_url}/spaces/{space_key}/pages/{page_id}"

        soup = BeautifulSoup(content_html, "lxml")

        headings = []
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            for heading in soup.find_all(tag):
                heading_id = heading.get("id", "")
                heading_text = heading.get_text(strip=True)
                if heading_id:
                    headings.append({
                        "level": tag,
                        "id": heading_id,
                        "text": heading_text,
                    })

        image_urls = []

        for img in soup.find_all("img"):
            src = unescape(img.get("src", ""))
            if src and not src.startswith("data:"):
                if src.startswith("/"):
                    src = f"{self.base_url}{src}"
                image_urls.append(src)

        # Only inline images (ri:url) are candidates: ri:link points to pages,
        # not to images.
        urls_in_text = re.findall(
            r'ri:url[^>]*ri:value="([^"]+)"',
            content_html
        )
        for u in urls_in_text:
            u = unescape(u)
            if u not in image_urls:
                image_urls.append(u)

        attachments = self.get_page_attachments(page_id)
        for att in attachments:
            if _is_image(att.get("media_type", "")):
                dl = att.get("download_url")
                if dl and dl not in image_urls:
                    image_urls.append(dl)

        return WikiPage(
            id=page_id,
            title=title,
            space_key=space_key,
            content_html=content_html,
            source_url=source_url,
            version=version,
            headings=headings,
            image_urls=image_urls,
        )

    def download_image(self, url: str, output_dir: Path) -> Optional[Path]:
        # Attachment urls all end with ".../download", so fall back to the
        # attachment id to keep a distinct name for every image.
        parts = [p for p in url.split("/") if p]
        name = parts[-1].split("?")[0] if parts else ""
        if name in ("", "download", "content") and len(parts) >= 2:
            name = parts[-2]
        name = re.sub(r"[^a-zA-Z0-9._-]", "_", name) or f"image_{abs(hash(url))}"

        has_extension = bool(Path(name).suffix)
        output_path = output_dir / name
        if has_extension and output_path.exists():
            return output_path

        try:
            resp = self.client.get(url)
            resp.raise_for_status()

            # Some urls are pages, not images: keep only real images.
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            if not content_type.startswith("image/"):
                return None

            if not has_extension:
                extension = mimetypes.guess_extension(content_type) or ".png"
                name = f"{name}{extension}"
                output_path = output_dir / name
                if output_path.exists():
                    return output_path

            output_path.write_bytes(resp.content)
            return output_path
        except Exception:
            return None

    def get_page_attachments(self, page_id: str) -> list[dict]:
        attachments: list[dict] = []
        start = 0
        limit = 50

        while True:
            resp = self.client.get(
                f"{self.api_base}/content/{page_id}/child/attachment",
                params={"limit": limit, "start": start},
            )
            resp.raise_for_status()
            data = resp.json()

            for att in data.get("results", []):
                download_url = att.get("_links", {}).get("download", "")
                if download_url:
                    if download_url.startswith("/"):
                        download_url = f"{self.base_url}{download_url}"
                    attachments.append({
                        "id": att.get("id"),
                        "title": att.get("title"),
                        "media_type": att.get("metadata", {}).get("mediaType", ""),
                        "download_url": download_url,
                    })

            if len(data.get("results", [])) < limit:
                break
            start += limit

        return attachments

    def get_all_pages_for_all_spaces(self) -> dict[str, list[WikiPage]]:
        result: dict[str, list[WikiPage]] = {}
        for space_key in self.spaces:
            print(f"Crawling space: {space_key}")
            try:
                pages = self.get_all_pages(space_key)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (403, 404):
                    print(
                        f"  ⚠️  Space '{space_key}' non accessibile "
                        f"({status}) — salto"
                    )
                    result[space_key] = []
                    continue
                raise
            except httpx.RequestError as exc:
                print(
                    f"  ⚠️  Space '{space_key}' non raggiungibile "
                    f"({type(exc).__name__}) — salto"
                )
                result[space_key] = []
                continue
            print(f"  Found {len(pages)} pages in {space_key}")
            result[space_key] = pages
        return result

    def close(self):
        self.client.close()


def _is_image(media_type: str) -> bool:
    return media_type.startswith("image/")
