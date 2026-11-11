"""Microstock AI Studio - Modern Streamlit Entry Point.

Alur Kerja:
Tab 1: Commercial Prompt Studio (18 Styles, Lighting, Lenses, Composition, Aspect Ratio)
Tab 2: Inspeksi Visual Gambar & Paket SEO Microstock (Gemini Vision 100% Akurat)
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
from microstock.prompt_enhancer import enhance_prompt
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
inject_css()

# Session State Initialization
st.session_state.setdefault("enhanced_prompt", "")
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


# Persistent Background Batch Monitor (Visible across all tabs)
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
                f"⚡ **Background Process Berjalan di Tab 2**: {job.status_text} ({int(job.progress * 100)}%)\n\n"
                "*Anda bebas membuka Tab 1, Tab 3, atau Tab 4. Proses batch tetap berjalan di latar belakang!*"
            )
            st.progress(job.progress)
        with c2:
            st.caption("Kontrol:")
            if st.button("⏹️ Batalkan", key="btn_cancel_bg_job", use_container_width=True):
                pool.cancel_job(job_id)
                st.session_state["active_batch_job_id"] = None
                st.toast("Proses background dibatalkan.")
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
        st.toast(f"🎉 Batch Vision Selesai! {len(res.get('items', []))} gambar telah diproses dan disimpan.", icon="✅")
        st.rerun()
    elif job.status == "failed":
        st.error(f"❌ Background Batch Processing Gagal: {job.error}")
        st.session_state["active_batch_job_id"] = None
        if st.button("Tutup Notifikasi", key="btn_close_err"):
            st.rerun()


render_background_batch_monitor()

# Workstation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Commercial Prompt Studio",
    "2. Inspeksi Gambar & Paket SEO (Gemini Vision)",
    "3. Reverse Prompt (Image to Prompt)",
    "4. Distribusi Contributor & Database Studio",
])

with tab1:
    with st.expander("10 Momen Komersial Mendatang", expanded=bool("market_trends" in st.session_state)):
        col_scan_text, col_scan_btn = st.columns([3, 1], gap="medium")
        with col_scan_text:
            st.caption("Pindai kalender momen global mendatang untuk menemukan 10 event bernilai komersial tinggi lengkap dengan 4 variasi sudut pandang.")
        with col_scan_btn:
            if st.button("Pindai 10 Momen", use_container_width=True, type="secondary"):
                if not api_key:
                    st.warning("Masukkan API Key di sidebar terlebih dahulu.")
                else:
                    with st.spinner("Menganalisis kalender momen global, media massa, dan tren unduhan microstock..."):
                        try:
                            from microstock.trend_analyzer import get_trending_ideas
                            client = config.get_client(api_key)
                            trends_data = get_trending_ideas(client)
                            st.session_state.market_trends = trends_data
                            st.session_state.selected_trend_idx = 0
                            st.session_state.trend_var_indices = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal mengambil tren: {e}")

        if "market_trends" in st.session_state:
            raw_data = st.session_state.market_trends
            trends_list = raw_data.get("trends", []) if isinstance(raw_data, dict) else raw_data
            if trends_list:
                import re
                from microstock.trend_analyzer import ensure_trend_variations

                if "selected_trend_idx" not in st.session_state:
                    st.session_state.selected_trend_idx = 0
                if "trend_var_indices" not in st.session_state:
                    st.session_state.trend_var_indices = {}

                pill_options = list(range(len(trends_list)))
                if "trend_pills_selector" not in st.session_state or st.session_state.trend_pills_selector is None:
                    st.session_state.trend_pills_selector = st.session_state.selected_trend_idx

                selected_idx = st.pills(
                    "Pilih Momen:",
                    options=pill_options,
                    format_func=lambda i: f"#{i+1} {trends_list[i].get('event_name', '')[:20]}",
                    label_visibility="collapsed",
                    key="trend_pills_selector",
                )
                if selected_idx is not None and selected_idx != st.session_state.selected_trend_idx:
                    st.session_state.selected_trend_idx = selected_idx
                    cur_trend = trends_list[selected_idx]
                    cur_vars = ensure_trend_variations(cur_trend)
                    cur_v_idx = st.session_state.trend_var_indices.get(selected_idx, 0) % len(cur_vars)
                    st.session_state.tab1_base_idea = cur_vars[cur_v_idx]

                active_idx = st.session_state.selected_trend_idx
                if active_idx >= len(trends_list):
                    active_idx = 0
                active_trend = trends_list[active_idx]

                variations = ensure_trend_variations(active_trend)
                var_idx = st.session_state.trend_var_indices.get(active_idx, 0) % len(variations)
                active_concept = variations[var_idx]

                if not st.session_state.get("tab1_base_idea"):
                    st.session_state.tab1_base_idea = active_concept

                raw_status = active_trend.get("market_status", "Viral")
                status_badge = re.sub(r"[^\w\s/]", "", str(raw_status)).strip() or "Viral"
                event_name = active_trend.get("event_name") or active_trend.get("category", "Momen Peringatan")
                target_date = active_trend.get("target_date", "Mendatang")
                rec_cat = active_trend.get("recommended_cat", "Fotografi (Photorealism)")
                rec_style = active_trend.get("recommended_style", "")
                rec_ratio = active_trend.get("recommended_ratio", "16:9")

                card_col1, card_col2 = st.columns([1.6, 1.4], gap="medium")
                with card_col1:
                    st.markdown(
                        f"""
                        <div class="ms-card-modern" style="padding:0.75rem 0.95rem; margin-bottom:0.4rem;">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
                            <b style="font-size:1.02rem; color:var(--text-accent);">{event_name}</b>
                            <span class="ms-step-badge ms-badge-amber" style="font-size:0.72rem; padding:2px 7px;">{status_badge}</span>
                          </div>
                          <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.3rem;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:3px;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                            <b>Waktu:</b> {target_date} &nbsp;·&nbsp;
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:3px;"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                            <b>Rekomendasi:</b> {rec_cat} · {rec_style or 'Standar'} ({rec_ratio})
                          </div>
                          <p style="font-size:0.82rem; color:var(--text-secondary); margin:0.15rem 0; line-height:1.35;">
                            <i>"{active_trend.get('reason', '')}"</i>
                          </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with card_col2:
                    st.markdown(
                        f"""
                        <div class="ms-card-modern" style="padding:0.75rem 0.95rem; margin-bottom:0.4rem; border-color:var(--accent-primary);">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
                            <span style="font-size:0.75rem; font-weight:700; color:var(--accent-primary); letter-spacing:0.5px;">
                              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px; margin-right:3px;"><path d="M9 18h6M10 22h4M15 2a6 6 0 0 0-6 6c0 2 1 3.5 2 4.5V14a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-1.5c1-1 2-2.5 2-4.5a6 6 0 0 0-6-6z"/></svg>
                              KONSEP VARIASI {var_idx + 1} DARI {len(variations)}
                            </span>
                          </div>
                          <div style="font-size:0.84rem; font-weight:600; color:var(--text-primary); min-height:42px; line-height:1.35;">
                            {active_concept}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                def _cycle_concept():
                    cur = st.session_state.trend_var_indices.get(active_idx, 0)
                    nxt = (cur + 1) % len(variations)
                    st.session_state.trend_var_indices[active_idx] = nxt
                    st.session_state.tab1_base_idea = variations[nxt]

                def _apply_current_trend():
                    st.session_state.tab1_base_idea = active_concept
                    if rec_cat in config.STYLE_CATEGORIES:
                        st.session_state.tab1_style_cat = rec_cat
                        if rec_style in config.STYLE_CATEGORIES[rec_cat]:
                            st.session_state.tab1_style_sub = rec_style
                        else:
                            st.session_state.tab1_style_sub = config.STYLE_CATEGORIES[rec_cat][0]
                    if rec_ratio in config.ASPECT_RATIOS:
                        st.session_state.tab1_ratio = rec_ratio

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.button(
                        f"Ganti Variasi ({var_idx + 1}/{len(variations)})",
                        key=f"cycle_var_{active_idx}",
                        on_click=_cycle_concept,
                        use_container_width=True,
                    )
                with btn_col2:
                    st.button(
                        "Terapkan ke Form",
                        key=f"apply_all_{active_idx}",
                        on_click=_apply_current_trend,
                        use_container_width=True,
                    )

    st.markdown("<div style='margin-bottom:0.6rem;'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        st.markdown(
            """
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:800; margin:0 0 0.8rem; color:var(--text-primary);">
              Parameter & Konsep Visual
            </h3>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Konsep Utama / Subjek Gambar**")
        base_idea = st.text_area(
            "Konsep Utama",
            key="tab1_base_idea",
            height=100,
            placeholder="Contoh: Seorang arsitek tampak belakang mengamati maket gedung modern dengan pencahayaan alami jendela",
            label_visibility="collapsed",
        )

        st.markdown("**Pilihan Gaya & Estetika Visual**")
        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            st.caption("Kategori Utama:")
            style_cat_list = list(config.STYLE_CATEGORIES.keys())
            if "tab1_style_cat" not in st.session_state or st.session_state.tab1_style_cat not in style_cat_list:
                st.session_state.tab1_style_cat = config.DEFAULT_STYLE_CATEGORY

            selected_category = st.selectbox(
                "Kategori Utama Gaya",
                options=style_cat_list,
                key="tab1_style_cat",
                label_visibility="collapsed",
            )

        with col_cat2:
            st.caption("Sub-Gaya Spesifik:")
            sub_styles = config.STYLE_CATEGORIES.get(selected_category, config.STYLE_CATEGORIES[config.DEFAULT_STYLE_CATEGORY])
            if "tab1_style_sub" not in st.session_state or st.session_state.tab1_style_sub not in sub_styles:
                st.session_state.tab1_style_sub = sub_styles[0]

            selected_style = st.selectbox(
                "Sub-Gaya Spesifik",
                options=sub_styles,
                key="tab1_style_sub",
                label_visibility="collapsed",
            )

        c_a, c_b = st.columns(2)
        with c_a:
            st.markdown("**Kondisi Pencahayaan (Lighting)**")
            selected_lighting = st.selectbox(
                "Pencahayaan",
                options=list(config.LIGHTING_OPTIONS.keys()),
                index=2,
                key="tab1_lighting",
                label_visibility="collapsed",
            )
        with c_b:
            st.markdown("**Lensa & Sudut Kamera**")
            selected_camera = st.selectbox(
                "Lensa Kamera",
                options=list(config.CAMERA_OPTIONS.keys()),
                index=0,
                key="tab1_camera",
                label_visibility="collapsed",
            )

        c_c, c_d = st.columns(2)
        with c_c:
            st.markdown("**Komposisi Framing**")
            selected_comp = st.selectbox(
                "Komposisi",
                options=list(config.COMPOSITION_OPTIONS.keys()),
                index=0,
                key="tab1_composition",
                label_visibility="collapsed",
            )
        with c_d:
            st.markdown("**Rasio Aspek (Aspect Ratio)**")
            selected_ratio = st.selectbox(
                "Rasio Aspek",
                options=list(config.ASPECT_RATIOS.keys()),
                format_func=lambda k: config.ASPECT_RATIO_LABELS[k],
                index=2,  # 16:9
                key="tab1_ratio",
                label_visibility="collapsed",
            )

        st.write("")
        btn_generate_prompt = st.button(
            "Generate Prompt Komersial",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
        )
        if not api_key:
            st.info("Masukkan Google Gemini API Key gratis di sidebar kiri terlebih dahulu.")

        if btn_generate_prompt:
            if not base_idea.strip():
                st.warning("Mohon tuliskan konsep utama gambar Anda terlebih dahulu.")
            else:
                with st.spinner("Meracik prompt fotografi komersial profesional..."):
                    try:
                        client = config.get_client(api_key)
                        res_prompt = enhance_prompt(
                            client=client,
                            base_idea=base_idea,
                            style_name=selected_style,
                            aspect_ratio=selected_ratio,
                            lighting=selected_lighting,
                            camera=selected_camera,
                            composition=selected_comp,
                        )
                        st.session_state.enhanced_prompt = res_prompt
                        st.toast("Prompt komersial berhasil diracik.")
                    except Exception as e:
                        st.error(f"Gagal membuat prompt: {e}")

    with col_right:
        st.markdown(
            """
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:800; margin:0 0 0.8rem; color:var(--text-primary);">
              Output Prompt Siap Salin
            </h3>
            """,
            unsafe_allow_html=True,
        )

        prompt_val = st.session_state.enhanced_prompt
        if prompt_val:
            # Handle string and legacy list gracefully
            if isinstance(prompt_val, list):
                prompt_text = prompt_val[0] if prompt_val else ""
            else:
                prompt_text = str(prompt_val)
            if isinstance(prompt_text, dict):
                prompt_text = prompt_text.get("prompt", "")

            st.code(prompt_text, language=None, wrap_lines=True)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.link_button(
                    "Buka Gemini Web",
                    "https://gemini.google.com",
                    use_container_width=True,
                    type="primary",
                )
            with c_btn2:
                if st.button("Bersihkan Prompt", use_container_width=True):
                    st.session_state.enhanced_prompt = ""
                    st.rerun()

            with st.expander("Panduan Alur Kerja Auto-Sync:", expanded=True):
                st.markdown(
                    """
                    1. **Salin Prompt**: Klik tombol salin di sudut kanan atas kotak prompt.
                    2. **Tempel di Gemini Web**: Buka `gemini.google.com` dan tempelkan prompt.
                    3. **Download Gambar**: Unduh gambar pilihan Anda di web Gemini.
                    4. **Buka Tab 2**: Gambar yang baru diunduh otomatis terdeteksi via Auto-Sync, siap di-upscale dan disusun 50 keywords SEO.
                    """
                )
        else:
            st.markdown(
                """
                <div class="ms-card-modern" style="border: 2px dashed var(--border-color); padding: 2rem 1.5rem; text-align: center;">
                  <b style="font-size: 1.05rem; display: block; margin-bottom: 0.5rem; color: var(--text-primary);">Prompt Anda Akan Muncul Di Sini</b>
                  <p style="color: var(--text-secondary); font-size: 0.92rem; margin: 0; font-weight: 500;">
                    Tuliskan konsep dasar di panel kiri, pilih gaya & lensa, lalu klik <b>Generate Prompt Komersial</b>.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


with tab2:
    with st.expander("Auto-Sync Folder Download", expanded=True):
        st.markdown(
            """
            <p style="font-size:0.88rem; color:var(--text-secondary); margin:0 0 0.5rem; font-weight:500;">
              Mendeteksi otomatis gambar yang diunduh dari <b>gemini.google.com</b> dan mengakumulasi gambar baru tanpa duplikasi.
            </p>
            """,
            unsafe_allow_html=True,
        )
        col_w1, col_w2, col_w3 = st.columns([2.5, 2, 1.2])
        with col_w1:
            watch_path = st.text_input(
                "Folder Download:",
                value=st.session_state.get("watch_dir", folder_watcher.get_default_downloads_dir()),
                key="input_watch_dir",
                help="Folder penyimpanan unduhan Gemini Web.",
            )
            st.session_state["watch_dir"] = watch_path
        with col_w2:
            selected_window = st.selectbox(
                "Rentang Waktu Unduhan:",
                options=list(folder_watcher.TIME_WINDOWS.keys()),
                index=0,
                help="Mendeteksi gambar dalam rentang waktu yang dipilih.",
            )
        with col_w3:
            st.caption("Aksi:")
            btn_scan = st.button("Pindai Folder", use_container_width=True)

        pending_dl = folder_watcher.check_pending_downloads(watch_path)
        if pending_dl > 0:
            st.info(f"{pending_dl} file sedang dalam proses unduh di browser. Tunggu selesai, lalu klik Pindai Folder.")

        cutoff = folder_watcher.get_cutoff_timestamp(selected_window)
        found_files = folder_watcher.scan_recent_images(watch_path, since_timestamp=cutoff, max_files=50)

        current_imported = st.session_state.get("imported_from_watcher", [])
        existing_filenames = {item[0] for item in current_imported}

        if found_files:
            unimported_count = sum(1 for fn, _, _, _ in found_files if fn not in existing_filenames)
            st.markdown(
                f"**Terdeteksi {len(found_files)} gambar** "
                f"({unimported_count} baru, {len(found_files) - unimported_count} sudah di antrean):"
            )

            thumb_cols = st.columns(min(len(found_files), 5))
            for i, (fn, fpath, mtime, fsize) in enumerate(found_files[:5]):
                with thumb_cols[i]:
                    img_data = folder_watcher.read_image_bytes(fpath)
                    if img_data:
                        tag_str = "[Baru]" if fn not in existing_filenames else "[Antrean]"
                        st.image(img_data[1], caption=f"{tag_str} {fn[:14]} ({fsize//1024} KB)", use_container_width=True)

            c_imp1, c_imp2 = st.columns([2.5, 1.5])
            with c_imp1:
                btn_add_label = f"Tambahkan {unimported_count} Gambar ke Antrean" if unimported_count > 0 else "Semua Gambar Sudah di Antrean"
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
                    st.toast(f"{added_count} gambar ditambahkan ke antrean.")
                    st.rerun()
            with c_imp2:
                if current_imported:
                    if st.button(f"Kosongkan Antrean ({len(current_imported)})", use_container_width=True):
                        st.session_state["imported_from_watcher"] = []
                        st.rerun()
        else:
            st.markdown(
                f"""
                <div class="ms-card-modern" style="border: 1px dashed var(--border-color); padding: 1.2rem; text-align: center; margin-top: 0.5rem;">
                  <b style="font-size: 0.95rem; color: var(--text-primary); display: block; margin-bottom: 0.25rem;">Belum Ada Gambar Baru yang Terdeteksi</b>
                  <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0; line-height: 1.4;">
                    Unduh gambar dari Gemini Web ke folder <code>{watch_path}</code>, lalu klik tombol Pindai Folder.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if current_imported:
                if st.button(f"Kosongkan Antrean ({len(current_imported)})", use_container_width=True):
                    st.session_state["imported_from_watcher"] = []
                    st.rerun()

    # 2. MANUAL FILE UPLOADER (ALTERNATIVE)
    uploaded_files = st.file_uploader(
        "Atau unggah file manual (JPG, PNG, WebP):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Anda dapat mengunggah 1 hingga 10+ file gambar sekaligus.",
    )

    # Combine images from Auto-Sync watcher AND manual uploader with duplicate disambiguation
    image_entries = []  # list of (filename, raw_bytes, mime)
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
            <div style="display:inline-flex; align-items:center; gap:0.5rem; background:rgba(37,99,235,0.12); border:1px solid rgba(59,130,246,0.3); border-radius:8px; padding:0.4rem 0.9rem; margin-bottom:0.8rem;">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#3B82F6;"></span>
              <span style="font-weight:700; color:var(--text-accent); font-size:0.92rem;">Siap Dianalisis: {len(image_entries)} Gambar dalam Antrean</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(
                """
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                  <b style="font-size:1rem; color:var(--text-primary); font-family:'Space Grotesk',sans-serif;">
                    Pengaturan Upscaler & Standar Microstock
                  </b>
                  <span class="ms-step-badge ms-badge-green" style="font-size:0.72rem;">NCNN Vulkan</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_up1, col_up2 = st.columns([1.1, 0.9])
            with col_up1:
                do_upscale = st.checkbox(
                    "Lakukan Upscale Gambar (Otomatis Standar Microstock)",
                    value=False,
                    help="Menggunakan mesin Upscayl NCNN CLI lokal. Sistem otomatis menghitung rasio perbesaran agar resolusi gambar dijamin minimal 4 Megapiksel (≥ 4 MP)."
                )
                if do_upscale:
                    upscale_mode = st.radio(
                        "Pilihan Mode Resolusi Upscale:",
                        [
                            "Smart Microstock (~8 MP · Standar 4K)",
                            "Ultra 4x (~16-25 MP · Resolusi Penuh)",
                        ],
                        index=0,
                        help="Smart Microstock melakukan upscale AI 4x untuk detail tajam, lalu mengoptimalkan dimensi ke standar 4K (~8 MP) agar file tidak membengkak dan cepat diunggah. Ultra 4x mempertahankan resolusi biner 4x penuh."
                    )
                    if "Smart" in upscale_mode:
                        st.caption("Mode Smart Microstock: Detail tajam, dimensi optimal ~8 MP, ukuran file hemat (3-6 MB).")
                    else:
                        st.caption("Mode Ultra 4x: Resolusi biner 4x penuh (16-25 MP), ukuran file berkisar 10-25 MB.")
                else:
                    upscale_mode = "Off"

            with col_up2:
                enforce_4mb = False
                if do_upscale:
                    enforce_4mb = st.checkbox(
                        "Wajibkan ukuran file fisik minimal 4 MB",
                        value=False,
                        help="Standar wajib untuk kurasi Freepik / Vecteezy. Jika dicentang, berkas dipadatkan dengan padding marker non-destruktif sehingga dijamin ≥ 4 MB tanpa mengubah kualitas pixel."
                    )
                    if enforce_4mb:
                        st.caption("Standar Freepik/Vecteezy: Ukuran file fisik minimal 4 MB.")
                    else:
                        st.caption("Aktifkan jika mengirim ke agensi yang mewajibkan file minimal 4 MB.")

        st.markdown("<br>", unsafe_allow_html=True)
        is_job_running = False
        active_job_id = st.session_state.get("active_batch_job_id")
        if active_job_id:
            j = queue.get_worker_pool().get_job(active_job_id)
            if j and j.status == "running":
                is_job_running = True

        if is_job_running:
            st.info("⚡ **Pemrosesan sedang berlangsung di latar belakang.** Anda bebas berpindah tab sambil memantau bilah status di atas.")

        btn_analyze = st.button(
            "⏳ Sedang Memproses di Background..." if is_job_running else f"Mulai Analisis {len(image_entries)} Gambar & Susun Metadata SEO",
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
            st.toast("⚡ Analisis batch dimulai di background. Anda bebas berpindah tab!", icon="🚀")
            st.rerun()

        # Last completed summary banner
        last_info = st.session_state.get("last_completed_job_info")
        if last_info and not is_job_running:
            st.success(f"Berhasil menganalisis {last_info['count']} gambar.")
            if last_info.get("do_upscale"):
                mode_label = "Smart Microstock ~8 MP" if "Smart" in last_info.get("upscale_mode", "") else "Ultra 4x Penuh"
                rule_info = f"mode {mode_label}, resolusi minimal 4 MP" + (" dan file fisik minimal 4 MB" if last_info.get("enforce_4mb") else "")
                st.info(f"Gambar hasil upscale ({rule_info}) dan file CSV otomatis tersimpan di folder lokal:\n`{last_info['local_dir']}`")
            else:
                st.info(f"File metadata CSV otomatis tersimpan di folder lokal:\n`{last_info['local_dir']}`")

    # Display Results & Export Hub
    package = st.session_state.batch_package
    if package:
        st.divider()
        render_export_hub(
            df=package["df"],
            zip_bytes=package["zip"],
            zip_name=package["zip_name"],
            csv_bytes=package["csv"],
            batch_id=package["id"],
        )

        st.divider()
        st.subheader("Hasil Inspeksi & Metadata Gambar")
        render_results_grid(package["items"], package["id"])


with tab3:
    uploaded_ref_files = st.file_uploader(
        "Pilih atau seret gambar referensi Anda (JPG, PNG, WebP):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="tab3_ref_uploader",
        help="Unggah 1 atau beberapa gambar referensi untuk diubah menjadi prompt.",
    )

    ref_entries = []
    if uploaded_ref_files:
        for uf in uploaded_ref_files:
            ref_entries.append((uf.name, uf.getvalue(), uf.type or "image/jpeg"))

    if ref_entries:
        st.markdown(
            f"""
            <div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:10px; padding:0.85rem; margin-bottom:1rem;">
              <span class="ms-step-badge ms-badge-amber" style="font-size:0.88rem; font-weight:700; display:inline-block; margin-bottom:0.35rem;">{len(ref_entries)} Gambar Referensi Siap Dianalisis</span>
              <p style="font-size:0.85rem; color:var(--text-primary); margin:0.25rem 0 0;">
                File gambar hanya diproses di memori dan tidak disimpan di disk. Prompt yang dihasilkan akan otomatis disimpan dalam format <code>*.txt</code> di folder <code>exports/prompts/</code>.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        btn_reverse = st.button(
            f"Analisis {len(ref_entries)} Gambar & Buat Prompt Bersih",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
            key="btn_reverse_prompt",
        )

        if btn_reverse:
            client = config.get_client(api_key)
            from microstock.reverse_prompt import _detect_ratio, generate_reverse_prompt_async, save_prompt_to_file

            results = []
            rev_progress = st.progress(0.0, text="Memulai analisis reverse prompt...")

            async def process_all_reverse():
                for idx, (filename, raw_bytes, mime) in enumerate(ref_entries):
                    rev_progress.progress(idx / len(ref_entries), text=f"Menganalisis visual #{idx+1} dari {len(ref_entries)}: {filename}...")
                    
                    # Read dimensions with PIL for ratio detection
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
                        st.toast(f"Gagal menganalisis {filename}: {e}")
                        ratio = _detect_ratio(w, h)
                        prompt_str = f"Commercial microstock asset [Aspect Ratio: {ratio}]"
                        saved_path = ""

                    results.append({
                        "filename": filename,
                        "raw_bytes": raw_bytes,
                        "prompt": prompt_str,
                        "saved_path": saved_path,
                    })

            with st.spinner("Gemini Vision sedang membedah visual dan menyusun prompt komersial..."):
                asyncio.run(process_all_reverse())
                rev_progress.progress(1.0, text=f"Selesai! {len(results)} prompt berhasil dibuat.")

            st.session_state.reverse_results = results
            st.toast("Reverse Prompt berhasil dibuat dan disimpan!")

    # Display results
    if "reverse_results" in st.session_state and st.session_state.reverse_results:
        st.divider()
        st.markdown(
            """
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.3rem; font-weight:800; margin:0 0 1rem; color:var(--text-primary);">
              Hasil Reverse Prompt (Tersimpan di Disk)
            </h3>
            """,
            unsafe_allow_html=True,
        )

        for i, item in enumerate(st.session_state.reverse_results):
            with st.container(border=True):
                col_img, col_prompt = st.columns([1, 2.5], gap="medium")
                with col_img:
                    st.image(item["raw_bytes"], caption=item["filename"], use_container_width=True)
                    if item.get("saved_path"):
                        rel_path = os.path.relpath(item["saved_path"], os.path.dirname(os.path.abspath(__file__)))
                        st.caption(f"File: `{rel_path}`")
                with col_prompt:
                    st.markdown(f"**Prompt #{i+1} (Siap Pakai & Bersih):**")
                    st.code(item["prompt"], language=None, wrap_lines=True)
                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        st.link_button(
                            "Buka Google Gemini Web",
                            "https://gemini.google.com",
                            use_container_width=True,
                        )
                    with c_act2:
                        if st.button("Kirim ke Tab 1", key=f"send_tab1_{i}", use_container_width=True):
                            st.session_state.tab1_base_idea = item["prompt"]
                            st.toast("Prompt berhasil dikirim ke Tab 1!")


with tab4:
    st.markdown(
        """
        <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.35rem; font-weight:800; margin:0 0 0.5rem; color:var(--text-primary);">
          Studio Database & Contributor Distribution Hub
        </h3>
        <p style="color:var(--text-secondary); font-size:0.9rem; margin-bottom:1.2rem;">
          Arsip aset lokal terenkripsi (SQLite WAL), proteksi duplikasi pHash, dan pengiriman batch via FTP/SFTP langsung ke Adobe Stock, Shutterstock, dan Freepik.
        </p>
        """,
        unsafe_allow_html=True,
    )

    from microstock import analytics, db, distributor, metadata, security

    sec_info = security.get_security_status()
    kc_status = "macOS Keychain Native" if sec_info.get("keychain_supported") else "Encrypted Local Vault (PBKDF2 0600)"
    st.markdown(
        f"""
        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:8px; padding:0.5rem 0.8rem; margin-bottom:1rem; display:flex; align-items:center; justify-content:space-between;">
          <span style="font-size:0.82rem; color:var(--text-primary);">
            🔒 <b>Keamanan Kredensial:</b> {kc_status} Aktif · 0 Plaintext Passwords di Basis Data
          </span>
          <span class="ms-step-badge ms-badge-green" style="font-size:0.7rem;">Vault Aman</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. DATABASE ASSETS OVERVIEW & CURATION TELEMETRY
    recent_assets = db.list_recent_assets(limit=50)
    cur_stats = analytics.get_curation_analytics()
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Aset Terindeks", len(recent_assets))
    with col_m2:
        injected_count = sum(1 for a in recent_assets if a.get("is_xmp_injected"))
        st.metric("IPTC / XMP Embedded", f"{injected_count} Aset")
    with col_m3:
        st.metric("Total Terkirim SFTP", f"{cur_stats.get('total_submissions', 0)} Batch")
    with col_m4:
        st.metric("Tingkat Sukses Pengiriman", f"{cur_stats.get('upload_success_rate', 100.0)}%")

    with st.expander("Tabel Aset Terindeks di Database Lokal", expanded=True):
        if recent_assets:
            import pandas as pd
            display_rows = []
            missing_on_disk = 0
            for a in recent_assets:
                mp = (a.get("width", 0) * a.get("height", 0)) / 1_000_000
                fpath = a.get("file_path", "")
                exists = os.path.exists(fpath) if fpath else False
                if not exists:
                    missing_on_disk += 1
                display_rows.append({
                    "Status File": "✅ Ada di Komputer" if exists else "⚠️ Terhapus / Pindah",
                    "Nama File": a.get("file_name", ""),
                    "Resolusi": f"{a.get('width', 0)}x{a.get('height', 0)} ({mp:.1f} MP)",
                    "Rasio": a.get("aspect_ratio", ""),
                    "pHash": a.get("phash_hex", "")[:8] + "...",
                    "IPTC Embedded": "Ya" if a.get("is_xmp_injected") else "Tidak",
                    "Kategori": f"#{a.get('adobe_category_id', 12)} {metadata.ADOBE_CATEGORIES.get(a.get('adobe_category_id', 12), '')}",
                    "Judul": a.get("title", ""),
                    "Tanggal": str(a.get("created_at", ""))[:19],
                })

            col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 3])
            with col_b1:
                if st.button("🧹 Bersihkan Aset Hilang", help="Hapus entri database yang file fisiknya sudah terhapus di folder komputer", use_container_width=True):
                    removed = db.prune_missing_assets()
                    st.toast(f"Berhasil membersihkan {removed} aset yang sudah tidak ada di komputer.", icon="🧹")
                    st.rerun()
            with col_b2:
                if st.button("🗑️ Kosongkan Database Master", help="Hapus semua riwayat indeks database lokal", use_container_width=True):
                    cleared = db.clear_all_assets()
                    st.toast(f"Berhasil mengosongkan {cleared} aset dari database.", icon="🗑️")
                    st.rerun()
            with col_b3:
                if missing_on_disk > 0:
                    st.warning(f"⚠️ Terdeteksi {missing_on_disk} file yang sudah terhapus/berpindah dari folder komputer.")

            st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Database lokal masih kosong. Belum ada aset gambar yang terindeks.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. AGENCY CREDENTIALS & DIRECT SFTP/FTP DISPATCH
    with st.container(border=True):
        st.markdown(
            """
            <b style="font-size:1.05rem; color:var(--text-primary); font-family:'Space Grotesk',sans-serif;">
              Pengaturan Endpoint & Kredensial Contributor
            </b>
            <p style="font-size:0.85rem; color:var(--text-secondary); margin:0.2rem 0 0.8rem;">
              Masukkan akun kontributor FTP/SFTP resmi untuk mengunggah gambar langsung dari komputer Anda.
            </p>
            """,
            unsafe_allow_html=True,
        )

        col_ag1, col_ag2 = st.columns([1.2, 2.8], gap="medium")
        with col_ag1:
            selected_agency_key = st.selectbox(
                "Pilih Agensi Stok:",
                options=list(distributor.AGENCY_ENDPOINTS.keys()),
                format_func=lambda k: distributor.AGENCY_ENDPOINTS[k]["name"],
            )
            agency_meta = distributor.AGENCY_ENDPOINTS[selected_agency_key]
            st.caption(f"Host Default: `{agency_meta['host']}`")
            st.caption(f"Port / Protokol: `{agency_meta['port']}` ({agency_meta['protocol'].upper()})")

            if selected_agency_key == "adobe_stock":
                st.markdown(
                    """
                    <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:6px; padding:0.5rem 0.6rem; margin-top:0.5rem; font-size:0.75rem; color:var(--text-secondary);">
                      ⚠️ <b>Kebijakan Adobe Stock:</b> SFTP kini hanya dibuka Adobe untuk akun terverifikasi. Untuk akun baru, unggah file langsung di web <code>contributor.stock.adobe.com</code>. Judul dan 50 kata kunci otomatis terisi dari metadata XMP JPEG tanpa butuh CSV!
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
            if st.button("📂 Buka Folder Hasil di Finder", use_container_width=True):
                export_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
                import subprocess, sys
                if sys.platform == "darwin":
                    subprocess.run(["open", export_base])
                elif sys.platform == "win32":
                    os.startfile(export_base)
                else:
                    subprocess.run(["xdg-open", export_base])

        with col_ag2:
            saved_cred = db.get_agency_account(selected_agency_key) or {}
            c_host, c_port = st.columns([3, 1])
            with c_host:
                input_host = st.text_input("Server Host:", value=saved_cred.get("host", agency_meta["host"]))
            with c_port:
                input_port = st.number_input("Port:", value=int(saved_cred.get("port", agency_meta["port"])))

            c_user, c_pass = st.columns(2)
            with c_user:
                input_user = st.text_input("Username / ID Kontributor:", value=saved_cred.get("username", ""))
            with c_pass:
                input_pass = st.text_input("Password / FTP Token:", value=saved_cred.get("password", ""), type="password")

            c_act_save, c_act_test = st.columns(2)
            with c_act_save:
                if st.button("Simpan Kredensial Agensi", type="primary", use_container_width=True):
                    if input_user and input_pass:
                        db.save_agency_account(
                            agency_name=selected_agency_key,
                            host=input_host,
                            port=int(input_port),
                            protocol=agency_meta["protocol"],
                            username=input_user,
                            password=input_pass,
                        )
                        st.toast("Kredensial agensi berhasil disimpan di database lokal!")
                    else:
                        st.warning("Username dan Password tidak boleh kosong.")

            with c_act_test:
                if st.button("Tes Koneksi Server", use_container_width=True):
                    if input_host and input_user and input_pass:
                        with st.spinner("Menguji jabat tangan koneksi server..."):
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
                                st.error(f"Gagal koneksi: {msg}")
                    else:
                        st.warning("Lengkapi parameter host, username, dan password terlebih dahulu.")

    # 3. SUBMISSION LOGS
    with st.expander("Log Riwayat Pengiriman & Upload (Submission Logs)", expanded=False):
        sub_logs = db.list_recent_submissions(limit=30)
        if sub_logs:
            import pandas as pd
            log_rows = []
            for l in sub_logs:
                log_rows.append({
                    "Agensi": distributor.AGENCY_ENDPOINTS.get(l.get("agency_name", ""), {}).get("name", l.get("agency_name", "")),
                    "Nama File": l.get("remote_filename", ""),
                    "Status": l.get("status", ""),
                    "Protokol": l.get("submission_type", "").upper(),
                    "Waktu Upload": str(l.get("uploaded_at", ""))[:19],
                    "Error": l.get("error_message") or "-",
                })
            st.dataframe(pd.DataFrame(log_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada riwayat pengiriman via FTP/SFTP.")


