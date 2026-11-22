"""Local Desktop ASGI Server for Microstock AI Studio.
High-performance Starlette + Uvicorn server connecting the modern web UI directly
to the microstock Python core engine (Gemini Vision, Watcher, SQLite, ExifTool).
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from PIL import Image
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

# Ensure microstock package is discoverable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from microstock import (
    analytics,
    compliance,
    config,
    db,
    distributor,
    export as exp,
    folder_watcher,
    image_generator,
    metadata,
    phash,
    prompt_enhancer,
    reverse_prompt,
    security,
    upscaler,
)

WEB_DIR = os.path.join(PROJECT_ROOT, "microstock", "web")
EXPORTS_DIR = os.path.join(PROJECT_ROOT, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

# In-memory storage for active export batches
_EXPORT_PACKAGES: Dict[str, Dict[str, Any]] = {}


# -----------------------------------------------------------------------------
# REST API Handlers
# -----------------------------------------------------------------------------

async def get_status(request: Request) -> JSONResponse:
    """Return system status, database metrics, and API key presence."""
    api_key = config.load_saved_api_key()
    masked = (api_key[:6] + "..." + api_key[-4:]) if (api_key and len(api_key) > 12) else ("••••••••" if api_key else "")
    recent_assets = db.list_recent_assets(limit=100)
    
    return JSONResponse({
        "status": "online",
        "version": "2.5.0-desktop",
        "total_assets": len(recent_assets),
        "has_api_key": bool(api_key),
        "api_key_masked": masked,
        "default_download_dir": folder_watcher.get_default_downloads_dir(),
        "database_mode": "SQLite WAL",
        "styles_count": len(config.VISUAL_STYLES_32),
    })


async def get_key(request: Request) -> JSONResponse:
    """Get API key status."""
    api_key = config.load_saved_api_key()
    masked = (api_key[:6] + "..." + api_key[-4:]) if (api_key and len(api_key) > 12) else ("••••••••" if api_key else "")
    return JSONResponse({
        "has_key": bool(api_key),
        "masked": masked,
    })


async def save_key(request: Request) -> JSONResponse:
    """Save API key to local encrypted/persisted storage."""
    try:
        body = await request.json()
        key = str(body.get("api_key", "")).strip()
        if not key:
            return JSONResponse({"error": "API Key tidak boleh kosong."}, status_code=400)
        config.save_api_key(key)
        return JSONResponse({"success": True, "message": "API Key berhasil disimpan."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def delete_key(request: Request) -> JSONResponse:
    """Delete API key from local storage."""
    config.delete_saved_api_key()
    return JSONResponse({"success": True, "message": "API Key dihapus."})


async def generate_prompt(request: Request) -> JSONResponse:
    """Generate commercial prompt series or restyle formula."""
    try:
        body = await request.json()
        idea = str(body.get("idea", "")).strip()
        style_name = str(body.get("style", body.get("style_name", "Foto Studio"))).strip()
        mode = str(body.get("mode", "series")).strip()

        if mode == "restyle":
            restyle_p = config.format_photo_restyle_prompt(style_name)
            return JSONResponse({
                "result": {
                    "prompts": [{
                        "title": f"Restyle Formula: {style_name}",
                        "badge": "Image-to-Image",
                        "prompt": restyle_p,
                    }]
                }
            })

        if not idea:
            return JSONResponse({"error": "Ide subjek tidak boleh kosong."}, status_code=400)

        api_key = body.get("api_key") or config.load_saved_api_key()
        if not api_key:
            # High-quality fallback synthesis if API key is not yet set
            vs = config.VISUAL_STYLES_MAP.get(style_name)
            style_desc = vs.prompt_directive_en if vs else "clean commercial photography, studio directional lighting"
            shots = [
                {"title": "Shot 1: Commercial Product Hero", "badge": "Close-up", "ratio": "4:3", "angle": "intimate close-up perspective with rich textural detail"},
                {"title": "Shot 2: Wide Environmental Frame", "badge": "Establishing", "ratio": "16:9", "angle": "wide cinematic contextual composition in authentic setting"},
                {"title": "Shot 3: Overhead Symmetrical Flat-Lay", "badge": "Top-Down", "ratio": "1:1", "angle": "top-down perpendicular flat-lay with balanced geometry"},
                {"title": "Shot 4: Low-Angle Dynamic Perspective", "badge": "Action", "ratio": "3:2", "angle": "low ground-up energetic commercial perspective"},
                {"title": "Shot 5: Minimalist Negative Space", "badge": "Copy Space", "ratio": "16:9", "angle": "offset composition leaving clean commercial copy space"},
            ]
            synthesized = [
                {
                    "title": s["title"],
                    "badge": s["badge"],
                    "prompt": f"Commercial photography of {idea}, {s['angle']}, style: {style_desc}, pristine lighting, 8k resolution, stock library quality [Aspect Ratio: {s['ratio']}]",
                }
                for s in shots
            ]
            return JSONResponse({"result": {"prompts": synthesized}})

        client = config.get_client(api_key)
        try:
            series = prompt_enhancer.generate_thematic_series(
                client=client,
                base_idea=idea,
                style_name=style_name,
            )
        except Exception:
            series = prompt_enhancer._build_fallback_series(idea, style_name)
        return JSONResponse({"result": {"prompts": series}})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def check_compliance(request: Request) -> JSONResponse:
    """Evaluate metadata against stock agency rejection policies."""
    try:
        body = await request.json()
        title = str(body.get("title", "")).strip()
        desc = str(body.get("description", "")).strip()
        raw_kw = body.get("keywords", [])
        if isinstance(raw_kw, str):
            keywords = [k.strip() for k in raw_kw.split(",") if k.strip()]
        else:
            keywords = [str(k).strip() for k in raw_kw if str(k).strip()]
        prompt_txt = str(body.get("prompt", "")).strip()

        rep = compliance.evaluate_commercial_compliance(title, desc, keywords, prompt_txt)
        return JSONResponse({"compliance": rep.to_dict()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def list_assets(request: Request) -> JSONResponse:
    """Get list of locally indexed assets from SQLite."""
    limit = int(request.query_params.get("limit", 50))
    assets = db.list_recent_assets(limit=limit)
    return JSONResponse({"assets": assets, "total": len(assets)})


async def prune_assets(request: Request) -> JSONResponse:
    """Remove missing asset records from database."""
    removed = db.prune_missing_assets()
    return JSONResponse({"success": True, "removed": removed})


async def clear_assets(request: Request) -> JSONResponse:
    """Clear all assets from database."""
    cleared = db.clear_all_assets()
    return JSONResponse({"success": True, "cleared": cleared})


async def scan_watcher(request: Request) -> JSONResponse:
    """Scan downloads or target folder for recent images."""
    watch_dir = request.query_params.get("path") or config.load_saved_api_key() or folder_watcher.get_default_downloads_dir()
    window = request.query_params.get("window", "1 Jam Terakhir")
    
    cutoff = folder_watcher.get_cutoff_timestamp(window)
    found_files = folder_watcher.scan_recent_images(watch_dir, since_timestamp=cutoff, max_files=40)
    
    items = []
    for fn, fpath, mtime, fsize in found_files:
        # Generate lightweight base64 thumbnail
        thumb_data = ""
        try:
            with Image.open(fpath) as im:
                im.thumbnail((160, 160))
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=75)
                thumb_data = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass

        items.append({
            "filename": fn,
            "filepath": fpath,
            "size_kb": fsize // 1024,
            "mtime": mtime,
            "thumbnail": thumb_data,
        })

    pending = folder_watcher.check_pending_downloads(watch_dir)
    return JSONResponse({
        "files": items,
        "count": len(items),
        "pending_downloads": pending,
        "watch_dir": watch_dir,
    })


async def run_batch_vision(request: Request) -> JSONResponse:
    """Process batch images with Gemini Vision, auto-upscale, IPTC metadata, and direct folder output."""
    try:
        content_type = request.headers.get("content-type", "")
        raw_items: List[tuple[str, bytes]] = []
        do_upscale = False
        enforce_4mb = False

        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            files = form.getlist("images") or form.getlist("files")
            do_upscale = form.get("do_upscale") in ("true", "1", True)
            enforce_4mb = form.get("enforce_4mb") in ("true", "1", True)
            for f in files:
                fname = getattr(f, "filename", "image.jpg")
                content = await f.read()
                if content:
                    raw_items.append((fname, content))
        else:
            body = await request.json()
            file_paths = body.get("file_paths", [])
            do_upscale = bool(body.get("do_upscale", False))
            enforce_4mb = bool(body.get("enforce_4mb", False))
            for fpath in file_paths:
                if os.path.exists(fpath):
                    with open(fpath, "rb") as fr:
                        raw_items.append((os.path.basename(fpath), fr.read()))

        api_key = config.load_saved_api_key()
        if not api_key:
            return JSONResponse({"error": "Gemini API Key belum disetel di Pengaturan."}, status_code=400)
        if not raw_items:
            return JSONResponse({"error": "Pilih minimal 1 gambar untuk diproses."}, status_code=400)

        client = config.get_client(api_key)
        processed_items: List[image_generator.BatchItem] = []

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        batch_folder_name = f"batch_{timestamp}"
        out_dir = os.path.join(EXPORTS_DIR, batch_folder_name)
        os.makedirs(out_dir, exist_ok=True)

        for idx, (filename, raw_bytes) in enumerate(raw_items):
            mime = "image/jpeg"
            if filename.lower().endswith(".png"):
                mime = "image/png"
            elif filename.lower().endswith(".webp"):
                mime = "image/webp"

            md = None
            try:
                md = await metadata.generate_metadata_from_vision_async(
                    client=client,
                    image_bytes=raw_bytes,
                    mime_type=mime,
                    label=f"Visual #{idx+1}",
                )
            except Exception:
                md = metadata.create_fallback_metadata(filename)

            target_bytes = raw_bytes
            if do_upscale:
                try:
                    with Image.open(io.BytesIO(raw_bytes)) as _tmp:
                        ow, oh = _tmp.size
                except Exception:
                    ow, oh = 1024, 1024

                if upscaler.is_upscale_needed(ow, oh):
                    target_bytes, success, _ = await asyncio.to_thread(upscaler.upscale_bytes, raw_bytes)

            exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                image_generator.finalize_image,
                target_bytes,
                "JPEG",
                enforce_microstock_res=do_upscale,
                enforce_min_filesize=enforce_4mb,
                max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS if do_upscale else None,
                jpeg_quality=95,
                metadata=md,
            )

            # Save directly into output folder as JPEG with injected IPTC metadata
            base_name = os.path.splitext(filename)[0]
            out_file_name = f"{base_name}.jpg"
            out_file_path = os.path.join(out_dir, out_file_name)
            with open(out_file_path, "wb") as f_out:
                f_out.write(exp_bytes)

            phash_val = phash.compute_phash(exp_bytes)
            dups = db.find_near_duplicates_in_db(phash_val, max_hamming_distance=5)
            dup_risk = "HIGH" if (dups and dups[0][1] <= 3) else ("MEDIUM" if dups else None)

            item = image_generator.BatchItem(
                index=idx,
                variation=f"Batch {filename}",
                final_prompt="",
                filename=out_file_name,
                image_bytes=exp_bytes,
                preview_bytes=prev_bytes,
                mime_type=f_mime,
                width=w,
                height=h,
                metadata=md,
                phash=phash_val,
                is_xmp_injected=bool(md and md.title),
                duplicate_risk=dup_risk,
            )
            processed_items.append(item)

            db.save_asset(
                file_path=out_file_path,
                file_name=out_file_name,
                file_size_bytes=len(exp_bytes),
                width=w,
                height=h,
                aspect_ratio=reverse_prompt._detect_ratio(w, h),
                phash_hex=phash_val,
                title=md.title if md else "",
                description=md.description if md else "",
                keywords=md.keywords if md else [],
                adobe_category_id=md.adobe_category if md else 8,
                shutterstock_cats=md.shutterstock_categories if md else [],
                is_xmp_injected=bool(md and md.title),
            )

        results_preview = []
        for it in processed_items:
            results_preview.append({
                "filename": it.filename,
                "width": it.width,
                "height": it.height,
                "size_mb": round(len(it.image_bytes) / 1048576, 2),
                "title": it.metadata.title if it.metadata else "",
                "description": it.metadata.description if it.metadata else "",
                "keywords": it.metadata.keywords if it.metadata else [],
                "adobe_category": f"#{it.metadata.adobe_category} {it.metadata.adobe_category_name}" if it.metadata else "",
                "duplicate_risk": it.duplicate_risk,
                "is_xmp_injected": it.is_xmp_injected,
            })

        return JSONResponse({
            "success": True,
            "processed_count": len(processed_items),
            "folder_name": batch_folder_name,
            "folder_path": out_dir,
            "results": results_preview,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def open_system_folder(request: Request) -> JSONResponse:
    """Open folder in OS file manager (Finder on macOS)."""
    try:
        body = await request.json()
        folder_path = body.get("path", "")
        if not folder_path or not os.path.exists(folder_path):
            return JSONResponse({"error": "Folder tidak ditemukan di penyimpanan."}, status_code=404)
        if sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        elif sys.platform == "win32":
            os.startfile(folder_path)
        else:
            subprocess.Popen(["xdg-open", folder_path])
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def download_export(request: Request) -> Response:
    """Download generated ZIP or CSV package."""
    batch_id = request.path_params.get("batch_id")
    fmt = request.path_params.get("fmt", "zip").lower()
    
    pkg = _EXPORT_PACKAGES.get(batch_id)
    if not pkg:
        return JSONResponse({"error": "Paket ekspor tidak ditemukan atau kedaluwarsa."}, status_code=404)

    if fmt == "csv":
        return FileResponse(pkg["csv_path"], media_type="text/csv", filename=f"metadata_{batch_id}.csv")
    return FileResponse(pkg["zip_path"], media_type="application/zip", filename=f"microstock_pack_{batch_id}.zip")


async def run_reverse_prompt(request: Request) -> JSONResponse:
    """Extract prompt and aspect ratio from reference image."""
    try:
        body = await request.json()
        img_b64 = body.get("image_base64", "")
        api_key = config.load_saved_api_key()

        if not api_key:
            return JSONResponse({"error": "Gemini API Key belum disetel."}, status_code=400)
        if not img_b64:
            return JSONResponse({"error": "Gambar referensi kosong."}, status_code=400)

        raw_bytes = base64.b64decode(img_b64.split(",")[-1])
        with Image.open(io.BytesIO(raw_bytes)) as im:
            w, h = im.size

        client = config.get_client(api_key)
        prompt_str = await reverse_prompt.generate_reverse_prompt_async(
            client=client,
            image_bytes=raw_bytes,
            mime_type="image/jpeg",
            label="Reverse Prompt",
            width=w,
            height=h,
        )
        return JSONResponse({"prompt": prompt_str, "width": w, "height": h, "aspect_ratio": reverse_prompt._detect_ratio(w, h)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def test_agency_account(request: Request) -> JSONResponse:
    """Test FTP / SFTP agency connection."""
    try:
        body = await request.json()
        host = body.get("host", "")
        port = int(body.get("port", 21))
        proto = body.get("protocol", "ftp")
        user = body.get("username", "")
        pwd = body.get("password", "")

        ok, msg = distributor.test_agency_connection(host, port, proto, user, pwd)
        return JSONResponse({"success": ok, "message": msg})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def save_agency_account(request: Request) -> JSONResponse:
    """Save agency credentials to local SQLite storage."""
    try:
        body = await request.json()
        agency = body.get("agency_name", "")
        host = body.get("host", "")
        port = int(body.get("port", 21))
        proto = body.get("protocol", "ftp")
        user = body.get("username", "")
        pwd = body.get("password", "")

        db.save_agency_account(agency, host, port, proto, user, pwd)
        return JSONResponse({"success": True, "message": f"Kredensial untuk {agency} berhasil disimpan."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# -----------------------------------------------------------------------------
# Starlette Application Routing & Construction
# -----------------------------------------------------------------------------

routes = [
    Route("/api/status", get_status, methods=["GET"]),
    Route("/api/key", get_key, methods=["GET"]),
    Route("/api/key", save_key, methods=["POST"]),
    Route("/api/key", delete_key, methods=["DELETE"]),
    Route("/api/prompt/generate", generate_prompt, methods=["POST"]),
    Route("/api/compliance/check", check_compliance, methods=["POST"]),
    Route("/api/assets", list_assets, methods=["GET"]),
    Route("/api/assets/prune", prune_assets, methods=["POST"]),
    Route("/api/assets/clear", clear_assets, methods=["POST"]),
    Route("/api/watcher/scan", scan_watcher, methods=["GET"]),
    Route("/api/vision/batch", run_batch_vision, methods=["POST"]),
    Route("/api/folder/open", open_system_folder, methods=["POST"]),
    Route("/api/export/{batch_id}/{fmt}", download_export, methods=["GET"]),
    Route("/api/reverse-prompt", run_reverse_prompt, methods=["POST"]),
    Route("/api/accounts/test", test_agency_account, methods=["POST"]),
    Route("/api/accounts/save", save_agency_account, methods=["POST"]),
    Mount("/", app=StaticFiles(directory=WEB_DIR, html=True), name="static"),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware)


def main():
    port = int(os.environ.get("PORT", 8501))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Microstock Studio Precision Server on http://localhost:{port}/")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
