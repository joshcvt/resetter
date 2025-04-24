import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from atproto import Client, models
from atproto_client.models import (
    AppBskyFeedPost,
    AppBskyEmbedExternal,
)
import datetime

# when the vibecoding hits...

def scrape_rich_metadata(url: str):
    """
    Scrapes title, description, and og:image from a URL.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BlueskyBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=6)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        def get_meta(*names):
            for name in names:
                tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
                if tag and "content" in tag.attrs:
                    return tag["content"].strip()
            return ""

        title = get_meta("og:title", "twitter:title") or (soup.title.string.strip() if soup.title else "Untitled")
        description = get_meta("og:description", "twitter:description")
        image_url = get_meta("og:image", "twitter:image")

        return title[:300], description[:300], image_url if image_url.startswith("http") else ""
    except Exception as e:
        print(f"[Metadata Error] {e}")
        return "Untitled", "", ""


def download_image_as_bytes(url: str) -> Optional[bytes]:
    """
    Downloads an image from the given URL and returns the raw bytes.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BlueskyBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[Image Download Error] {e}")
        return None


def post_with_preview(client: Client, text: str):
    """
    Posts a Bluesky post with rich preview metadata and a proper thumbnail BlobRef.
    """
    url_pattern = re.compile(r"(https?://[^\s]+)")
    urls = url_pattern.findall(text)

    embed = None
    if urls:
        url = urls[0]
        title, description, thumb_url = scrape_rich_metadata(url)

        thumb_blob = None
        if thumb_url:
            thumb_bytes = download_image_as_bytes(thumb_url)
            if thumb_bytes:
                try:
                    uploaded_blob = client.com.atproto.repo.upload_blob(thumb_bytes)
                    thumb_blob = uploaded_blob.blob
                    print("successfully uploaded blob for thumb_url",thumb_url)
                except Exception as e:
                    print(f"[Thumbnail Upload Error] {e}")

        embed = AppBskyEmbedExternal.Main(
            external=AppBskyEmbedExternal.External(
                uri=url,
                title=title,
                description=description,
                thumb=thumb_blob,  # Must be a BlobRef or None
            )
        )

    post_record = AppBskyFeedPost.Record(
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        text=text,
        embed=embed
    )
    
    response = client.com.atproto.repo.create_record(
        data=models.ComAtprotoRepoCreateRecord.Data(
            repo=client.me.did,
            collection="app.bsky.feed.post",
            record=post_record.model_dump()
        )
    )

    return response
