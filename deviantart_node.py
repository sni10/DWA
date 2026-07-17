"""
DeviantArt Sender - ComfyUI Custom Node.

A custom ComfyUI node for uploading images to DeviantArt.
Finds the latest image in specified folder, uploads to Stash, and publishes.

Usage:
    1. Add the node to your ComfyUI workflow
    2. Configure client_id and client_secret from DeviantArt app
    3. Set folder_path to your output directory
    4. Configure tags, gallery, and other settings
    5. Run workflow - browser will open for authorization on first use
"""

import glob
import os
import re
import time
from pathlib import Path
from typing import Optional

import comfy.utils

from .da_auth import DeviantArtAuth
from .da_publish import publish_deviation
from .da_stash import upload_to_stash

# Display resolution options for dropdown
DISPLAY_RESOLUTION_OPTIONS = [
    "0 - Original",
    "1 - 400px",
    "2 - 600px",
    "3 - 800px",
    "4 - 900px",
    "5 - 1024px",
    "6 - 1280px",
    "7 - 1600px",
    "8 - 1920px",
]

# Mature level options for dropdown
MATURE_LEVEL_OPTIONS = ["none", "moderate", "strict"]

# Mature classification options (each as separate boolean)
MATURE_CLASSIFICATION_OPTIONS = ["nudity", "sexual", "gore", "language", "ideology"]

# Supported image extensions
SUPPORTED_EXTENSIONS = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"]


def find_latest_file(folder_path: str) -> Optional[str]:
    """
    Find the most recently created image file in folder.

    Args:
        folder_path: Path to folder containing images

    Returns:
        Path to latest file or None if no files found
    """
    all_files = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(folder_path, ext)
        all_files.extend(glob.glob(pattern))
        # Also check uppercase extensions
        all_files.extend(glob.glob(pattern.upper()))

    if not all_files:
        return None

    # Sort by creation time, get latest
    latest = max(all_files, key=os.path.getctime)
    return latest


def generate_title_from_filename(file_path: str) -> str:
    """
    Generate title from filename.

    Removes extension and replaces underscores with spaces.

    Args:
        file_path: Path to the file

    Returns:
        Clean title string
    """
    # Get filename without path
    filename = os.path.basename(file_path)

    # Remove extension
    name = os.path.splitext(filename)[0]

    # Replace underscores with spaces
    title = name.replace("_", " ")

    # Clean up multiple spaces
    title = re.sub(r"\s+", " ", title).strip()

    return title


def parse_tags(tags_string: str) -> list[str]:
    """
    Parse comma-separated tags string into list.

    Args:
        tags_string: Comma-separated tags (e.g., "art, digital, fantasy")

    Returns:
        List of cleaned tag strings
    """
    if not tags_string or not tags_string.strip():
        return []

    tags = [tag.strip() for tag in tags_string.split(",")]
    # Filter empty tags
    return [tag for tag in tags if tag]


def parse_display_resolution(resolution_option: str) -> int:
    """
    Parse display resolution from dropdown option.

    Args:
        resolution_option: Selected option (e.g., "0 - Original")

    Returns:
        Integer resolution code (0-8)
    """
    try:
        # Extract first character (the number)
        return int(resolution_option.split(" ")[0])
    except (ValueError, IndexError):
        return 0


def parse_galleryids(galleryids_string: str) -> Optional[list[str]]:
    """
    Parse comma-separated gallery UUIDs string into list.

    Args:
        galleryids_string: Comma-separated UUIDs
            (e.g., "14192C37-59DF-AB20-CBA7-6D9E917B05BB, 50DC32B0-...")

    Returns:
        List of UUID strings, or None if empty
    """
    if not galleryids_string or not galleryids_string.strip():
        return None

    # Split by comma and clean each UUID
    uuids = [uuid.strip() for uuid in galleryids_string.split(",")]
    # Filter empty strings
    uuids = [uuid for uuid in uuids if uuid]

    return uuids if uuids else None


