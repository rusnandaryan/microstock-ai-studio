"""Batch Generation Engine.

Generates N image variations in parallel (asyncio + bounded semaphores) and,
for every slot, runs the metadata call concurrently with the image call.
"""
from __future__ import annotations

import asyncio
import base64
import io
import re
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from google import genai
from PIL import Image

from . import config
from .metadata import ImageMetadata, generate_metadata_async
from .rate_limit import GenerationError, TransientError, retry_async

PREVIEW_MAX_SIDE = 900  # px – lightweight thumbnails for the UI grid


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
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
    enhanced_prompt: str
    style_name: str
    aspect_ratio: str
    image_model: str
    hf_api_key: Optional[str] = None
    image_size: str = config.DEFAULT_IMAGE_SIZE
    batch_size: int = 4
    max_concurrency: int = config.DEFAULT_MAX_CONCURRENCY
    export_format: str = "JPEG"              # "JPEG" (q=95) or "PNG"
    file_prefix: str = "microstock"
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Prompt assembly
# --------------------------------------------------------------------------- #
def build_image_prompt(enhanced_prompt: str, style_name: str, variation: str) -> str:
    style = config.STYLES[style_name]
    return (
        f"{enhanced_prompt.strip()}\n\n"
        f"Visual style: {style.directive}\n"
        f"{variation}\n"
        "Quality: ultra-detailed, professional commercial microstock quality, sharp, "
        "well-exposed, no artifacts, no watermark, no signature, no text overlays, no logos."
    )


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "image"


# --------------------------------------------------------------------------- #
# Single image call
# --------------------------------------------------------------------------- #
def _extract_image(response_obj) -> Tuple[bytes, str]:
    """Return (raw_bytes, mime_type) from response (generate_images, generate_content, or interactions)."""
    # 1. From client.models.generate_images (types.GenerateImagesResponse)
    generated_images = getattr(response_obj, "generated_images", None)
    if generated_images:
        first = generated_images[0]
        img_obj = getattr(first, "image", None)
        if img_obj and getattr(img_obj, "image_bytes", None):
            return img_obj.image_bytes, "image/jpeg"

    # 2. Direct parts inspection (response.parts or candidate parts)
    parts = getattr(response_obj, "parts", None) or []
    candidates = getattr(response_obj, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        if content and getattr(content, "parts", None):
            parts.extend(content.parts)

    for part in parts:
        if hasattr(part, "as_image"):
            try:
                pil_im = part.as_image()
                buf = io.BytesIO()
                pil_im.save(buf, format="JPEG", quality=95)
                return buf.getvalue(), "image/jpeg"
            except Exception:
                pass
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            data = inline.data
            mime = getattr(inline, "mime_type", None) or "image/jpeg"
            raw = base64.b64decode(data) if isinstance(data, str) else bytes(data)
            return raw, mime

    # 3. Text explanation or refusal
    text = (getattr(response_obj, "text", None) or getattr(response_obj, "output_text", None) or "").strip()
    if text:
        raise GenerationError(f"Model tidak menghasilkan gambar. Keterangan: {text[:200]}")
    raise TransientError("Model tidak mengembalikan gambar")


def generate_image_sync(client: genai.Client, prompt: str, aspect_ratio: str,
                        image_model: str, image_size: str) -> Tuple[bytes, str]:
    """Call Google Gemini Nano Banana or Imagen image model."""
    from google.genai import types

    if image_model == "pollinations":
        import urllib.parse
        import urllib.request
        encoded = urllib.parse.quote(prompt[:400])
        url = f"https://image.pollinations.ai/prompt/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
            if len(data) > 1000:
                return data, "image/jpeg"
        raise TransientError("Gagal mengambil gambar dari Pollinations.")

    if "imagen" in image_model:
        res = client.models.generate_images(
            model=image_model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/jpeg",
            ),
        )
        return _extract_image(res)

    # Gemini 3 Nano Banana models (e.g. gemini-3.1-flash-lite-image, gemini-3.1-flash-image, gemini-3-pro-image)
    cfg = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
    )
    res = client.models.generate_content(
        model=image_model,
        contents=prompt,
        config=cfg,
    )
    return _extract_image(res)


def finalize_image(raw: bytes, export_format: str, enforce_microstock_res: bool = False) -> Tuple[bytes, bytes, str, int, int]:
    """Convert to export format (max quality) and build preview.

    Auto-upscale to 4MP is disabled per user request (user will upscale manually).
    Resolution and aspect ratio from the original image are preserved intact.
    Returns (export_bytes, preview_bytes, mime_type, width, height).
    """
    import math

    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        width, height = im.size
        rgb = im.convert("RGB") if im.mode not in ("RGB",) else im.copy()

    total_pixels = width * height
    mp = total_pixels / 1_000_000

    # Downscale only if image exceeds the extreme 100MP microstock cap
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
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=95, subsampling=0, optimize=True, dpi=(300, 300))
        export_bytes = buf.getvalue()
        mime = "image/jpeg"

    preview = rgb.copy()
    preview.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE), Image.LANCZOS)
    pbuf = io.BytesIO()
    preview.save(pbuf, format="JPEG", quality=85)
    return export_bytes, pbuf.getvalue(), mime, width, height


