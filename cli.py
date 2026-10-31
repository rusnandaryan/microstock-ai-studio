#!/usr/bin/env python3
"""Microstock AI Studio - Terminal CLI Interface.

Jalankan perintah langsung dari terminal tanpa ketergantungan pada browser web.
Gunakan 'python cli.py --help' untuk melihat panduan lengkap.
"""
from __future__ import annotations

import os
import sys

# Auto-bootstrap: jika dijalankan dengan python sistem, otomatis re-exec menggunakan .venv lokal
_script_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dir = os.path.join(_script_dir, ".venv")
_venv_python = os.path.join(_venv_dir, "bin", "python3")
if os.path.exists(_venv_python) and os.path.abspath(sys.prefix) != os.path.abspath(_venv_dir):
    os.execv(_venv_python, [_venv_python] + sys.argv)

import argparse
import asyncio
import io
import subprocess
import time
from typing import List

from PIL import Image

from microstock import config, folder_watcher
from microstock.export import build_metadata_dataframe, build_zip, dataframe_to_csv_bytes
from microstock.image_generator import BatchItem, finalize_image
from microstock.metadata import generate_metadata_from_vision_async
from microstock.prompt_enhancer import enhance_prompt
from microstock.reverse_prompt import _detect_ratio, generate_reverse_prompt_async, save_prompt_to_file
from microstock.trend_analyzer import get_trending_ideas
from microstock.upscaler import is_upscale_needed, run_upscale


def get_authenticated_client(api_key: str | None = None):
    key = api_key or config.load_saved_api_key()
    if not key:
        print("❌ Error: GEMINI_API_KEY belum disetel.")
        print("   Silakan simpan API key di file .env atau operasikan via flag: --api-key <KEY>")
        sys.exit(1)
    return config.get_client(key)


def cmd_prompt(args: argparse.Namespace) -> None:
    """Generate commercial image prompt matching stock criteria."""
    client = get_authenticated_client(args.api_key)
    print(f"⏳ Meracik prompt komersial untuk: '{args.idea}'...")
    try:
        result = enhance_prompt(
            client=client,
            base_idea=args.idea,
            style_name=args.style,
            aspect_ratio=args.ratio,
            lighting=args.lighting,
            camera=args.camera,
            composition=args.composition,
        )
        print("\n" + "=" * 60)
        print("📸 PROMPT KOMERSIAL SIAP PAKAI:")
        print("=" * 60)
        print(result)
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"❌ Gagal meracik prompt: {e}")
        sys.exit(1)


def cmd_trends(args: argparse.Namespace) -> None:
    """Check trending topics on Adobe Stock."""
    client = get_authenticated_client(args.api_key)
    print("⏳ Menganalisis tren pasar Adobe Stock & Shutterstock saat ini...")
    try:
        data = get_trending_ideas(client)
        trends = data.get("trends", [])
        period = data.get("period", "Hari ini")
        print("\n" + "=" * 60)
        print(f"🔥 4 TREN KOMERSIAL UTAMA MICROSTOCK ({period}):")
        print("=" * 60)
        for i, item in enumerate(trends, 1):
            print(f"\n{i}. [{item.get('market_status', 'High Demand')}] {item.get('category', '')}")
            print(f"   Alasan : {item.get('reason', '')}")
            print(f"   Ide    : \"{item.get('base_idea', '')}\"")
            print(f"   Gaya   : {item.get('recommended_style', '')} ({item.get('recommended_ratio', '16:9')})")
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"❌ Gagal mengambil data tren: {e}")
        sys.exit(1)


def cmd_reverse(args: argparse.Namespace) -> None:
    """Reverse prompt an image file."""
    if not os.path.isfile(args.image_path):
        print(f"❌ File tidak ditemukan: {args.image_path}")
        sys.exit(1)

    client = get_authenticated_client(args.api_key)
    print(f"⏳ Menganalisis elemen visual: {os.path.basename(args.image_path)}...")

    with open(args.image_path, "rb") as f:
        raw_bytes = f.read()

    try:
        with Image.open(io.BytesIO(raw_bytes)) as im:
            w, h = im.size
    except Exception:
        w, h = 1920, 1080

    async def _run():
        return await generate_reverse_prompt_async(
            client=client,
            image_bytes=raw_bytes,
            mime_type="image/jpeg",
            width=w,
            height=h,
        )

    try:
        prompt_str = asyncio.run(_run())
        saved_path = save_prompt_to_file(prompt_str, os.path.basename(args.image_path))
        print("\n" + "=" * 60)
        print("🎯 REVERSE PROMPT BERHASIL DISUSUN:")
        print("=" * 60)
        print(prompt_str)
        print("=" * 60)
        print(f"💾 Tersimpan di: {saved_path}\n")
    except Exception as e:
        print(f"❌ Gagal membuat reverse prompt: {e}")
        sys.exit(1)


