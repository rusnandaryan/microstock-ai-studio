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

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="urllib3")
warnings.filterwarnings("ignore", message=".*urllib3.*")

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
from microstock.upscaler import is_upscale_needed, upscale_bytes


def get_authenticated_client(api_key: str | None = None):
    key = api_key or config.load_saved_api_key()
    if not key:
        print("[ERROR] GEMINI_API_KEY belum disetel.")
        print("   Silakan simpan API key di file .env atau operasikan via flag: --api-key <KEY>")
        sys.exit(1)
    return config.get_client(key)


def cmd_prompt(args: argparse.Namespace) -> None:
    """Generate commercial image prompt matching stock criteria."""
    client = get_authenticated_client(args.api_key)
    print(f"[INFO] Meracik prompt komersial untuk: '{args.idea}'...")
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
        print("PROMPT KOMERSIAL SIAP PAKAI:")
        print("=" * 60)
        print(result)
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"[ERROR] Gagal meracik prompt: {e}")
        sys.exit(1)


def cmd_trends(args: argparse.Namespace) -> None:
    """Check 10 upcoming global moments and microstock commercial trends."""
    client = get_authenticated_client(args.api_key)
    print("[INFO] Menganalisis 10 momen & hari besar mendatang di media massa dan microstock...")
    try:
        data = get_trending_ideas(client)
        trends = data.get("trends", [])
        period = data.get("period", "Hari ini")
        print("\n" + "=" * 60)
        print(f"10 MOMEN & HARI BESAR MENDATANG MICROSTOCK ({period}):")
        print("=" * 60)
        for i, item in enumerate(trends, 1):
            name = item.get("event_name") or item.get("category", "")
            date = item.get("target_date", "Mendatang")
            print(f"\n{i}. [{item.get('market_status', 'Viral')}] {name} ({date})")
            print(f"   Alasan : {item.get('reason', '')}")
            print(f"   Ide    : \"{item.get('base_idea', '')}\"")
            print(f"   Format : {item.get('recommended_cat', '')} · {item.get('recommended_style', '')} ({item.get('recommended_ratio', '16:9')})")
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data tren: {e}")
        sys.exit(1)


def cmd_reverse(args: argparse.Namespace) -> None:
    """Reverse prompt an image file."""
    if not os.path.isfile(args.image_path):
        print(f"[ERROR] File tidak ditemukan: {args.image_path}")
        sys.exit(1)

    client = get_authenticated_client(args.api_key)
    print(f"[INFO] Menganalisis elemen visual: {os.path.basename(args.image_path)}...")

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
        print("REVERSE PROMPT BERHASIL DISUSUN:")
        print("=" * 60)
        print(prompt_str)
        print("=" * 60)
        print(f"Tersimpan di: {saved_path}\n")
    except Exception as e:
        print(f"[ERROR] Gagal membuat reverse prompt: {e}")
        sys.exit(1)


