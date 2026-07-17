"""
Tests for DWA - DeviantArt Sender ComfyUI Node.
Tests only pure utility functions. No comfy dependency.
"""
import os
import tempfile
from pathlib import Path

import pytest

# ── Import what we CAN import directly (no comfy dependency) ──
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from da_stash import get_content_type, to_base36, StashUploadResult
from da_publish import PublishResult


# ── Functions copied from deviantart_node.py for testing ──
# (can't import that file — it imports comfy which is ComfyUI-only)

import glob
import re
from typing import Optional

SUPPORTED_EXTENSIONS = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"]


def find_latest_file(folder_path: str) -> Optional[str]:
    all_files = []
    for ext in SUPPORTED_EXTENSIONS:
        pattern = os.path.join(folder_path, ext)
        all_files.extend(glob.glob(pattern))
        all_files.extend(glob.glob(pattern.upper()))
    if not all_files:
        return None
    latest = max(all_files, key=os.path.getctime)
    return latest


def generate_title_from_filename(file_path: str) -> str:
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    title = name.replace("_", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def parse_tags(tags_string: str) -> list:
    if not tags_string or not tags_string.strip():
        return []
    tags = [tag.strip() for tag in tags_string.split(",")]
    return [tag for tag in tags if tag]


def parse_display_resolution(resolution_option: str) -> int:
    try:
        return int(resolution_option.split(" ")[0])
    except (ValueError, IndexError):
        return 0


def parse_galleryids(galleryids_string: str) -> Optional[list]:
    if not galleryids_string or not galleryids_string.strip():
        return None
    uuids = [uuid.strip() for uuid in galleryids_string.split(",")]
    uuids = [uuid for uuid in uuids if uuid]
    return uuids if uuids else None


# ═══════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════


class TestParseTags:
    def test_basic(self):
        assert parse_tags("art, digital, fantasy") == ["art", "digital", "fantasy"]

    def test_single(self):
        assert parse_tags("solo") == ["solo"]

    def test_empty(self):
        assert parse_tags("") == []

    def test_whitespace(self):
        assert parse_tags("   ") == []

    def test_trailing_commas(self):
        assert parse_tags("a, b, ,") == ["a", "b"]

    def test_strips(self):
        assert parse_tags("  hello ,  world  ") == ["hello", "world"]


class TestParseDisplayResolution:
    def test_original(self):
        assert parse_display_resolution("0 - Original") == 0

    def test_1920(self):
        assert parse_display_resolution("8 - 1920px") == 8

    def test_invalid(self):
        assert parse_display_resolution("garbage") == 0

    def test_empty(self):
        assert parse_display_resolution("") == 0


class TestParseGalleryIds:
    def test_single(self):
        assert parse_galleryids("14192C37-59DF-AB20-CBA7-6D9E917B05BB") == ["14192C37-59DF-AB20-CBA7-6D9E917B05BB"]

    def test_multiple(self):
        assert parse_galleryids("AAA-BBB, CCC-DDD") == ["AAA-BBB", "CCC-DDD"]

    def test_empty(self):
        assert parse_galleryids("") is None

    def test_whitespace(self):
        assert parse_galleryids("   ") is None


class TestGenerateTitle:
    def test_underscores(self):
        assert generate_title_from_filename("/path/to/my_art_piece.png") == "my art piece"

    def test_multiple_underscores(self):
        assert generate_title_from_filename("a___b.jpg") == "a b"

    def test_simple(self):
        assert generate_title_from_filename("hello.bmp") == "hello"

    def test_windows_path(self):
        assert generate_title_from_filename("C:/Users/output/cool_image_01.png") == "cool image 01"


class TestFindLatestFile:
    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            assert find_latest_file(d) is None

    def test_finds_png(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "test.png"
            f.write_bytes(b"x")
            assert "test.png" in find_latest_file(d)

    def test_finds_latest(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "old.png").write_bytes(b"1")
            time.sleep(0.05)
            (Path(d) / "new.jpg").write_bytes(b"2")
            assert "new.jpg" in find_latest_file(d)

    def test_ignores_txt(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "file.txt").write_bytes(b"x")
            assert find_latest_file(d) is None


class TestToBase36:
    def test_zero(self):
        assert to_base36(0) == "0"

    def test_35(self):
        assert to_base36(35) == "z"

    def test_36(self):
        assert to_base36(36) == "10"

    def test_large(self):
        assert to_base36(46656) == "1000"


class TestGetContentType:
    def test_png(self):
        assert get_content_type(Path("x.png")) == "image/png"

    def test_jpg(self):
        assert get_content_type(Path("x.jpg")) == "image/jpeg"

    def test_jpeg(self):
        assert get_content_type(Path("x.jpeg")) == "image/jpeg"

    def test_gif(self):
        assert get_content_type(Path("x.gif")) == "image/gif"

    def test_unknown(self):
        assert get_content_type(Path("x.xyz")) == "application/octet-stream"


class TestStashUploadResult:
    def test_success(self):
        r = StashUploadResult(success=True, itemid=123)
        assert r.success and r.itemid == 123

    def test_failure(self):
        r = StashUploadResult(success=False, error="oops")
        assert not r.success and r.error == "oops"


class TestPublishResult:
    def test_success(self):
        r = PublishResult(success=True, url="https://example.com")
        assert r.success and r.url == "https://example.com"

    def test_failure(self):
        r = PublishResult(success=False, error="fail")
        assert not r.success and r.error == "fail"

