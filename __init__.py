"""
DeviantArt Sender - ComfyUI Custom Node Package.

A custom ComfyUI node for uploading images to DeviantArt.
Authenticates via OAuth2, uploads to Stash, and publishes.

Installation:
    Copy the DWA folder to your ComfyUI custom_nodes directory.

Usage:
    1. Add "Send to DeviantArt" node to your workflow
    2. Configure client_id and client_secret from your DeviantArt app
    3. Set folder_path to your output directory
    4. Configure tags, gallery, and other settings
    5. Run workflow - browser opens for auth on first use
"""

from .deviantart_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