def cmd_process(args: argparse.Namespace) -> None:
    """Analyze images from folder or file list, upscale, and export SEO package."""
    client = get_authenticated_client(args.api_key)
    targets: List[tuple[str, bytes, str]] = []
    seen_names = set()

    def _add_target(fn: str, b: bytes, m: str) -> None:
        name = os.path.basename(fn).strip()
        stem, ext = os.path.splitext(name)
        candidate = name
        counter = 1
        while candidate.lower() in seen_names:
            candidate = f"{stem}_{counter}{ext}"
            counter += 1
        seen_names.add(candidate.lower())
        targets.append((candidate, b, m))

    if os.path.isdir(args.source):
        found = folder_watcher.scan_recent_images(args.source, max_files=args.limit)
        for fn, fpath, _, _ in found:
            item = folder_watcher.read_image_bytes(fpath)
            if item:
                _add_target(item[0], item[1], item[2])
    elif os.path.isfile(args.source):
        item = folder_watcher.read_image_bytes(args.source)
        if item:
            _add_target(item[0], item[1], item[2])

    if not targets:
        print(f"[WARN] Tidak ada gambar yang ditemukan untuk diproses di: {args.source}")
        sys.exit(0)

    print(f"[INFO] Memulai pemrosesan {len(targets)} gambar (Upscale: {args.upscale}, Freepik Min 4MB: {args.freepik})...\n")

    processed_items: list[BatchItem] = []

    async def _process_all():
        for idx, (filename, raw_bytes, mime) in enumerate(targets, 1):
            print(f"[{idx}/{len(targets)}] [INSPEKSI] Gemini Vision: {filename}...")
            try:
                md = await generate_metadata_from_vision_async(
                    client=client,
                    image_bytes=raw_bytes,
                    mime_type=mime,
                    label=filename,
                )
            except Exception as e:
                print(f"    [WARN] Gagal metadata: {e}. Menggunakan fallback.")
                from microstock.metadata import create_fallback_metadata
                md = create_fallback_metadata(filename)

            target_bytes = raw_bytes
            if args.upscale:
                try:
                    with Image.open(io.BytesIO(raw_bytes)) as _tmp:
                        ow, oh = _tmp.size
                except Exception:
                    ow, oh = 1024, 1024

                if is_upscale_needed(ow, oh):
                    print(f"    [UPSCALE] Menjalankan AI Upscale 4x ({ow}x{oh} -> ~4x)...")
                    target_bytes, success, err = await asyncio.to_thread(upscale_bytes, raw_bytes)
                    if not success:
                        print(f"    [WARN] Upscale gagal: {err}. Beralih ke Lanczos.")

            exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                finalize_image,
                target_bytes,
                "JPEG",
                enforce_microstock_res=args.upscale,
                enforce_min_filesize=args.freepik,
                max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS if args.smart else None,
                jpeg_quality=95,
                metadata=md,
            )

            from microstock import db
            from microstock.phash import compute_phash, similarity_percent
            from microstock.reverse_prompt import _detect_ratio

            phash_val = compute_phash(exp_bytes)
            dups = db.find_near_duplicates_in_db(phash_val, max_hamming_distance=5)
            dup_warning = ""
            if dups:
                top_match, dist, sim = dups[0]
                dup_warning = f" [PERINGATAN: Mirip {sim}% dgn {top_match.get('file_name', 'arsip')}]"

            db.save_asset(
                file_path=os.path.join(args.source if os.path.isdir(args.source) else os.path.dirname(args.source), filename),
                file_name=filename,
                file_size_bytes=len(exp_bytes),
                width=w,
                height=h,
                aspect_ratio=_detect_ratio(w, h),
                phash_hex=phash_val,
                title=md.title if md else "",
                description=md.description if md else "",
                keywords=md.keywords if md else [],
                adobe_category_id=md.adobe_category if md else 8,
                shutterstock_cats=md.shutterstock_categories if md else [],
                is_xmp_injected=bool(md and md.title),
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
                phash=phash_val,
                is_xmp_injected=bool(md and md.title),
                duplicate_risk="HIGH" if dups and dups[0][1] <= 3 else ("MEDIUM" if dups else None),
            ))
            print(f"    [OK] Selesai: {w}x{h} px ({len(exp_bytes)/1024/1024:.2f} MB), {len(md.keywords)} keywords (IPTC: Embedded, pHash: {phash_val[:8]}...){dup_warning}")

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
    print("[SUKSES] PEMROSESAN SELESAI DENGAN SUKSES!")
    print("=" * 60)
    print(f"Folder Hasil Ekspor : {export_dir}")
    print(f"Master CSV           : {export_dir}/metadata.csv")
    print(f"Paket Siap Upload    : {export_dir}/package_{timestamp}.zip")
    print("=" * 60 + "\n")


