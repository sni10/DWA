"""
DeviantArt Publish module for ComfyUI node.

Handles publishing deviations from Stash via /stash/publish endpoint.
Requires itemid from successful Stash upload.
"""

from typing import Optional

import requests

# API URL
API_STASH_PUBLISH_URL = "https://www.deviantart.com/api/v1/oauth2/stash/publish"


class PublishResult:
    """Result of a publish operation."""

    def __init__(
        self,
        success: bool,
        deviationid: Optional[str] = None,
        url: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """
        Initialize publish result.

        Args:
            success: Whether publish was successful
            deviationid: DeviantArt deviation ID
            url: URL to the published deviation
            error: Error message if failed
        """
        self.success = success
        self.deviationid = deviationid
        self.url = url
        self.error = error


def publish_deviation(
    access_token: str,
    itemid: int,
    is_mature: bool = False,
    mature_level: Optional[str] = None,
    mature_classification: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    display_resolution: int = 0,
    galleryids: Optional[list[str]] = None,
    allow_comments: bool = True,
    allow_free_download: bool = True,
    add_watermark: bool = False,
    is_ai_generated: bool = True,
    noai: bool = False,
    feature: bool = True,
) -> PublishResult:
    """
    Publish a deviation from Stash to DeviantArt.

    Args:
        access_token: Valid OAuth access token
        itemid: Stash item ID from upload_to_stash result
        is_mature: Whether content is mature/adult
        mature_level: Maturity level (strict, moderate)
        mature_classification: List of mature content types
        tags: List of tags for the deviation
        display_resolution: Display resolution setting:
            0 = original, 1 = 400px, 2 = 600px, 3 = 800px,
            4 = 900px, 5 = 1024px, 6 = 1280px, 7 = 1600px, 8 = 1920px
        galleryids: List of gallery folder UUIDs to publish to
        allow_comments: Allow comments on deviation
        allow_free_download: Allow free download
        add_watermark: Add watermark (only works if display_resolution > 0)
        is_ai_generated: Whether content is AI generated
        noai: Opt out of AI training
        feature: Feature this deviation

    Returns:
        PublishResult with deviationid and url on success, error on failure
    """
    # Build request data as list of tuples to properly handle arrays
    # DeviantArt API expects array params as repeated keys: tags[]=x&tags[]=y
    params: list[tuple[str, object]] = [
        ("access_token", access_token),
        ("itemid", itemid),
        ("is_mature", 1 if is_mature else 0),
        ("feature", 1 if feature else 0),
        ("allow_comments", 1 if allow_comments else 0),
        ("display_resolution", display_resolution),
        ("allow_free_download", 1 if allow_free_download else 0),
        ("is_ai_generated", 1 if is_ai_generated else 0),
        ("noai", 1 if noai else 0),
    ]

    if mature_level:
        params.append(("mature_level", mature_level))

    if mature_classification:
        for classification in mature_classification:
            params.append(("mature_classification[]", classification))

    if tags:
        for tag in tags:
            params.append(("tags[]", tag))

    if add_watermark and display_resolution > 0:
        params.append(("add_watermark", 1))

    if galleryids:
        for gallery_uuid in galleryids:
            params.append(("galleryids[]", gallery_uuid))

    try:
        print(f"Publishing deviation with itemid={itemid}")
        print(f"Tags being sent: {tags}")

        response = requests.post(
            API_STASH_PUBLISH_URL,
            data=params,
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("status") == "success":
            deviationid = result.get("deviationid")
            url = result.get("url")

            print(f"Published successfully!")
            print(f"  Deviation ID: {deviationid}")
            print(f"  URL: {url}")

            return PublishResult(
                success=True,
                deviationid=deviationid,
                url=url,
            )

        error_msg = result.get(
            "error_description", result.get("error", "Unknown error")
        )
        print(f"Publish failed: {error_msg}")
        return PublishResult(success=False, error=error_msg)

    except requests.RequestException as e:
        error_msg = f"Publish request failed: {e}"
        print(f"ERROR: {error_msg}")
        return PublishResult(success=False, error=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during publish: {e}"
        print(f"ERROR: {error_msg}")
        return PublishResult(success=False, error=error_msg)