def cmd_process(args: argparse.Namespace) -> None:
    """Analyze images from folder or file list, upscale, and export SEO package."""
    client = get_authenticated_client(args.api_key)
    targets: List[tuple[str, bytes, str]] = []

    if os.path.isdir(args.source):
        found = folder_watcher.scan_recent_images(args.source, max_files=args.limit)
        for fn, fpath, _, _ in found:
            item = folder_watcher.read_image_bytes(fpath)
            if item:
                targets.append(item)
    elif os.path.isfile(args.source):
        item = folder_watcher.read_image_bytes(args.source)
        if item:
            targets.append(item)

    if not targets:
        print(f"⚠️ Tidak ada gambar yang ditemukan untuk diproses di: {args.source}")
        sys.exit(0)

    print(f"🚀 Memulai pemrosesan {len(targets)} gambar (Upscale: {args.upscale}, Freepik Min 4MB: {args.freepik})...\n")

    processed_items: list[BatchItem] = []

    async def _process_all():
        for idx, (filename, raw_bytes, mime) in enumerate(targets, 1):
            print(f"[{idx}/{len(targets)}] 🔍 Inspeksi Gemini Vision: {filename}...")
            try:
                md = await generate_metadata_from_vision_async(
                    client=client,
                    image_bytes=raw_bytes,
                    mime_type=mime,
                    label=filename,
                )
            except Exception as e:
                print(f"    ⚠️ Gagal metadata: {e}. Menggunakan fallback.")
                clean_title = os.path.splitext(filename)[0].replace("_", " ").title()
                from microstock.metadata import ImageMetadata
                md = ImageMetadata(
                    title=clean_title,
                    description=f"High quality stock asset: {clean_title}.",
                    keywords=["stock", "commercial", "modern", "quality"],
                    adobe_category=12,
                    shutterstock_categories=["Objects"],
                )

            target_bytes = raw_bytes
            if args.upscale:
                try:
                    with Image.open(io.BytesIO(raw_bytes)) as _tmp:
                        ow, oh = _tmp.size
                except Exception:
                    ow, oh = 1024, 1024

                if is_upscale_needed(ow, oh):
                    print(f"    ⚡ Menjalankan AI Upscale 4x ({ow}x{oh} -> ~4x)...")
                    import tempfile
                    in_p = None
                    out_p = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as in_f:
                            in_f.write(raw_bytes)
                            in_p = in_f.name
                        out_p = in_p.replace(".jpg", "_up.jpg")
                        success, err = await asyncio.to_thread(run_upscale, in_p, out_p, 4, "realesrgan-x4plus", 400)
                        if success:
                            with open(out_p, "rb") as out_f:
                                target_bytes = out_f.read()
                        else:
                            print(f"    ⚠️ Upscale gagal: {err}. Beralih ke Lanczos.")
                    finally:
                        for p in (in_p, out_p):
                            if p and os.path.exists(p):
                                try: os.remove(p)
                                except OSError: pass

            exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                finalize_image,
                target_bytes,
                "JPEG",
                enforce_microstock_res=args.upscale,
                enforce_min_filesize=args.freepik,
                max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS if args.smart else None,
                jpeg_quality=95,
            )

            processed_items.append(BatchItem(
                index=idx - 1,
                variation=f"Processed {filename}",
                final_prompt="",
                filename=filename,
                image_bytes=exp_bytes,
                preview_bytes=prev_bytes,
                mime_type=f_mime,
                width=w,
                height=h,
                metadata=md,
            ))
            print(f"    ✅ Selesai: {w}x{h} px ({len(exp_bytes)/1024/1024:.2f} MB), {len(md.keywords)} keywords.")

    asyncio.run(_process_all())

    # Build exports
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports", f"batch_{timestamp}")
    os.makedirs(export_dir, exist_ok=True)

    df = build_metadata_dataframe(processed_items)
    csv_bytes = dataframe_to_csv_bytes(df)
    zip_bytes = build_zip(processed_items, None, df)

    with open(os.path.join(export_dir, "metadata.csv"), "wb") as f:
        f.write(csv_bytes)
    with open(os.path.join(export_dir, f"package_{timestamp}.zip"), "wb") as f:
        f.write(zip_bytes)

    if args.upscale:
        for it in processed_items:
            if it.image_bytes:
                with open(os.path.join(export_dir, it.filename), "wb") as f_img:
                    f_img.write(it.image_bytes)

    print("\n" + "=" * 60)
    print("🎉 PEMROSESAN SELESAI DENGAN SUKSES!")
    print("=" * 60)
    print(f"📁 Folder Hasil Ekspor : {export_dir}")
    print(f"📄 Master CSV           : {export_dir}/metadata.csv")
    print(f"📦 Paket Siap Upload    : {export_dir}/package_{timestamp}.zip")
    print("=" * 60 + "\n")