def cmd_gui(args: argparse.Namespace) -> None:
    """Launch Streamlit Web GUI."""
    print("[INFO] Menjalankan Microstock AI Studio di browser...")
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def cmd_db(args: argparse.Namespace) -> None:
    """Inspect SQLite WAL database and recent indexed assets."""
    from microstock import db
    assets = db.list_recent_assets(limit=args.limit)
    subs = db.list_recent_submissions(limit=10)
    print("\n" + "=" * 60)
    print("STATUS DATABASE MASTER (SQLite WAL):")
    print("=" * 60)
    print(f"Path Database       : {db.get_default_db_path()}")
    print(f"Total Aset Terindeks: {len(assets)}")
    print(f"Aset IPTC Injected  : {sum(1 for a in assets if a.get('is_xmp_injected'))}")
    print("-" * 60)
    for i, a in enumerate(assets[:15], 1):
        xmp_str = "[IPTC OK]" if a.get("is_xmp_injected") else "[NO IPTC]"
        print(f"{i}. {xmp_str} {a.get('file_name')} ({a.get('width')}x{a.get('height')}) - {a.get('title', '')[:30]}...")
    if subs:
        print("\nRiwayat Pengiriman Agensi:")
        for s in subs[:5]:
            print(f"- [{s.get('agency_name')}] {s.get('remote_filename')} -> {s.get('status')}")
    print("=" * 60 + "\n")


def cmd_upload(args: argparse.Namespace) -> None:
    """Upload processed image files directly to stock agencies (FTP/SFTP)."""
    from microstock import distributor
    if args.agency not in distributor.AGENCY_ENDPOINTS:
        print(f"[ERROR] Agensi '{args.agency}' tidak valid. Pilihan: {list(distributor.AGENCY_ENDPOINTS.keys())}")
        sys.exit(1)

    targets = []
    if os.path.isdir(args.path):
        for f in os.listdir(args.path):
            if f.lower().endswith((".jpg", ".jpeg")):
                targets.append(os.path.join(args.path, f))
    elif os.path.isfile(args.path):
        targets.append(args.path)

    if not targets:
        print(f"[ERROR] Tidak ada file JPEG yang ditemukan di: {args.path}")
        sys.exit(1)

    print(f"[INFO] Memulai pengiriman {len(targets)} file ke {distributor.AGENCY_ENDPOINTS[args.agency]['name']}...")
    try:
        results = distributor.dispatch_batch_to_agency(
            agency_key=args.agency,
            file_paths=targets,
            progress_callback=lambda idx, tot, msg: print(f"[{idx}/{tot}] {msg}"),
        )
        success_count = sum(1 for r in results if r.success)
        print(f"\n[SUKSES] {success_count}/{len(targets)} file berhasil diunggah.")
    except Exception as e:
        print(f"[ERROR] Gagal mengirim: {e}")
        sys.exit(1)