class DeviantArtSender:
    """ComfyUI node for sending images to DeviantArt."""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        return {
            "required": {
                "images": ("IMAGE",),
                "folder_path": ("STRING", {
                    "default": "output",
                    "multiline": False,
                }),
                "client_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "client_secret": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "tags": ("STRING", {
                    "default": "digital art, ai generated",
                    "multiline": True,
                }),
                "display_resolution": (DISPLAY_RESOLUTION_OPTIONS, {
                    "default": DISPLAY_RESOLUTION_OPTIONS[0],
                }),
                "galleryids": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "is_ai_generated": ("BOOLEAN", {"default": True}),
                "is_mature": ("BOOLEAN", {"default": False}),
                "mature_level": (MATURE_LEVEL_OPTIONS, {
                    "default": MATURE_LEVEL_OPTIONS[0],
                }),
                "mature_nudity": ("BOOLEAN", {"default": False}),
                "mature_sexual": ("BOOLEAN", {"default": False}),
                "mature_gore": ("BOOLEAN", {"default": False}),
                "mature_language": ("BOOLEAN", {"default": False}),
                "mature_ideology": ("BOOLEAN", {"default": False}),
                "feature": ("BOOLEAN", {"default": True}),
                "allow_comments": ("BOOLEAN", {"default": True}),
                "allow_free_download": ("BOOLEAN", {"default": True}),
                "add_watermark": ("BOOLEAN", {"default": False}),
                "publish_after_stash": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "title": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "artist_comments": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "send"
    OUTPUT_NODE = True
    CATEGORY = "output"

    def send(
        self,
        images,
        folder_path: str,
        client_id: str,
        client_secret: str,
        tags: str,
        display_resolution: str,
        galleryids: str,
        is_ai_generated: bool,
        is_mature: bool,
        mature_level: str,
        mature_nudity: bool,
        mature_sexual: bool,
        mature_gore: bool,
        mature_language: bool,
        mature_ideology: bool,
        feature: bool,
        allow_comments: bool,
        allow_free_download: bool,
        add_watermark: bool,
        publish_after_stash: bool,
        artist_comments: str = "",
        title: str = "",
    ):
        """
        Send latest image from folder to DeviantArt.

        This method:
        1. Waits for file to be written (3 second delay)
        2. Finds latest image in folder
        3. Authenticates with DeviantArt (opens browser if needed)
        4. Uploads to Stash
        5. Publishes to DeviantArt

        Args:
            images: Input images (from ComfyUI pipeline)
            folder_path: Path to folder with output images
            client_id: DeviantArt application client ID
            client_secret: DeviantArt application client secret
            tags: Comma-separated tags
            display_resolution: Display resolution dropdown selection
            galleryids: Gallery UUID (optional)
            is_ai_generated: Mark as AI generated
            is_mature: Mark as mature content
            allow_comments: Allow comments
            allow_free_download: Allow free download

        Returns:
            Empty tuple (output node)
        """
        # Validate required fields
        if not client_id or not client_secret:
            print("ERROR: client_id and client_secret are required!")
            return ()

        if not folder_path:
            print("ERROR: folder_path is required!")
            return ()

        # Wait for file to be fully written
        print("Waiting for image to be saved...")
        time.sleep(3)

        # Find latest file
        print(f"Searching for latest image in: {folder_path}")
        latest_file = find_latest_file(folder_path)

        if not latest_file:
            print(f"ERROR: No image files found in {folder_path}")
            return ()

        print(f"Found latest file: {latest_file}")

        # Use title field if provided, otherwise generate from filename
        if title and title.strip():
            final_title = title.strip()[:50]
            print(f"Using title: {final_title}")
        else:
            final_title = generate_title_from_filename(latest_file)
            print(f"Generated title from filename: {final_title}")

        # Parse tags
        tags_list = parse_tags(tags)
        print(f"Tags: {tags_list}")

        # Parse display resolution
        resolution = parse_display_resolution(display_resolution)
        print(f"Display resolution: {resolution}")

        # Parse gallery IDs (supports multiple comma-separated UUIDs)
        gallery_list = parse_galleryids(galleryids)
        if gallery_list:
            print(f"Galleries: {gallery_list}")

        # 3 steps: authenticate, upload to Stash, publish.
        pbar = comfy.utils.ProgressBar(3)

        # Authenticate with DeviantArt
        print("Authenticating with DeviantArt...")
        auth = DeviantArtAuth(
            client_id=client_id,
            client_secret=client_secret,
        )

        access_token = auth.ensure_authenticated()
        if not access_token:
            print("ERROR: Authentication failed!")
            return ()

        print("Authentication successful!")
        pbar.update(1)

        # Upload to Stash
        print("Uploading to Stash...")
        stash_result = upload_to_stash(
            file_path=latest_file,
            access_token=access_token,
            title=final_title,
            artist_comments=artist_comments if artist_comments else None,
            tags=tags_list,
            is_ai_generated=is_ai_generated,
        )

        if not stash_result.success:
            print(f"ERROR: Stash upload failed: {stash_result.error}")
            return ()

        print(f"Stash upload successful! ItemID: {stash_result.itemid}")
        pbar.update(1)

        # Check if we should publish after stash
        if not publish_after_stash:
            print("Publish after stash is disabled. Image saved to Stash only.")
            pbar.update(1)  # nothing left to do — fill the bar
            return ()

        # Build mature classification list from individual booleans
        mature_classification_list = []
        if mature_nudity:
            mature_classification_list.append("nudity")
        if mature_sexual:
            mature_classification_list.append("sexual")
        if mature_gore:
            mature_classification_list.append("gore")
        if mature_language:
            mature_classification_list.append("language")
        if mature_ideology:
            mature_classification_list.append("ideology")

        # Determine mature_level to send (None if "none" selected)
        mature_level_value = mature_level if mature_level != "none" else None

        # Publish to DeviantArt
        print("Publishing to DeviantArt...")
        publish_result = publish_deviation(
            access_token=access_token,
            itemid=stash_result.itemid,
            tags=tags_list,
            display_resolution=resolution,
            galleryids=gallery_list,
            is_ai_generated=is_ai_generated,
            is_mature=is_mature,
            mature_level=mature_level_value,
            mature_classification=mature_classification_list if mature_classification_list else None,
            feature=feature,
            allow_comments=allow_comments,
            allow_free_download=allow_free_download,
            add_watermark=add_watermark,
        )

        if not publish_result.success:
            print(f"ERROR: Publish failed: {publish_result.error}")
            return ()

        print(f"Published successfully!")
        print(f"  URL: {publish_result.url}")
        pbar.update(1)

        return ()


# ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "DeviantArtSender": DeviantArtSender,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DeviantArtSender": "🎨 Send to DeviantArt",
}
