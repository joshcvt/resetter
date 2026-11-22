import re
import requests
from typing import Optional, Tuple
from bs4 import BeautifulSoup
import datetime

# Talks to Bluesky's XRPC HTTP API directly with requests instead of the atproto SDK:
# the SDK took ~20 s and ~470 MB just to import in Lambda, for the three calls we need.
# https://docs.bsky.app/docs/advanced-guides/posts

DEFAULT_PDS = "https://bsky.social"
XRPC_TIMEOUT = 15


class BskySession:
    """Logged-in session: the access token, the account DID, and the PDS to send writes to."""

    def __init__(self, handle: str, app_password: str, pds: str = DEFAULT_PDS):
        resp = requests.post(f"{pds}/xrpc/com.atproto.server.createSession",
                             json={"identifier": handle, "password": app_password},
                             timeout=XRPC_TIMEOUT)
        _raise_for_xrpc(resp, "createSession")
        body = resp.json()
        self.did = body["did"]
        self.access_jwt = body["accessJwt"]
        # bsky.social is an entryway; writes belong on the account's own PDS, named in its DID document
        self.pds = _pds_from_did_doc(body.get("didDoc")) or pds

    def call(self, method: str, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_jwt}"
        resp = requests.post(f"{self.pds}/xrpc/{method}", headers=headers, timeout=XRPC_TIMEOUT, **kwargs)
        _raise_for_xrpc(resp, method)
        return resp.json()


def _pds_from_did_doc(did_doc) -> Optional[str]:
    for svc in (did_doc or {}).get("service", []):
        if svc.get("id", "").endswith("#atproto_pds") and svc.get("serviceEndpoint"):
            return svc["serviceEndpoint"].rstrip("/")
    return None


def _raise_for_xrpc(resp, method: str):
    if resp.ok:
        return
    try:
        err = resp.json()
        detail = f"{err.get('error')}: {err.get('message')}"
    except ValueError:
        detail = resp.text[:200]
    raise RuntimeError(f"Bluesky {method} failed with HTTP {resp.status_code}: {detail}")


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


def download_image_as_bytes(url: str) -> Optional[Tuple[bytes, str]]:
    """
    Downloads an image from the given URL and returns (raw bytes, MIME type).
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BlueskyBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=6)
        resp.raise_for_status()
        mime = resp.headers.get("Content-Type", "").split(";")[0].strip()
        return resp.content, (mime if mime.startswith("image/") else "image/jpeg")
    except Exception as e:
        print(f"[Image Download Error] {e}")
        return None


def post_with_preview(session: BskySession, text: str):
    """
    Posts a Bluesky post with rich preview metadata and clickable URLs.
    """
    url_pattern = re.compile(r"(https?://[^\s]+)")
    matches = list(url_pattern.finditer(text))

    embed = None
    facets = []

    # Build facets so URLs become clickable
    for m in matches:
        url = m.group(1)

        # Bluesky facets require byte offsets, not character offsets
        start_byte = len(text[:m.start()].encode("utf-8"))
        end_byte = len(text[:m.end()].encode("utf-8"))

        facets.append({
            "index": {
                "byteStart": start_byte,
                "byteEnd": end_byte,
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url,
                }
            ],
        })

    # Build rich preview embed using the first URL (same as your existing behavior)
    if matches:
        url = matches[0].group(1)
        title, description, thumb_url = scrape_rich_metadata(url)

        external = {"uri": url, "title": title, "description": description}
        if thumb_url:
            thumb = download_image_as_bytes(thumb_url)
            if thumb:
                thumb_bytes, thumb_mime = thumb
                try:
                    # the returned blob ref goes into the record as-is
                    external["thumb"] = session.call("com.atproto.repo.uploadBlob", data=thumb_bytes,
                                                     headers={"Content-Type": thumb_mime})["blob"]
                    print("successfully uploaded blob for thumb_url",thumb_url)
                except Exception as e:
                    print(f"[Thumbnail Upload Error] {e}")
        else:
            print("no preview image found for", url)

        embed = {"$type": "app.bsky.embed.external", "external": external}

    post_record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if facets:
        post_record["facets"] = facets
    if embed:
        post_record["embed"] = embed

    # returns {"uri": "at://...", "cid": "..."}
    return session.call("com.atproto.repo.createRecord",
                        json={"repo": session.did, "collection": "app.bsky.feed.post", "record": post_record})