def cmd_desktop(args: argparse.Namespace) -> None:
    """Launch the Native Desktop Workstation (Local REST Server + Native App Window)."""
    from microstock.server import start_desktop_server
    import webbrowser
    import threading

    host = getattr(args, "host", "127.0.0.1")
    port = int(getattr(args, "port", 8505))
    server = start_desktop_server(host, port)
    url = f"http://{host}:{port}"
    print(f"\n[INFO] Microstock AI Studio Pro - Desktop Native Engine Aktif")
    print(f"[INFO] Server berjalan di: {url}")
    print(f"[INFO] Waktu cold-start: < 0.2 detik · RAM: < 35 MB")
    print("Tekan Ctrl+C untuk menutup server.\n")

    def _open_app():
        time.sleep(0.4)
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
        opened = False
        for cpath in chrome_paths:
            if os.path.exists(cpath):
                try:
                    subprocess.Popen([cpath, f"--app={url}"])
                    opened = True
                    break
                except Exception:
                    pass
        if not opened:
            webbrowser.open(url)

    threading.Thread(target=_open_app, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Desktop server dihentikan.")
        server.server_close()


def main() -> None:
    api_parser = argparse.ArgumentParser(add_help=False)
    api_parser.add_argument("--api-key", help="Google Gemini API Key (opsional jika sudah ada di .env)")

    parser = argparse.ArgumentParser(
        prog="microstock",
        description="Microstock AI Studio - Professional Terminal CLI & Automation Tool",
        epilog="Contoh penggunaan:\n"
               "  python cli.py prompt \"cangkir kopi keramik\"\n"
               "  python cli.py process ~/Downloads --upscale\n"
               "  python cli.py reverse foto.jpg\n"
               "  python cli.py trends\n"
               "  python cli.py gui",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[api_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia:")

    p_prompt = subparsers.add_parser("prompt", parents=[api_parser], help="Racik 1 prompt komersial profesional terstandarisasi")
    p_prompt.add_argument("idea", help="Konsep dasar / ide subjek gambar")
    p_prompt.add_argument("--style", default=config.DEFAULT_STYLE, help="Nama gaya preset estetika")
    p_prompt.add_argument("--ratio", default="16:9", choices=list(config.ASPECT_RATIOS.keys()), help="Target rasio aspek")
    p_prompt.add_argument("--lighting", default=config.DEFAULT_LIGHTING, help="Kondisi pencahayaan")
    p_prompt.add_argument("--camera", default=config.DEFAULT_CAMERA, help="Lensa & sudut kamera")
    p_prompt.add_argument("--composition", default=config.DEFAULT_COMPOSITION, help="Komposisi framing")
    p_prompt.set_defaults(func=cmd_prompt)

    p_process = subparsers.add_parser("process", parents=[api_parser], help="Analisis folder gambar, susun metadata SEO, AI upscale, dan buat ZIP")
    p_process.add_argument("source", nargs="?", default=folder_watcher.get_default_downloads_dir(), help="Path folder atau file gambar (default: Gemini Downloads)")
    p_process.add_argument("--limit", type=int, default=50, help="Batas maksimal gambar yang dipindai (default: 50)")
    p_process.add_argument("--upscale", action="store_true", help="Aktifkan AI upscaler 4x jika resolusi < 4.2 MP")
    p_process.add_argument("--smart", action="store_true", default=True, help="Batasi target resolusi ~8.3 MP (Smart Microstock)")
    p_process.add_argument("--freepik", action="store_true", help="Wajibkan ukuran file minimal 4 MB (standar Freepik)")
    p_process.set_defaults(func=cmd_process)

    p_reverse = subparsers.add_parser("reverse", parents=[api_parser], help="Bedah visual gambar menjadi prompt komersial (Image to Prompt)")
    p_reverse.add_argument("image_path", help="Path ke file gambar yang ingin dianalisis")
    p_reverse.set_defaults(func=cmd_reverse)

    p_trends = subparsers.add_parser("trends", parents=[api_parser], help="Lihat 10 momen & hari besar mendatang yang berpotensi trending di microstock")
    p_trends.set_defaults(func=cmd_trends)

    p_gui = subparsers.add_parser("gui", parents=[api_parser], help="Buka antarmuka visual web (Streamlit)")
    p_gui.set_defaults(func=cmd_gui)

    p_db = subparsers.add_parser("db", parents=[api_parser], help="Inspeksi ringkasan database SQLite dan arsip aset")
    p_db.add_argument("--limit", type=int, default=30, help="Jumlah aset yang ditampilkan (default: 30)")
    p_db.set_defaults(func=cmd_db)

    p_upload = subparsers.add_parser("upload", parents=[api_parser], help="Kirim aset gambar langsung ke server agensi via FTP/SFTP")
    p_upload.add_argument("agency", choices=["adobe_stock", "shutterstock", "freepik"], help="Nama target agensi")
    p_upload.add_argument("path", help="Path ke folder atau file gambar yang ingin diunggah")
    p_upload.set_defaults(func=cmd_upload)

    p_desktop = subparsers.add_parser("desktop", aliases=["dekstop"], parents=[api_parser], help="Buka antarmuka desktop native (Ultra-fast SPA < 35 MB RAM)")
    p_desktop.add_argument("--port", type=int, default=8505, help="Port local server (default: 8505)")
    p_desktop.set_defaults(func=cmd_desktop)

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