# --------------------------------------------------------------------------- #
# Batch orchestration
# --------------------------------------------------------------------------- #
ProgressCb = Callable[[str, BatchItem], None]   # event, item
LogCb = Callable[[str], None]


async def _process_slot(
    client: genai.Client,
    item: BatchItem,
    s: BatchSettings,
    image_sem: asyncio.Semaphore,
    text_sem: asyncio.Semaphore,
    on_progress: Optional[ProgressCb],
    on_log: Optional[LogCb],
    do_image: bool = True,
    do_metadata: bool = True,
) -> BatchItem:
    t0 = time.perf_counter()
    label = f"Image #{item.index + 1}"

    async def image_task() -> None:
        async with image_sem:
            try:
                # Slight spacing between items to avoid instant Free Tier RPM burst
                if item.index > 0:
                    await asyncio.sleep(item.index * 1.5)

                raw, _ = await retry_async(
                    lambda: asyncio.to_thread(
                        generate_image_sync, client, item.final_prompt,
                        s.aspect_ratio, s.image_model, s.image_size),
                    label=label, on_retry=on_log,
                )
                exp, prev, mime, w, h = await asyncio.to_thread(finalize_image, raw, s.export_format)
                item.image_bytes, item.preview_bytes = exp, prev
                item.mime_type, item.width, item.height = mime, w, h
            except Exception as exc:  # noqa: BLE001
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    item.image_error = "⚠️ Batas kuota gratis Gemini tercapai untuk saat ini. Mohon tunggu 1-2 menit sebelum mencoba lagi."
                else:
                    item.image_error = err_str
        if on_progress:
            on_progress("image", item)

    async def metadata_task() -> None:
        async with text_sem:
            try:
                item.metadata = await generate_metadata_async(
                    client, s.enhanced_prompt, s.style_name, item.variation,
                    label=f"Metadata #{item.index + 1}", on_retry=on_log,
                )
            except Exception as exc:  # noqa: BLE001
                item.metadata_error = str(exc)
        if on_progress:
            on_progress("metadata", item)

    # Image + metadata for the same slot run concurrently (metadata only needs
    # the prompt + aesthetic, so it doesn't have to wait for pixels).
    jobs = []
    if do_image:
        jobs.append(image_task())
    if do_metadata:
        jobs.append(metadata_task())
    await asyncio.gather(*jobs)
    item.elapsed = time.perf_counter() - t0
    return item


def plan_batch(s: BatchSettings) -> List[BatchItem]:
    """Create the N slot definitions (prompt variation + filename) for a batch."""
    n = max(1, min(10, int(s.batch_size)))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    slug = slugify(f"{s.file_prefix}-{s.enhanced_prompt[:60]}")
    ext = "png" if s.export_format.upper() == "PNG" else "jpg"

    items: List[BatchItem] = []
    for i in range(n):
        variation = config.VARIATION_DIRECTIVES[i % len(config.VARIATION_DIRECTIVES)]
        items.append(BatchItem(
            index=i,
            variation=variation,
            final_prompt=build_image_prompt(s.enhanced_prompt, s.style_name, variation),
            filename=f"{slug}-{stamp}-{i + 1:02d}.{ext}",
        ))
    return items


async def process_items_async(
    client: genai.Client,
    items: List[BatchItem],
    s: BatchSettings,
    on_progress: Optional[ProgressCb] = None,
    on_log: Optional[LogCb] = None,
) -> List[BatchItem]:
    """Run all slots concurrently, bounded by semaphores (rate-limit friendly)."""
    image_sem = asyncio.Semaphore(max(1, s.max_concurrency))
    text_sem = asyncio.Semaphore(max(2, s.max_concurrency * 2))  # text calls are cheap
    await asyncio.gather(*[
        _process_slot(client, it, s, image_sem, text_sem, on_progress, on_log)
        for it in items
    ])
    return items


def run_batch(
    client: genai.Client,
    s: BatchSettings,
    on_progress: Optional[ProgressCb] = None,
    on_log: Optional[LogCb] = None,
) -> List[BatchItem]:
    """Sync entry point (Streamlit scripts are synchronous)."""
    items = plan_batch(s)
    return asyncio.run(process_items_async(client, items, s, on_progress, on_log))


def retry_failed(
    client: genai.Client,
    items: List[BatchItem],
    s: BatchSettings,
    on_progress: Optional[ProgressCb] = None,
    on_log: Optional[LogCb] = None,
) -> List[BatchItem]:
    """Re-run only slots whose image or metadata failed. Mutates items in place."""
    failed = [it for it in items if not it.ok or it.metadata is None]
    for it in failed:
        if not it.ok:
            it.image_error = None
        if it.metadata is None:
            it.metadata_error = None
    if failed:
        asyncio.run(_retry_async(client, failed, s, on_progress, on_log))
    return items


async def _retry_async(client, failed, s, on_progress, on_log):
    image_sem = asyncio.Semaphore(max(1, s.max_concurrency))
    text_sem = asyncio.Semaphore(max(2, s.max_concurrency * 2))
    await asyncio.gather(*[
        _process_slot(client, it, s, image_sem, text_sem, on_progress, on_log,
                      do_image=not it.ok, do_metadata=it.metadata is None)
        for it in failed
    ])
