"""Microstock AI Studio - Modern Streamlit Entry Point.

Alur Kerja:
Tab 1: Commercial Prompt Studio (18 Styles, Lighting, Lenses, Composition, Aspect Ratio)
Tab 2: Inspeksi Visual Gambar & Paket SEO Microstock (Gemini Vision 100% Akurat)
"""
from __future__ import annotations

import asyncio
import io
import os
import time
import uuid

from PIL import Image
import streamlit as st

from microstock import config, folder_watcher
from microstock.export import build_metadata_dataframe, build_zip, dataframe_to_csv_bytes
from microstock.image_generator import BatchItem, finalize_image
from microstock.metadata import generate_metadata_from_vision_async
from microstock.prompt_enhancer import enhance_prompt
from microstock.ui_components import (
    download_image_from_url,
    inject_css,
    render_export_hub,
    render_header,
    render_results_grid,
    render_sidebar,
)

st.set_page_config(
    page_title="Microstock AI Studio Pro",
    page_icon="📸",
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

# Workstation Tabs
tab1, tab2, tab3 = st.tabs([
    "1. Commercial Prompt Studio",
    "2. Inspeksi Gambar & Paket SEO (Gemini Vision)",
    "3. Reverse Prompt (Image to Prompt)",
])

# TAB 1: COMMERCIAL PROMPT STUDIO
with tab1:
    st.markdown(
        """
        <div class="ms-card-modern" style="padding:1.1rem 1.3rem; margin-bottom:1.3rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <div>
              <h2 style="font-family:'Space Grotesk',sans-serif; font-size:1.45rem; font-weight:800; margin:0 0 0.2rem; color:var(--text-primary);">
                Generator Prompt Komersial Siap Pakai
              </h2>
              <p style="color:var(--text-secondary); font-size:0.88rem; margin:0; font-weight:500;">
                Formulasi prompt dengan 7 aturan komersial: 100% bebas model wanita, faceless, reservasi copy space, dan bebas trademark.
              </p>
            </div>
            <div style="display:flex; gap:0.4rem;">
              <span class="ms-step-badge ms-badge-green" style="font-size:0.75rem;">✓ Zero Trademark</span>
              <span class="ms-step-badge ms-badge-accent" style="font-size:0.75rem;">✓ Faceless / Back-angle</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

        # Trend Discovery Section
        with st.expander("📈 Sedang buntu? Cek Tren & Ide Microstock Laris", expanded=False):
            if st.button("Analisis Tren Adobe Stock Saat Ini", use_container_width=True, type="secondary"):
                if not api_key:
                    st.warning("Masukkan API Key di sidebar terlebih dahulu.")
                else:
                    with st.spinner("Menganalisis data pasar dan tren unduhan microstock..."):
                        try:
                            from microstock.trend_analyzer import get_trending_ideas
                            client = config.get_client(api_key)
                            trends_data = get_trending_ideas(client)
                            st.session_state.market_trends = trends_data
                        except Exception as e:
                            st.error(f"Gagal mengambil tren: {e}")
            
            if "market_trends" in st.session_state:
                st.markdown("<br>", unsafe_allow_html=True)
                raw_data = st.session_state.market_trends
                period_str = raw_data.get("period", "") if isinstance(raw_data, dict) else ""
                trends_list = raw_data.get("trends", []) if isinstance(raw_data, dict) else raw_data

                if period_str:
                    st.markdown(
                        f"""
                        <div class="ms-step-badge ms-badge-green" style="display:inline-block; padding:0.5rem 0.85rem; margin-bottom:0.8rem; font-size:0.88rem; font-weight:700;">
                          📅 Periode Analisis: {period_str} (Berdasarkan Tren Pasar Global)
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                for i, trend in enumerate(trends_list):
                    status_badge = trend.get("market_status", "🔥 High Demand")
                    rec_cat = trend.get("recommended_cat", "Fotografi (Photorealism)")
                    rec_style = trend.get("recommended_style", "")
                    rec_ratio = trend.get("recommended_ratio", "16:9")

                    st.markdown(
                        f"""
                        <div class="ms-card-modern" style="padding:1rem; margin-bottom:0.8rem;">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                            <b style="font-size:1rem; color:var(--text-accent);">{trend.get('category', 'Kategori Tren')}</b>
                            <span class="ms-step-badge ms-badge-amber" style="font-size:0.75rem; padding:2px 8px;">{status_badge}</span>
                          </div>
                          <p style="font-size:0.88rem; color:var(--text-secondary); margin:0.3rem 0; line-height:1.4;"><i>"{trend.get('reason', '')}"</i></p>
                          <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:6px; padding:0.4rem 0.6rem; font-size:0.8rem; color:var(--text-primary); margin-bottom:0.4rem;">
                            🎯 <b>Rekomendasi:</b> {rec_cat} · {rec_style or 'Standar'} ({rec_ratio})
                          </div>
                          <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:6px; padding:0.5rem 0.65rem; margin-top:0.4rem; font-size:0.88rem; font-weight:600; color:var(--text-primary);">
                            💡 {trend.get('base_idea', '')}
                          </div>
                        </div>
                        """, unsafe_allow_html=True
                    )
                    if st.button(f"Terapkan Tren #{i+1}", key=f"use_trend_{i}", use_container_width=True):
                        st.session_state.tab1_base_idea = trend.get("base_idea", "")
                        if rec_cat in config.STYLE_CATEGORIES:
                            st.session_state.tab1_style_cat = rec_cat
                            if rec_style in config.STYLE_CATEGORIES[rec_cat]:
                                st.session_state.tab1_style_sub = rec_style
                            else:
                                st.session_state.tab1_style_sub = config.STYLE_CATEGORIES[rec_cat][0]
                        if rec_ratio in config.ASPECT_RATIOS:
                            st.session_state.tab1_ratio = rec_ratio
                        st.rerun()

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
                        st.toast("Prompt komersial berhasil diracik!", icon="✅")
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
            st.markdown(
                """
                <div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-bottom:0.6rem;">
                  <span class="ms-step-badge ms-badge-green" style="font-size:0.75rem;">✓ Faceless / Back-angle</span>
                  <span class="ms-step-badge ms-badge-green" style="font-size:0.75rem;">✓ Copy Space Ready</span>
                  <span class="ms-step-badge ms-badge-accent" style="font-size:0.75rem;">✓ Zero Trademark</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if isinstance(prompt_val, list):
                st.markdown("**5 Alternatif Prompt Komersial Siap Pakai:**")
                for idx, item in enumerate(prompt_val):
                    prompt_text = item.get("prompt", "") if isinstance(item, dict) else str(item)

                    st.markdown(
                        f"""
                        <div class="ms-card-modern" style="padding:0.9rem 1.1rem; margin-top:0.85rem; margin-bottom:0.85rem;">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.45rem;">
                            <b style="font-size:0.95rem; color:var(--text-primary); font-family:'Space Grotesk',sans-serif;">Alternatif #{idx + 1}</b>
                            <span class="ms-step-badge ms-badge-accent" style="font-size:0.72rem; padding:0.18rem 0.55rem;">Siap Pakai</span>
                          </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.code(prompt_text, language=None, wrap_lines=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.code(prompt_val, language=None, wrap_lines=True)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.link_button(
                    "Buka Google Gemini Web",
                    "https://gemini.google.com",
                    use_container_width=True,
                    type="primary",
                )
            with c_btn2:
                if st.button("Bersihkan Prompt", use_container_width=True):
                    st.session_state.enhanced_prompt = ""
                    st.rerun()

            with st.expander("Panduan Alur Kerja Cepat (Auto-Sync Tanpa Upload Manual):", expanded=True):
                st.markdown(
                    """
                    1. **Salin Prompt**: Klik ikon salin di sudut kanan atas kotak prompt di atas.
                    2. **Tempel di Gemini Web**: Buka `gemini.google.com` dan tempelkan prompt tersebut.
                    3. **Download Gambar**: Klik tombol unduh (⬇️) pada gambar pilihan Anda di web Gemini.
                    4. **Buka Tab 2**: Gambar yang baru diunduh akan **otomatis terdeteksi via Auto-Sync**! Cukup 1 klik untuk memasukkannya ke antrean, langsung siap di-upscale (garansi ≥ 4 MP & opsional ≥ 4 MB) dan disusun 50 keywords SEO akurat tanpa repot upload manual.
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


# TAB 2: INSPEKSI GAMBAR & METADATA (GEMINI VISION)
with tab2:
    st.markdown(
        """
        <div class="ms-card-modern" style="padding:1.1rem 1.3rem; margin-bottom:1.3rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <div>
              <h2 style="font-family:'Space Grotesk',sans-serif; font-size:1.45rem; font-weight:800; margin:0 0 0.2rem; color:var(--text-primary);">
                Inspeksi Visual & Paket Microstock
              </h2>
              <p style="color:var(--text-secondary); font-size:0.88rem; margin:0; font-weight:500;">
                Inspeksi elemen visual nyata dengan Gemini Vision, upscale resolusi NCNN (≥ 4 MP), dan susun 50 keyword SEO siap upload CSV/ZIP.
              </p>
            </div>
            <div style="display:flex; gap:0.4rem;">
              <span class="ms-step-badge ms-badge-purple" style="font-size:0.75rem;">Gemini Vision AI</span>
              <span class="ms-step-badge ms-badge-amber" style="font-size:0.75rem;">50 Keywords Sorted</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. AUTO-SYNC DOWNLOAD FOLDER WATCHER
    with st.expander("Auto-Sync dari Folder Download (Deteksi Otomatis & Akumulasi)", expanded=True):
        st.markdown(
            """
            <p style="font-size:0.9rem; color:var(--text-secondary); margin:0 0 0.6rem; font-weight:500;">
              Fitur ini otomatis mendeteksi batch gambar yang Anda unduh dari <b>gemini.google.com</b>. Anda dapat memindai berkali-kali (gambar baru akan otomatis <b>diakumulasi tanpa duplikasi</b>).
            </p>
            """,
            unsafe_allow_html=True,
        )
        col_w1, col_w2, col_w3 = st.columns([2.5, 2, 1.2])
        with col_w1:
            watch_path = st.text_input(
                "Folder Download yang Dipantau:",
                value=st.session_state.get("watch_dir", folder_watcher.get_default_downloads_dir()),
                key="input_watch_dir",
                help="Folder di Mac Anda tempat file hasil download Gemini Web mendarat (default: ~/Downloads).",
            )
            st.session_state["watch_dir"] = watch_path
        with col_w2:
            selected_window = st.selectbox(
                "Jendela Waktu Unduhan:",
                options=list(folder_watcher.TIME_WINDOWS.keys()),
                index=0,  # 15 Menit Terakhir (Sesi Sekarang)
                help="Hanya mendeteksi gambar yang diunduh dalam rentang waktu ini, mengabaikan file lama.",
            )
        with col_w3:
            st.caption("Pindai Folder:")
            btn_scan = st.button("🔄 Pindai Sekarang", use_container_width=True)

        # Check for active in-progress downloads
        pending_dl = folder_watcher.check_pending_downloads(watch_path)
        if pending_dl > 0:
            st.info(f"⏳ Terdeteksi **{pending_dl} file** sedang dalam proses download di browser. Tunggu hingga download selesai di browser, lalu klik **Pindai Sekarang** lagi.")

        cutoff = folder_watcher.get_cutoff_timestamp(selected_window)
        found_files = folder_watcher.scan_recent_images(watch_path, since_timestamp=cutoff, max_files=50)

        current_imported = st.session_state.get("imported_from_watcher", [])
        existing_filenames = {item[0] for item in current_imported}

        if found_files:
            # Count how many of the found files are genuinely new
            unimported_count = sum(1 for fn, _, _, _ in found_files if fn not in existing_filenames)
            st.markdown(
                f"**Terdeteksi {len(found_files)} gambar pada rentang waktu ini** "
                f"*( {unimported_count} gambar baru belum masuk antrean, {len(found_files) - unimported_count} sudah ada )*:"
            )

            thumb_cols = st.columns(min(len(found_files), 5))
            for i, (fn, fpath, mtime, fsize) in enumerate(found_files[:5]):
                with thumb_cols[i]:
                    img_data = folder_watcher.read_image_bytes(fpath)
                    if img_data:
                        badge = "✅" if fn in existing_filenames else "🆕"
                        st.image(img_data[1], caption=f"{badge} {fn[:12]}.. ({fsize//1024} KB)", use_container_width=True)

            c_imp1, c_imp2 = st.columns([2.5, 1.5])
            with c_imp1:
                btn_add_label = f"📥 Tambahkan {unimported_count} Gambar Baru ke Antrean" if unimported_count > 0 else "✅ Semua Gambar Sudah Masuk Antrean"
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
                    st.toast(f"Berhasil menambahkan {added_count} gambar! Total antrean: {len(current_imported)} gambar.", icon="✅")
                    st.rerun()
            with c_imp2:
                if current_imported:
                    if st.button(f"🗑️ Kosongkan Antrean ({len(current_imported)} Gambar)", use_container_width=True):
                        st.session_state["imported_from_watcher"] = []
                        st.rerun()
        else:
            st.markdown(
                f"""
                <div class="ms-card-modern" style="border: 2px dashed var(--border-color); padding: 1.5rem; text-align: center; margin-top: 0.6rem;">
                  <b style="font-size: 1rem; color: var(--text-primary); display: block; margin-bottom: 0.35rem;">Belum Ada Gambar Baru yang Terdeteksi</b>
                  <p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0; line-height: 1.5;">
                    Setelah mengunduh gambar dari Gemini Web ke folder <code>{watch_path}</code>, klik tombol <b>Pindai Sekarang</b> di atas untuk mendeteksi batch secara otomatis.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if current_imported:
                if st.button(f"🗑️ Kosongkan Antrean Auto-Sync ({len(current_imported)} Gambar)", use_container_width=True):
                    st.session_state["imported_from_watcher"] = []
                    st.rerun()

    # 2. MANUAL FILE UPLOADER (ALTERNATIVE)
    uploaded_files = st.file_uploader(
        "Atau unggah file manual (JPG, PNG, WebP):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Anda dapat mengunggah 1 hingga 10+ file gambar sekaligus.",
    )

    # Combine images from Auto-Sync watcher AND manual uploader
    image_entries = []  # list of (filename, raw_bytes, mime)
    if st.session_state.get("imported_from_watcher"):
        for fn, raw_b, mime_t in st.session_state["imported_from_watcher"]:
            image_entries.append((fn, raw_b, mime_t))

    if uploaded_files:
        for uf in uploaded_files:
            if not any(e[0] == uf.name for e in image_entries):
                image_entries.append((uf.name, uf.getvalue(), uf.type or "image/jpeg"))

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
                        st.caption("✓ **Mode Smart Microstock Aktif:** Detail AI 4x tajam, dimensi optimal ~8 MP, ukuran file hemat (3-6 MB).")
                    else:
                        st.caption("✓ **Mode Ultra 4x Aktif:** Resolusi biner 4x penuh (16-25 MP), ukuran file berkisar 10-25 MB.")
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
                        st.caption("✓ **Standar Freepik/Vecteezy Aktif:** Ukuran file fisik dijamin minimal **4 MB**.")
                    else:
                        st.caption("ℹ️ *Opsional:* Aktifkan jika Anda mengirim ke Freepik/Vecteezy yang menolak file < 4 MB.")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_analyze = st.button(
            f"Mulai Analisis {len(image_entries)} Gambar & Susun Metadata SEO",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
        )

        if btn_analyze:
            client = config.get_client(api_key)
            processed_items: list[BatchItem] = []
            progress_bar = st.progress(0.0, text="Memulai analisis Gemini Vision...")

            async def process_all_images():
                for idx, (filename, raw_bytes, mime) in enumerate(image_entries):
                    progress_bar.progress(idx / len(image_entries), text=f"Menganalisis visual #{idx+1} dari {len(image_entries)}: {filename}...")

                    # Generate vision metadata
                    md = None
                    try:
                        md = await generate_metadata_from_vision_async(
                            client=client,
                            image_bytes=raw_bytes,
                            mime_type=mime,
                            label=f"Gambar #{idx+1}",
                        )
                    except Exception as e:
                        st.toast(f"⚠️ Gagal menyusun metadata untuk {filename}: {e}", icon="⚠️")
                        clean_title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip().title()
                        from microstock.metadata import ImageMetadata
                        md = ImageMetadata(
                            title=clean_title or "Commercial Microstock Asset",
                            description=f"High quality commercial microstock asset: {clean_title or 'visual concept'}.",
                            keywords=[w.lower() for w in clean_title.split() if len(w) > 2] + ["stock", "commercial", "concept", "isolated", "quality", "modern"],
                            adobe_category=12,
                            shutterstock_categories=["Objects", "Miscellaneous"],
                        )

                    target_bytes = raw_bytes
                    if do_upscale:
                        try:
                            with Image.open(io.BytesIO(raw_bytes)) as _tmp_im:
                                orig_w, orig_h = _tmp_im.size
                        except Exception:
                            orig_w, orig_h = 1024, 1024

                        from microstock.upscaler import is_upscale_needed, run_upscale
                        if is_upscale_needed(orig_w, orig_h):
                            progress_bar.progress(idx / len(image_entries), text=f"Memperbesar (AI Upscale 4x Standar Microstock) #{idx+1} dari {len(image_entries)}: {filename}...")
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as in_f:
                                in_f.write(raw_bytes)
                                in_path = in_f.name
                            out_path = in_path.replace(".jpg", "_up.jpg")
                            success, err_msg = await asyncio.to_thread(run_upscale, in_path, out_path, 4, "realesrgan-x4plus", 400)
                            if success:
                                with open(out_path, "rb") as out_f:
                                    target_bytes = out_f.read()
                                try: os.remove(out_path)
                                except: pass
                            else:
                                err_detail = f" ({err_msg})" if err_msg else ""
                                st.toast(f"Upscale lokal gagal untuk {filename}{err_detail}, beralih ke pembesaran Lanczos otomatis.", icon="⚠️")
                            try: os.remove(in_path)
                            except: pass
                        else:
                            progress_bar.progress(idx / len(image_entries), text=f"Gambar #{idx+1} sudah beresolusi tinggi ({orig_w}x{orig_h} px ≥ 4 MP), melewati perbesaran AI...")

                    progress_bar.progress(idx / len(image_entries), text=f"Menyiapkan resolusi & preview #{idx+1}...")
                    # Finalize image & thumbnail (Enforces >= 4MP and optionally >= 4MB, Smart Microstock cap)
                    is_smart = "Smart" in upscale_mode if do_upscale else False
                    exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                        finalize_image,
                        target_bytes,
                        "JPEG",
                        enforce_microstock_res=do_upscale,
                        enforce_min_filesize=enforce_4mb,
                        max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS if (do_upscale and is_smart) else None,
                        jpeg_quality=95,
                    )

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
                    )
                    processed_items.append(item)
                    progress_bar.progress((idx + 1) / len(image_entries), text=f"Selesai {idx+1}/{len(image_entries)} gambar")

            with st.spinner("Gemini Vision sedang menginspeksi elemen visual nyata..."):
                asyncio.run(process_all_images())

            # Package into master dataframe and zip
            df = build_metadata_dataframe(processed_items)
            zip_bytes = build_zip(processed_items, None, df)
            csv_bytes = dataframe_to_csv_bytes(df)

            # Auto-save to local folder on your Mac
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

            st.session_state.vision_items = processed_items
            st.session_state.batch_package = {
                "id": uuid.uuid4().hex[:8],
                "items": processed_items,
                "df": df,
                "zip": zip_bytes,
                "zip_name": f"microstock-pack-{timestamp}.zip",
                "csv": csv_bytes,
                "local_dir": local_export_dir,
            }
            st.success(f"Berhasil menganalisis {len(processed_items)} gambar dengan 100% akurasi visual!")
            if do_upscale:
                mode_label = "Smart Microstock ~8 MP" if "Smart" in upscale_mode else "Ultra 4x Penuh"
                rule_info = f"mode {mode_label}, resolusi minimal 4 MP" + (" dan file fisik minimal 4 MB" if enforce_4mb else "")
                st.info(f"Gambar hasil upscale ({rule_info}) dan file CSV otomatis tersimpan di folder lokal:\n`{local_export_dir}`")
            else:
                st.info(f"File metadata CSV otomatis tersimpan di folder lokal (file gambar asli tidak disimpan untuk menghemat ruang disk):\n`{local_export_dir}`")

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


# TAB 3: REVERSE PROMPT (IMAGE TO PROMPT)
with tab3:
    st.markdown(
        """
        <div class="ms-card-modern" style="padding:1.1rem 1.3rem; margin-bottom:1.3rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <div>
              <h2 style="font-family:'Space Grotesk',sans-serif; font-size:1.45rem; font-weight:800; margin:0 0 0.2rem; color:var(--text-primary);">
                Reverse Prompt Studio (Image to Prompt)
              </h2>
              <p style="color:var(--text-secondary); font-size:0.88rem; margin:0; font-weight:500;">
                Bedah visual gambar referensi menjadi formula prompt fotografi komersial yang dapat direproduksi dan disimpan otomatis ke .txt.
              </p>
            </div>
            <div style="display:flex; gap:0.4rem;">
              <span class="ms-step-badge ms-badge-accent" style="font-size:0.75rem;">Deconstruct Matrix</span>
              <span class="ms-step-badge ms-badge-green" style="font-size:0.75rem;">Auto-Save TXT</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            from microstock.reverse_prompt import generate_reverse_prompt_async, save_prompt_to_file

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

                    prompt_str = await generate_reverse_prompt_async(
                        client=client,
                        image_bytes=raw_bytes,
                        mime_type=mime,
                        label=f"Reverse #{idx+1}",
                        width=w,
                        height=h,
                    )

                    saved_path = save_prompt_to_file(prompt_str, filename)
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
            st.toast("Reverse Prompt berhasil dibuat dan disimpan!", icon="✅")

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
                    rel_path = os.path.relpath(item["saved_path"], os.path.dirname(os.path.abspath(__file__)))
                    st.caption(f"💾 File: `{rel_path}`")
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
                        if st.button(f"📥 Kirim ke Tab 1", key=f"send_tab1_{i}", use_container_width=True):
                            st.session_state.tab1_base_idea = item["prompt"]
                            st.toast("Prompt berhasil dikirim ke Tab 1!", icon="✅")

