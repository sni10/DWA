"""
DeviantArt Stash upload module for ComfyUI node.

Handles uploading files to DeviantArt Stash via /stash/submit endpoint.
Returns itemid, stack, and stackid for subsequent publish operation.
"""

from pathlib import Path
from typing import Optional

import requests

# API URL
API_STASH_SUBMIT_URL = "https://www.deviantart.com/api/v1/oauth2/stash/submit"


def get_content_type(file_path: Path) -> str:
    """
    Get MIME content type based on file extension.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    ext = file_path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return content_types.get(ext, "application/octet-stream")


def to_base36(number: int) -> str:
    """
    Convert integer to base36 string for sta.sh URL.

    Args:
        number: Integer itemid from API response

    Returns:
        Base36 encoded string (lowercase)
    """
    if number == 0:
        return "0"

    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = []

    while number:
        number, remainder = divmod(number, 36)
        result.append(chars[remainder])

    return "".join(reversed(result))


class StashUploadResult:
    """Result of a Stash upload operation."""

    def __init__(
        self,
        success: bool,
        itemid: Optional[int] = None,
        stack: Optional[str] = None,
        stackid: Optional[int] = None,
        stash_url: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """
        Initialize upload result.

        Args:
            success: Whether upload was successful
            itemid: Stash item ID (required for publish)
            stack: Stack name (optional)
            stackid: Stack ID (optional)
            stash_url: URL to view item in Stash
            error: Error message if failed
        """
        self.success = success
        self.itemid = itemid
        self.stack = stack
        self.stackid = stackid
        self.stash_url = stash_url
        self.error = error


def upload_to_stash(
    file_path: str,
    access_token: str,
    title: Optional[str] = None,
    artist_comments: Optional[str] = None,
    tags: Optional[list[str]] = None,
    original_url: Optional[str] = None,
    is_dirty: bool = False,
    noai: bool = False,
    is_ai_generated: bool = True,
    stack: Optional[str] = None,
    stackid: Optional[int] = None,
) -> StashUploadResult:
    """
    Upload a file to DeviantArt Stash.

    Args:
        file_path: Path to the image file
        access_token: Valid OAuth access token
        title: Title for the deviation (max 50 chars)
        artist_comments: Artist's description/comments
        tags: List of tags
        original_url: URL to original source
        is_dirty: Whether content contains adult themes
        noai: Opt out of AI training
        is_ai_generated: Whether content is AI generated
        stack: Stack name to add item to
        stackid: Stack ID to add item to

    Returns:
        StashUploadResult with itemid on success, error on failure
    """
    path = Path(file_path)

    if not path.exists():
        return StashUploadResult(
            success=False,
            error=f"File not found: {file_path}"
        )

    # Build request data as list of tuples to properly handle arrays
    # DeviantArt API expects array params as repeated keys: tags[]=x&tags[]=y
    data: list[tuple[str, object]] = [("access_token", access_token)]

    if title:
        # Truncate title to 50 characters (API limit)
        data.append(("title", title[:50]))

    if artist_comments:
        data.append(("artist_comments", artist_comments))

    if tags:
        for tag in tags:
            data.append(("tags[]", tag))

    if original_url:
        data.append(("original_url", original_url))

    if is_dirty:
        data.append(("is_dirty", "1"))

    if noai:
        data.append(("noai", "1"))

    if is_ai_generated:
        data.append(("is_ai_generated", "1"))

    if stack:
        data.append(("stack", stack))

    if stackid:
        data.append(("stackid", stackid))

    try:
        print(f"Uploading file to Stash: {path.name}")
        if tags:
            print(f"Tags being sent: {tags}")

        with path.open("rb") as fh:
            files = {
                "file": (path.name, fh, get_content_type(path)),
            }

            response = requests.post(
                API_STASH_SUBMIT_URL,
                data=data,
                files=files,
                timeout=120,  # Longer timeout for file upload
            )
            response.raise_for_status()

        result = response.json()

        if result.get("status") == "success":
            itemid = result.get("itemid")
            if not itemid:
                return StashUploadResult(
                    success=False,
                    error="No itemid in response"
                )

            # Generate stash URL from itemid
            base36_id = to_base36(itemid)
            stash_url = f"https://sta.sh/0{base36_id}"

            print(f"File uploaded to Stash successfully!")
            print(f"  ItemID: {itemid}")
            print(f"  URL: {stash_url}")

            return StashUploadResult(
                success=True,
                itemid=itemid,
                stack=result.get("stack"),
                stackid=result.get("stackid"),
                stash_url=stash_url,
            )

        error_msg = result.get(
            "error_description", result.get("error", "Unknown error")
        )
        return StashUploadResult(success=False, error=error_msg)

    except requests.RequestException as e:
        error_msg = f"Stash upload request failed: {e}"
        print(f"ERROR: {error_msg}")
        return StashUploadResult(success=False, error=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during stash upload: {e}"
        print(f"ERROR: {error_msg}")
        return StashUploadResult(success=False, error=error_msg)
