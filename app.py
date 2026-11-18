"""Microstock AI Studio - Modern Streamlit Entry Point.

Unified Workstation Studio:
- Left Column: Commercial Prompt Studio & 32 Visual Styles
- Right Column: Auto-Sync & Vision Studio (SEO Keywords, Upscaler, Export)
- Collapsible Bottom: Reverse Prompt & Database/Distribution Hub
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="urllib3")
warnings.filterwarnings("ignore", message=".*urllib3.*")

import asyncio
import io
import os
import time
import uuid

from PIL import Image
import streamlit as st

from microstock import analytics, config, db, distributor, folder_watcher, metadata, queue, security
from microstock.export import build_metadata_dataframe, build_zip, dataframe_to_csv_bytes
from microstock.image_generator import BatchItem, finalize_image
from microstock.metadata import generate_metadata_from_vision_async
from microstock.prompt_enhancer import enhance_prompt, generate_thematic_series
from microstock.ui_components import (
    inject_css,
    render_export_hub,
    render_header,
    render_results_grid,
    render_sidebar,
)

st.set_page_config(
    page_title="Microstock AI Studio Pro",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css(is_dark=False)

# Session State Initialization
st.session_state.setdefault("enhanced_prompt", "")
st.session_state.setdefault("thematic_series", [])
st.session_state.setdefault("restyle_prompt", "")
st.session_state.setdefault("tab1_output_mode", "")
st.session_state.setdefault("vision_items", [])
st.session_state.setdefault("batch_package", None)
st.session_state.setdefault("imported_from_watcher", [])
st.session_state.setdefault("watch_dir", folder_watcher.get_default_downloads_dir())

api_key = render_sidebar()
render_header()


def _run_batch_vision_job(
    image_entries: list[tuple[str, bytes, str]],
    api_key: str,
    do_upscale: bool,
    upscale_mode: str,
    enforce_4mb: bool,
    watch_path: str,
    progress_callback=None,
) -> dict:
    import asyncio
    import io
    import os
    import time
    from PIL import Image

    from microstock import config, db
    from microstock.export import build_metadata_dataframe, build_zip, dataframe_to_csv_bytes
    from microstock.image_generator import BatchItem, finalize_image
    from microstock.metadata import create_fallback_metadata, generate_metadata_from_vision_async
    from microstock.phash import compute_phash
    from microstock.reverse_prompt import _detect_ratio
    from microstock.upscaler import is_upscale_needed, upscale_bytes

    client = config.get_client(api_key)
    processed_items: list[BatchItem] = []
    total = len(image_entries)

    async def _async_worker():
        for idx, (filename, raw_bytes, mime) in enumerate(image_entries):
            step_pct = idx / total
            if progress_callback:
                progress_callback(step_pct, f"Menganalisis visual #{idx+1} dari {total}: {filename}...")

            # Generate vision metadata
            md = None
            try:
                md = await generate_metadata_from_vision_async(
                    client=client,
                    image_bytes=raw_bytes,
                    mime_type=mime,
                    label=f"Gambar #{idx+1}",
                )
            except Exception:
                md = create_fallback_metadata(filename)

            target_bytes = raw_bytes
            if do_upscale:
                try:
                    with Image.open(io.BytesIO(raw_bytes)) as _tmp_im:
                        orig_w, orig_h = _tmp_im.size
                except Exception:
                    orig_w, orig_h = 1024, 1024

                if is_upscale_needed(orig_w, orig_h):
                    if progress_callback:
                        progress_callback(step_pct, f"AI Upscale #{idx+1} dari {total}: {filename}...")
                    target_bytes, success, err_msg = await asyncio.to_thread(upscale_bytes, raw_bytes)
                else:
                    if progress_callback:
                        progress_callback(step_pct, f"Gambar #{idx+1} sudah beresolusi tinggi (≥ 4 MP)...")

            if progress_callback:
                progress_callback(step_pct, f"Menyiapkan resolusi & preview #{idx+1}...")

            is_smart = "Smart" in upscale_mode if do_upscale else False
            exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                finalize_image,
                target_bytes,
                "JPEG",
                enforce_microstock_res=do_upscale,
                enforce_min_filesize=enforce_4mb,
                max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS if (do_upscale and is_smart) else None,
                jpeg_quality=95,
                metadata=md,
            )

            phash_val = compute_phash(exp_bytes)
            dups = db.find_near_duplicates_in_db(phash_val, max_hamming_distance=5)
            dup_risk = "HIGH" if (dups and dups[0][1] <= 3) else ("MEDIUM" if dups else None)

            item = BatchItem(
                index=idx,
                variation=f"Uploaded {filename}",
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
                duplicate_risk=dup_risk,
            )
            processed_items.append(item)

            resolved_path = os.path.join(watch_path if (watch_path and os.path.isdir(watch_path)) else os.getcwd(), filename)
            db.save_asset(
                file_path=resolved_path,
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
            if progress_callback:
                progress_callback((idx + 1) / total, f"Selesai #{idx+1}/{total} gambar")

    asyncio.run(_async_worker())

    df = build_metadata_dataframe(processed_items)
    zip_bytes = build_zip(processed_items, None, df)
    csv_bytes = dataframe_to_csv_bytes(df)

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    local_export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports", f"batch_{timestamp}")
    os.makedirs(local_export_dir, exist_ok=True)

    if do_upscale:
        for it in processed_items:
            if it.image_bytes:
                with open(os.path.join(local_export_dir, it.filename), "wb") as f_img:
                    f_img.write(it.image_bytes)

    with open(os.path.join(local_export_dir, "metadata.csv"), "wb") as f_csv:
        f_csv.write(csv_bytes)

    return {
        "items": processed_items,
        "df": df,
        "zip": zip_bytes,
        "zip_name": f"microstock-pack-{timestamp}.zip",
        "csv": csv_bytes,
        "local_dir": local_export_dir,
        "do_upscale": do_upscale,
        "upscale_mode": upscale_mode,
        "enforce_4mb": enforce_4mb,
    }


# Persistent Background Batch Monitor
@st.fragment(run_every="1.5s")
def render_background_batch_monitor():
    job_id = st.session_state.get("active_batch_job_id")
    if not job_id:
        return
    pool = queue.get_worker_pool()
    job = pool.get_job(job_id)
    if not job:
        st.session_state["active_batch_job_id"] = None
        return

    if job.status == "running":
        c1, c2 = st.columns([4.2, 0.8])
        with c1:
            st.info(
                f"**Pemrosesan Latar Belakang**: {job.status_text} ({int(job.progress * 100)}%)\n\n"
                "*Proses batch tetap berjalan di latar belakang.*"
            )
            st.progress(job.progress)
        with c2:
            st.caption("Kontrol:")
            if st.button("Batalkan", key="btn_cancel_bg_job", use_container_width=True):
                pool.cancel_job(job_id)
                st.session_state["active_batch_job_id"] = None
                st.toast("Proses latar belakang dibatalkan.")
                st.rerun()
    elif job.status == "completed":
        res = job.result
        if res:
            st.session_state.vision_items = res["items"]
            st.session_state.batch_package = {
                "id": uuid.uuid4().hex[:8],
                "items": res["items"],
                "df": res["df"],
                "zip": res["zip"],
                "zip_name": res["zip_name"],
                "csv": res["csv"],
                "local_dir": res["local_dir"],
            }
            st.session_state["last_completed_job_info"] = {
                "count": len(res["items"]),
                "local_dir": res["local_dir"],
                "do_upscale": res.get("do_upscale", False),
                "upscale_mode": res.get("upscale_mode", "Off"),
                "enforce_4mb": res.get("enforce_4mb", False),
            }
        st.session_state["active_batch_job_id"] = None
        st.toast(f"Batch vision selesai. {len(res.get('items', []))} gambar berhasil diproses.")
        st.rerun()
    elif job.status == "failed":
        st.error(f"Pemrosesan latar belakang gagal: {job.error}")
        st.session_state["active_batch_job_id"] = None
        if st.button("Tutup Notifikasi", key="btn_close_err"):
            st.rerun()


render_background_batch_monitor()

# ---------------------------------------------------------
# Workstation Studio: 2 Columns Side-by-Side (Zero Tabs)
# ---------------------------------------------------------
col_prompt, col_vision = st.columns([1, 1], gap="large")

with col_prompt:
    st.markdown(
        """
        <div style="margin-bottom:0.6rem;">
          <h2 style="font-family:'Plus Jakarta Sans',sans-serif; font-size:1.15rem; font-weight:700; margin:0; color:var(--text-primary);">
            Prompt Studio
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    base_idea = st.text_area(
        "Konsep Subjek",
        key="tab1_base_idea",
        height=95,
        placeholder="Tulis konsep gambar (misal: Barista menyeduh pour-over coffee di kafe modern pagi hari, uap hangat, cangkir estetik)",
        label_visibility="collapsed",
    )

    style_names = [vs.name for vs in config.VISUAL_STYLES_32]

    def _format_style_choice(sname: str) -> str:
        vs = config.VISUAL_STYLES_MAP.get(sname)
        if vs:
            return f"{vs.name} ({vs.characteristic_id}) · {vs.category}"
        return sname

    selected_style = st.selectbox(
        "Style Visual (32 Pilihan):",
        options=style_names,
        index=23,  # Foto Studio
        format_func=_format_style_choice,
        key="tab1_selected_style",
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_series = st.button(
            "Racik 5 Sudut Seri",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
        )
    with col_btn2:
        btn_restyle = st.button(
            "Format Foto Restyle",
            type="secondary",
            use_container_width=True,
        )

    if btn_series:
        if not base_idea.strip():
            st.warning("Tuliskan konsep utama gambar terlebih dahulu.")
        else:
            with st.spinner(f"Meracik 5 sudut seri dengan style '{selected_style}'..."):
                try:
                    client = config.get_client(api_key)
                    series_results = generate_thematic_series(
                        client=client,
                        base_idea=base_idea,
                        style_name=selected_style,
                    )
                    st.session_state.thematic_series = series_results
                    st.session_state.tab1_output_mode = "series"
                    st.toast("Koleksi seri 5-sudut berhasil diracik.")
                except Exception as e:
                    st.error(f"Gagal meracik koleksi seri: {e}")

    if btn_restyle:
        restyle_prompt_text = config.format_photo_restyle_prompt(selected_style)
        st.session_state.restyle_prompt = restyle_prompt_text
        st.session_state.tab1_output_mode = "restyle"
        st.toast(f"Prompt restyle '{selected_style}' siap.")

    # Output Area in Left Column
    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    if st.session_state.get("tab1_output_mode") == "series" and st.session_state.get("thematic_series"):
        series = st.session_state.thematic_series
        c_head1, c_head2 = st.columns([1.8, 1.2])
        with c_head1:
            st.markdown(
                f"""
                <span style="font-weight:700; color:var(--text-primary); font-size:0.92rem;">
                  Hasil Seri: {len(series)} Sudut Komersial
                </span>
                """,
                unsafe_allow_html=True,
            )
        with c_head2:
            st.link_button("Buka Gemini Web", "https://gemini.google.com", use_container_width=True, type="primary")

        for idx, item in enumerate(series):
            shot_title = item.get("title", f"Shot #{idx+1}")
            shot_badge = item.get("badge", "Commercial")
            with st.expander(f"{idx+1}. {shot_title} ({shot_badge})", expanded=(idx == 0)):
                st.code(item.get("prompt", ""), language=None, wrap_lines=True)

        if st.button("Bersihkan Koleksi Seri", use_container_width=True):
            st.session_state.thematic_series = []
            st.session_state.tab1_output_mode = ""
            st.rerun()

    elif st.session_state.get("tab1_output_mode") == "restyle" and st.session_state.get("restyle_prompt"):
        st.markdown(
            """
            <div style="margin-bottom:0.4rem;">
              <span style="font-weight:700; color:var(--text-primary); font-size:0.92rem;">
                Formula Transformasi Foto
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(st.session_state.restyle_prompt, language=None, wrap_lines=True)
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            st.link_button("Buka Gemini Web", "https://gemini.google.com", use_container_width=True, type="primary")
        with c_r2:
            if st.button("Tutup Restyle", use_container_width=True):
                st.session_state.restyle_prompt = ""
                st.session_state.tab1_output_mode = ""
                st.rerun()
    else:
        st.markdown(
            """
            <div class="ms-card-modern" style="border: 1px dashed var(--border-color); padding: 1.2rem 1rem; text-align: center; margin-top:0.4rem;">
              <span style="font-size:0.88rem; font-weight:500; color:var(--text-muted);">
                Pilih style lalu klik tombol di atas untuk menyusun prompt.
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


with col_vision:
    st.markdown(
        """
        <div style="margin-bottom:0.6rem;">
          <h2 style="font-family:'Plus Jakarta Sans',sans-serif; font-size:1.15rem; font-weight:700; margin:0; color:var(--text-primary);">
            Vision & Auto-Sync
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_w1, col_w2, col_w3 = st.columns([2.5, 1.5, 1.0])
    with col_w1:
        watch_path = st.text_input(
            "Folder Unduhan",
            value=st.session_state.get("watch_dir", folder_watcher.get_default_downloads_dir()),
            key="input_watch_dir",
            label_visibility="collapsed",
        )
        st.session_state["watch_dir"] = watch_path
    with col_w2:
        selected_window = st.selectbox(
            "Rentang",
            options=list(folder_watcher.TIME_WINDOWS.keys()),
            index=0,
            label_visibility="collapsed",
        )
    with col_w3:
        btn_scan = st.button("Pindai Folder", use_container_width=True)

    pending_dl = folder_watcher.check_pending_downloads(watch_path)
    if pending_dl > 0:
        st.info(f"{pending_dl} file sedang diunduh di browser. Klik Pindai jika sudah selesai.")

    cutoff = folder_watcher.get_cutoff_timestamp(selected_window)
    found_files = folder_watcher.scan_recent_images(watch_path, since_timestamp=cutoff, max_files=50)
    current_imported = st.session_state.get("imported_from_watcher", [])
    existing_filenames = {item[0] for item in current_imported}

    if found_files:
        unimported_count = sum(1 for fn, _, _, _ in found_files if fn not in existing_filenames)
        thumb_cols = st.columns(min(len(found_files), 5))
        for i, (fn, fpath, mtime, fsize) in enumerate(found_files[:5]):
            with thumb_cols[i]:
                img_data = folder_watcher.read_image_bytes(fpath)
                if img_data:
                    tag_str = "Baru" if fn not in existing_filenames else "Antrean"
                    st.image(img_data[1], caption=f"[{tag_str}] {fn[:12]} ({fsize//1024} KB)", use_container_width=True)

        c_imp1, c_imp2 = st.columns([2.5, 1.5])
        with c_imp1:
            btn_add_label = f"Tambahkan {unimported_count} Gambar Baru" if unimported_count > 0 else "Semua Sudah di Antrean"
            if st.button(btn_add_label, type="primary", use_container_width=True, disabled=unimported_count == 0):
                added_count = 0
                for fn, fpath, mtime, fsize in found_files:
                    if fn not in existing_filenames:
                        data = folder_watcher.read_image_bytes(fpath)
                        if data:
                            current_imported.append(data)
                            existing_filenames.add(fn)
                            added_count += 1
                st.session_state["imported_from_watcher"] = current_imported
                st.toast(f"{added_count} gambar dimasukkan ke antrean.")
                st.rerun()
        with c_imp2:
            if current_imported:
                if st.button(f"Kosongkan ({len(current_imported)})", use_container_width=True):
                    st.session_state["imported_from_watcher"] = []
                    st.rerun()

    uploaded_files = st.file_uploader(
        "Upload manual (JPG, PNG, WebP):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="manual_uploader",
        label_visibility="collapsed",
    )

    image_entries = []
    seen_filenames = set()

    def _add_entry(raw_name: str, raw_bytes: bytes, mime_type: str) -> None:
        name = os.path.basename(raw_name).strip()
        stem, ext = os.path.splitext(name)
        candidate = name
        counter = 1
        while candidate.lower() in seen_filenames:
            candidate = f"{stem}_{counter}{ext}"
            counter += 1
        seen_filenames.add(candidate.lower())
        image_entries.append((candidate, raw_bytes, mime_type or "image/jpeg"))

    if st.session_state.get("imported_from_watcher"):
        for fn, raw_b, mime_t in st.session_state["imported_from_watcher"]:
            _add_entry(fn, raw_b, mime_t)

    if uploaded_files:
        for uf in uploaded_files:
            _add_entry(uf.name, uf.getvalue(), uf.type or "image/jpeg")

    if image_entries:
        st.markdown(
            f"""
            <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:6px; padding:0.4rem 0.8rem; margin:0.5rem 0;">
              <span style="font-weight:600; color:var(--text-primary); font-size:0.86rem;">
                Antrean: {len(image_entries)} gambar siap dianalisis
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            do_upscale = st.checkbox(
                "Upscale resolusi standar (≥ 4 MP)",
                value=False,
                key="chk_upscale",
            )
            upscale_mode = "Smart Microstock (~8 MP)" if do_upscale else "Off"
        with col_opt2:
            enforce_4mb = False
            if do_upscale:
                enforce_4mb = st.checkbox(
                    "Wajib file fisik ≥ 4 MB (Freepik/Vecteezy)",
                    value=False,
                    key="chk_4mb",
                )

        is_job_running = False
        active_job_id = st.session_state.get("active_batch_job_id")
        if active_job_id:
            j = queue.get_worker_pool().get_job(active_job_id)
            if j and j.status == "running":
                is_job_running = True

        btn_analyze = st.button(
            "Sedang memproses di latar belakang..." if is_job_running else f"Analisis {len(image_entries)} Gambar & Susun Metadata",
            type="primary",
            use_container_width=True,
            disabled=bool(is_job_running or not api_key),
        )

        if btn_analyze and not is_job_running:
            job_id = queue.get_worker_pool().submit(
                f"Batch Vision ({len(image_entries)} gambar)",
                _run_batch_vision_job,
                image_entries,
                api_key,
                do_upscale,
                upscale_mode,
                enforce_4mb,
                watch_path,
            )
            st.session_state["active_batch_job_id"] = job_id
            st.toast("Analisis batch dimulai di latar belakang.")
            st.rerun()

    # Results & Export Hub
    package = st.session_state.batch_package
    if package:
        st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
        render_export_hub(
            df=package["df"],
            zip_bytes=package["zip"],
            zip_name=package["zip_name"],
            csv_bytes=package["csv"],
            batch_id=package["id"],
        )
        with st.expander("Tinjau Detail Hasil & Grid Gambar", expanded=False):
            render_results_grid(package["items"], package["id"])


# ---------------------------------------------------------
# Secondary Tools (Collapsible Bottom Utilities)
# ---------------------------------------------------------
st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

with st.expander("Reverse Prompt (Ekstrak Prompt dari Gambar Referensi)", expanded=False):
    uploaded_ref_files = st.file_uploader(
        "Unggah gambar referensi:",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="tab3_ref_uploader",
    )
    ref_entries = []
    if uploaded_ref_files:
        for uf in uploaded_ref_files:
            ref_entries.append((uf.name, uf.getvalue(), uf.type or "image/jpeg"))

    if ref_entries:
        btn_reverse = st.button(
            f"Analisis {len(ref_entries)} Gambar & Buat Prompt",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
            key="btn_reverse_prompt",
        )
        if btn_reverse:
            client = config.get_client(api_key)
            from microstock.reverse_prompt import _detect_ratio, generate_reverse_prompt_async, save_prompt_to_file

            results = []
            rev_progress = st.progress(0.0, text="Menganalisis visual...")

            async def process_all_reverse():
                for idx, (filename, raw_bytes, mime) in enumerate(ref_entries):
                    rev_progress.progress(idx / len(ref_entries), text=f"Menganalisis visual #{idx+1}: {filename}...")
                    try:
                        with Image.open(io.BytesIO(raw_bytes)) as im:
                            w, h = im.size
                    except Exception:
                        w, h = 1920, 1080

                    try:
                        prompt_str = await generate_reverse_prompt_async(
                            client=client,
                            image_bytes=raw_bytes,
                            mime_type=mime,
                            label=f"Reverse #{idx+1}",
                            width=w,
                            height=h,
                        )
                        saved_path = save_prompt_to_file(prompt_str, filename)
                    except Exception as e:
                        st.toast(f"Gagal {filename}: {e}")
                        ratio = _detect_ratio(w, h)
                        prompt_str = f"Commercial microstock asset [Aspect Ratio: {ratio}]"
                        saved_path = ""

                    results.append({
                        "filename": filename,
                        "raw_bytes": raw_bytes,
                        "prompt": prompt_str,
                        "saved_path": saved_path,
                    })

            asyncio.run(process_all_reverse())
            rev_progress.progress(1.0, text="Selesai!")
            st.session_state.reverse_results = results
            st.toast("Reverse prompt berhasil dibuat.")

    if "reverse_results" in st.session_state and st.session_state.reverse_results:
        for i, item in enumerate(st.session_state.reverse_results):
            with st.container(border=True):
                c_img, c_p = st.columns([1, 3])
                with c_img:
                    st.image(item["raw_bytes"], caption=item["filename"], use_container_width=True)
                with c_p:
                    st.markdown(f"**Prompt #{i+1}:**")
                    st.code(item["prompt"], language=None, wrap_lines=True)
                    if st.button("Kirim ke Prompt Studio", key=f"send_studio_{i}"):
                        st.session_state.tab1_base_idea = item["prompt"]
                        st.toast("Prompt dikirim ke Prompt Studio.")
                        st.rerun()


with st.expander("Database Aset & Distribusi Kontributor (FTP / SFTP)", expanded=False):
    from microstock import analytics, db, distributor, metadata, security

    recent_assets = db.list_recent_assets(limit=50)
    cur_stats = analytics.get_curation_analytics()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Aset Terindeks", len(recent_assets))
    with m2:
        injected_count = sum(1 for a in recent_assets if a.get("is_xmp_injected"))
        st.metric("IPTC Embedded", f"{injected_count} Aset")
    with m3:
        st.metric("Terkirim SFTP", f"{cur_stats.get('total_submissions', 0)} Batch")
    with m4:
        st.metric("Tingkat Sukses", f"{cur_stats.get('upload_success_rate', 100.0)}%")

    if recent_assets:
        import pandas as pd
        display_rows = []
        for a in recent_assets:
            mp = (a.get("width", 0) * a.get("height", 0)) / 1_000_000
            fpath = a.get("file_path", "")
            exists = os.path.exists(fpath) if fpath else False
            display_rows.append({
                "Status": "Tersedia" if exists else "Hilang",
                "File": a.get("file_name", ""),
                "Resolusi": f"{a.get('width', 0)}x{a.get('height', 0)} ({mp:.1f} MP)",
                "Judul": a.get("title", ""),
                "Tanggal": str(a.get("created_at", ""))[:19],
            })

        c_b1, c_b2, _ = st.columns([1.5, 1.5, 3])
        with c_b1:
            if st.button("Bersihkan File Hilang", use_container_width=True):
                removed = db.prune_missing_assets()
                st.toast(f"Dibersihkan {removed} aset.")
                st.rerun()
        with c_b2:
            if st.button("Kosongkan Database", use_container_width=True):
                cleared = db.clear_all_assets()
                st.toast(f"Dikosongkan {cleared} aset.")
                st.rerun()

        st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)
    else:
        st.info("Database aset lokal masih kosong.")

    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    st.markdown("**Pengaturan Agensi Kontributor:**")
    c_ag1, c_ag2 = st.columns([1.2, 2.8], gap="medium")
    with c_ag1:
        selected_agency_key = st.selectbox(
            "Pilih Agensi:",
            options=list(distributor.AGENCY_ENDPOINTS.keys()),
            format_func=lambda k: distributor.AGENCY_ENDPOINTS[k]["name"],
        )
        agency_meta = distributor.AGENCY_ENDPOINTS[selected_agency_key]
        if st.button("Buka Folder Exports", use_container_width=True):
            export_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
            import subprocess, sys
            if sys.platform == "darwin":
                subprocess.run(["open", export_base])
            elif sys.platform == "win32":
                os.startfile(export_base)
            else:
                subprocess.run(["xdg-open", export_base])

    with c_ag2:
        saved_cred = db.get_agency_account(selected_agency_key) or {}
        ch1, ch2 = st.columns([3, 1])
        with ch1:
            input_host = st.text_input("Server Host:", value=saved_cred.get("host", agency_meta["host"]))
        with ch2:
            input_port = st.number_input("Port:", value=int(saved_cred.get("port", agency_meta["port"])))

        cu1, cu2 = st.columns(2)
        with cu1:
            input_user = st.text_input("Username:", value=saved_cred.get("username", ""))
        with cu2:
            input_pass = st.text_input("Password:", value=saved_cred.get("password", ""), type="password")

        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("Simpan Kredensial", type="primary", use_container_width=True):
                if input_user and input_pass:
                    db.save_agency_account(
                        agency_name=selected_agency_key,
                        host=input_host,
                        port=int(input_port),
                        protocol=agency_meta["protocol"],
                        username=input_user,
                        password=input_pass,
                    )
                    st.toast("Kredensial disimpan.")
                else:
                    st.warning("Username dan Password tidak boleh kosong.")
        with ca2:
            if st.button("Tes Koneksi", use_container_width=True):
                if input_host and input_user and input_pass:
                    with st.spinner("Menguji koneksi..."):
                        success, msg = distributor.test_agency_connection(
                            host=input_host,
                            port=int(input_port),
                            protocol=agency_meta["protocol"],
                            username=input_user,
                            password=input_pass,
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(f"Gagal: {msg}")
                else:
                    st.warning("Lengkapi parameter host, username, dan password.")