def cmd_gui(args: argparse.Namespace) -> None:
    """Launch Streamlit Web GUI."""
    print("🌐 Menjalankan Microstock AI Studio di browser...")
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="microstock",
        description="📸 Microstock AI Studio - Professional Terminal CLI & Automation Tool",
        epilog="Contoh penggunaan:\n"
               "  python cli.py prompt \"cangkir kopi keramik\"\n"
               "  python cli.py process ~/Downloads --upscale\n"
               "  python cli.py reverse foto.jpg\n"
               "  python cli.py trends\n"
               "  python cli.py gui",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-key", help="Google Gemini API Key (opsional jika sudah ada di .env)")

    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia:")

    # 1. Subcommand: prompt
    p_prompt = subparsers.add_parser("prompt", help="Racik 1 prompt komersial profesional terstandarisasi")
    p_prompt.add_argument("idea", help="Konsep dasar / ide subjek gambar")
    p_prompt.add_argument("--style", default=config.DEFAULT_STYLE, help="Nama gaya preset estetika")
    p_prompt.add_argument("--ratio", default="16:9", choices=list(config.ASPECT_RATIOS.keys()), help="Target rasio aspek")
    p_prompt.add_argument("--lighting", default=config.DEFAULT_LIGHTING, help="Kondisi pencahayaan")
    p_prompt.add_argument("--camera", default=config.DEFAULT_CAMERA, help="Lensa & sudut kamera")
    p_prompt.add_argument("--composition", default=config.DEFAULT_COMPOSITION, help="Komposisi framing")
    p_prompt.set_defaults(func=cmd_prompt)

    # 2. Subcommand: process
    p_process = subparsers.add_parser("process", help="Analisis folder gambar, susun metadata SEO, AI upscale, dan buat ZIP")
    p_process.add_argument("source", nargs="?", default=folder_watcher.get_default_downloads_dir(), help="Path folder atau file gambar (default: Gemini Downloads)")
    p_process.add_argument("--limit", type=int, default=50, help="Batas maksimal gambar yang dipindai (default: 50)")
    p_process.add_argument("--upscale", action="store_true", help="Aktifkan AI upscaler 4x jika resolusi < 4.2 MP")
    p_process.add_argument("--smart", action="store_true", default=True, help="Batasi target resolusi ~8.3 MP (Smart Microstock)")
    p_process.add_argument("--freepik", action="store_true", help="Wajibkan ukuran file minimal 4 MB (standar Freepik)")
    p_process.set_defaults(func=cmd_process)

    # 3. Subcommand: reverse
    p_reverse = subparsers.add_parser("reverse", help="Bedah visual gambar menjadi prompt komersial (Image to Prompt)")
    p_reverse.add_argument("image_path", help="Path ke file gambar yang ingin dianalisis")
    p_reverse.set_defaults(func=cmd_reverse)

    # 4. Subcommand: trends
    p_trends = subparsers.add_parser("trends", help="Lihat 4 kategori topik komersial yang sedang tren di Adobe Stock")
    p_trends.set_defaults(func=cmd_trends)

    # 5. Subcommand: gui
    p_gui = subparsers.add_parser("gui", help="Buka antarmuka visual web (Streamlit)")
    p_gui.set_defaults(func=cmd_gui)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

