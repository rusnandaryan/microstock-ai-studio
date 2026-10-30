"""Batch item data structures and post-processing engine.

Handles resolution enforcement, smart downsampling, Freepik padding, and preview generation.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

from PIL import Image

from . import config
from .metadata import ImageMetadata

PREVIEW_MAX_SIDE = 900  # px – lightweight thumbnails for the UI grid


# Data models
@dataclass
class BatchItem:
    index: int
    variation: str
    final_prompt: str
    filename: str = ""
    image_bytes: Optional[bytes] = None      # full-resolution export file
    preview_bytes: Optional[bytes] = None    # downscaled JPEG for display
    mime_type: str = "image/jpeg"
    width: int = 0
    height: int = 0
    metadata: Optional[ImageMetadata] = None
    image_error: Optional[str] = None
    metadata_error: Optional[str] = None
    elapsed: float = 0.0

    @property
    def ok(self) -> bool:
        return self.image_bytes is not None


@dataclass
class BatchSettings:
    enhanced_prompt: str = ""
    style_name: str = ""
    aspect_ratio: str = "16:9"
    image_model: str = "Gemini Vision"
    hf_api_key: Optional[str] = None
    image_size: str = "1K"
    batch_size: int = 4
    max_concurrency: int = config.DEFAULT_MAX_CONCURRENCY
    export_format: str = "JPEG"
    file_prefix: str = "microstock"
    extra: dict = field(default_factory=dict)


def _pad_jpeg_to_min_size(data: bytes, min_bytes: int) -> bytes:
    """Pad a valid JPEG with standard COM (0xFF 0xFE) comment segments to guarantee min_bytes.

    Guarantees >= min_bytes without altering pixel data or image dimensions.
    Standard microstock platforms (Freepik, Vecteezy, Shutterstock) accept standard JPEG COM segments.
    """
    diff = min_bytes - len(data)
    if diff <= 0 or not data.endswith(b"\xff\xd9"):
        return data

    header = data[:-2]
    eoi = data[-2:]
    chunks = bytearray()
    while diff > 0:
        chunk_payload_size = min(diff - 4, 65530)
        if chunk_payload_size <= 0:
            chunks.extend(b"\xff\xfe\x00\x04")
            diff -= 4
            break
        length_field = chunk_payload_size + 2
        chunks.extend(b"\xff\xfe" + length_field.to_bytes(2, "big") + (b" " * chunk_payload_size))
        diff -= (chunk_payload_size + 4)
    return bytes(header) + bytes(chunks) + eoi


def finalize_image(
    raw: bytes,
    export_format: str,
    enforce_microstock_res: bool = False,
    enforce_min_filesize: bool = False,
    max_target_pixels: Optional[int] = None,
    jpeg_quality: int = 95,
) -> Tuple[bytes, bytes, str, int, int]:
    """Convert to export format and build preview.

    - enforce_microstock_res: Guarantees >= 4MP (Adobe Stock / Shutterstock minimum).
    - enforce_min_filesize: Guarantees >= 4MB JPEG file size (Freepik / Vecteezy minimum).
    - max_target_pixels: Optional pixel cap (e.g. config.SMART_MICROSTOCK_TARGET_PIXELS for Smart Microstock).
    - jpeg_quality: JPEG compression quality (default 95: optimal size-to-fidelity ratio).
    Returns (export_bytes, preview_bytes, mime_type, width, height).
    """
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        width, height = im.size
        rgb = im.convert("RGB") if im.mode not in ("RGB",) else im.copy()

    total_pixels = width * height
    mp = total_pixels / 1_000_000

    # 1. Enforce minimum resolution >= 4 MP (MANDATORY when upscale is active)
    if enforce_microstock_res and total_pixels < config.TARGET_MIN_PIXELS:
        scale_res = math.sqrt(config.TARGET_MIN_PIXELS / max(1, total_pixels))
        new_w = max(1, int(math.ceil(width * scale_res)))
        new_h = max(1, int(math.ceil(height * scale_res)))
        rgb = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = rgb.size
        total_pixels = width * height
        mp = total_pixels / 1_000_000

    # 2. Smart Microstock cap: Downsample if exceeding target (e.g. ~8.3 MP)
    if max_target_pixels and total_pixels > max_target_pixels:
        scale_down = math.sqrt(max_target_pixels / total_pixels)
        new_w = max(1, int(round(width * scale_down)))
        new_h = max(1, int(round(height * scale_down)))
        rgb = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = rgb.size
        total_pixels = width * height
        mp = total_pixels / 1_000_000

    # 3. Downscale only if image exceeds the extreme 100MP microstock cap
    if total_pixels > 0 and mp > config.MAX_IMAGE_MEGAPIXELS:
        scale = math.sqrt(98_000_000 / total_pixels)
        new_w = max(1, int(round(width * scale)))
        new_h = max(1, int(round(height * scale)))
        rgb = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = rgb.size

    if export_format.upper() == "PNG":
        buf = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True)
        export_bytes = buf.getvalue()
        mime = "image/png"
    else:
        # Standard high-quality JPEG
        buf = io.BytesIO()
        save_kwargs = {"quality": jpeg_quality, "optimize": True, "dpi": (300, 300)}
        if jpeg_quality >= 98:
            save_kwargs["subsampling"] = 0
        rgb.save(buf, format="JPEG", **save_kwargs)
        export_bytes = buf.getvalue()
        mime = "image/jpeg"

        # 4. Enforce minimum file size >= 4 MB (OPTIONAL checkbox)
        if enforce_min_filesize and len(export_bytes) < config.MIN_FILE_SIZE_BYTES:
            export_bytes = _pad_jpeg_to_min_size(export_bytes, config.MIN_FILE_SIZE_BYTES)

    preview = rgb.copy()
    preview.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE), Image.LANCZOS)
    pbuf = io.BytesIO()
    preview.save(pbuf, format="JPEG", quality=85)
    return export_bytes, pbuf.getvalue(), mime, width, height
