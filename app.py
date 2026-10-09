"""Microstock Magic Studio — Modern Streamlit Entry Point.

Alur Kerja:
Tab 1: Magic Prompt Studio (18 Styles, Lighting, Lenses, Composition, Aspect Ratio)
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

from microstock import config
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
    page_title="Microstock AI Studio",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# --------------------------------------------------------------------------- #
# Session State Initialization
# --------------------------------------------------------------------------- #
st.session_state.setdefault("enhanced_prompt", "")
st.session_state.setdefault("vision_items", [])
st.session_state.setdefault("batch_package", None)

api_key = render_sidebar()
render_header()

# --------------------------------------------------------------------------- #
# Modern Neo-Pop Tabs Layout
# --------------------------------------------------------------------------- #
tab1, tab2 = st.tabs([
    "1. Magic Prompt Studio",
    "2. Inspeksi Gambar & Paket SEO (Gemini Vision)",
])

# =========================================================================== #
# TAB 1: GENERATOR MAGIC PROMPT
# =========================================================================== #
with tab1:
    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
          <h2 style="font-family:'Space Grotesk',sans-serif; font-size:1.6rem; font-weight:800; margin:0 0 0.3rem;">
            Generator Prompt Komersial Siap Pakai
          </h2>
          <p style="color:#4A4853; font-size:0.95rem; margin:0; font-weight:600;">
            Kombinasikan konsep dasar dengan parameter fotografi pro. Hasilnya 100% patuh aturan hak cipta Adobe Stock.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        st.markdown(
            """
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:800; margin:0 0 0.8rem; color:#1A191E;">
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
                            trends = get_trending_ideas(client)
                            st.session_state.market_trends = trends
                        except Exception as e:
                            st.error(f"Gagal mengambil tren: {e}")
            
            if "market_trends" in st.session_state:
                st.markdown("<br>", unsafe_allow_html=True)
                for i, trend in enumerate(st.session_state.market_trends):
                    st.markdown(
                        f"""
                        <div style="background:#FFFFFF; border:2px solid #1A191E; border-radius:10px; padding:1rem; margin-bottom:0.8rem; box-shadow:2px 2px 0px rgba(26,25,30,0.1);">
                          <b style="font-size:1rem; color:#D9381E;">🔥 {trend.get('category', 'Kategori Tren')}</b>
                          <p style="font-size:0.88rem; color:#4A4853; margin:0.3rem 0; line-height:1.4;"><i>"{trend.get('reason', '')}"</i></p>
                          <div style="background:#F8F6F0; border-left:3px solid #1A191E; padding:0.5rem; margin-top:0.5rem; font-size:0.9rem; font-weight:600;">
                            💡 {trend.get('base_idea', '')}
                          </div>
                        </div>
                        """, unsafe_allow_html=True
                    )
                    if st.button(f"Gunakan Ide #{i+1}", key=f"use_trend_{i}"):
                        st.session_state.tab1_base_idea = trend.get('base_idea', '')
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
        selected_style = st.selectbox(
            "Gaya Visual",
            options=list(config.STYLES.keys()),
            index=0,
            key="tab1_style",
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
        btn_magic = st.button(
            "Generate Magic Prompt Sekarang",
            type="primary",
            use_container_width=True,
            disabled=not api_key,
        )
        if not api_key:
            st.info("Masukkan Google Gemini API Key gratis di sidebar kiri terlebih dahulu.")

        if btn_magic:
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
                        st.toast("Magic Prompt berhasil dibuat!", icon="✨")
                    except Exception as e:
                        st.error(f"Gagal membuat prompt: {e}")

    with col_right:
        st.markdown(
            """
            <h3 style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:800; margin:0 0 0.8rem; color:#1A191E;">
              Output Prompt Siap Salin
            </h3>
            """,
            unsafe_allow_html=True,
        )

        prompt_val = st.session_state.enhanced_prompt
        if prompt_val:
            if isinstance(prompt_val, list):
                st.markdown("**Pilih salah satu (atau salin semuanya):**")
                for idx, p in enumerate(prompt_val):
                    st.caption(f"Alternatif #{idx + 1}")
                    st.code(p, language=None, wrap_lines=True)
            else:
                st.code(prompt_val, language=None, wrap_lines=True)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.link_button(
                    "Buka gemini.google.com ↗",
                    "https://gemini.google.com",
                    use_container_width=True,
                    type="primary",
                )
            with c_btn2:
                if st.button("Bersihkan Prompt", use_container_width=True):
                    st.session_state.enhanced_prompt = ""
                    st.rerun()

            with st.expander("Panduan Alur Kerja di Gemini Web:", expanded=True):
                st.markdown(
                    """
                    1. **Salin Prompt**: Klik ikon salin di sudut kanan atas kotak prompt di atas.
                    2. **Tempel di Gemini Web**: Buka `gemini.google.com` dan tempelkan prompt tersebut.
                    3. **Download Gambar**: Klik tombol unduh (⬇️) pada gambar hasil generate dari web Gemini.
                    4. **Buka Tab 2**: Unggah gambar yang telah Anda unduh ke **Tab 2** untuk inspeksi visual Gemini Vision dan pembuatan 50 keywords SEO akurat. Anda dapat melakukan upscale resolusi secara mandiri jika diperlukan.
                    """
                )
        else:
            st.markdown(
                """
                <div style="background:#FFFFFF; border:2px dashed #1A191E; border-radius:12px; padding:2rem 1.5rem; text-align:center; box-shadow:3px 3px 0px rgba(26,25,30,0.06);">
                  <b style="font-size:1.05rem; display:block; margin-bottom:0.5rem; color:#1A191E;">Prompt Anda Akan Muncul Di Sini</b>
                  <p style="color:#4A4853; font-size:0.92rem; margin:0; font-weight:600;">
                    Tuliskan konsep dasar di panel kiri, pilih gaya & lensa, lalu klik <b>Generate Magic Prompt Sekarang</b>.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================================== #
# TAB 2: INSPEKSI GAMBAR & METADATA (GEMINI VISION)
# =========================================================================== #
with tab2:
    st.markdown(
        """
        <div style="margin-bottom: 1.2rem;">
          <h2 style="font-family:'Space Grotesk',sans-serif; font-size:1.6rem; font-weight:800; margin:0 0 0.3rem;">
            Inspeksi Visual & Paket Microstock
          </h2>
          <p style="color:#4A4853; font-size:0.95rem; margin:0; font-weight:600;">
            Unggah gambar hasil generate dari Gemini Web. Gemini Vision akan menganalisis konten visual nyata, mempertahankan resolusi asli, serta menyusun 50 keywords anti-reject dan metadata lengkap untuk Adobe Stock & Shutterstock.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Pilih atau seret gambar Anda (JPG, PNG, WebP):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Anda dapat mengunggah 1 hingga 10+ file gambar sekaligus.",
    )

    image_entries = []  # list of (filename, raw_bytes, mime)
    if uploaded_files:
        for uf in uploaded_files:
            image_entries.append((uf.name, uf.getvalue(), uf.type or "image/jpeg"))

    if image_entries:
        st.markdown(
            f"""
            <div style="display:inline-block; background:#E7F5FF; border:1.5px solid #1A191E; border-radius:8px; padding:0.4rem 0.9rem; margin-bottom:0.8rem; box-shadow:2px 2px 0px #1A191E;">
              <span style="font-weight:700; color:#1864AB; font-size:0.92rem;">Terdeteksi {len(image_entries)} gambar siap dianalisis</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Pengaturan Upscaler & Metadata**")
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            do_upscale = st.checkbox("Lakukan Upscale Gambar (Otomatis Lokal)", value=False, help="Menggunakan mesin Upscayl NCNN CLI lokal.")
        with col_up2:
            upscale_factor = st.selectbox("Tingkat Perbesaran (Scale)", [2, 3, 4], index=2, disabled=not do_upscale)

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
                    md = await generate_metadata_from_vision_async(
                        client=client,
                        image_bytes=raw_bytes,
                        mime_type=mime,
                        label=f"Gambar #{idx+1}",
                    )

                    target_bytes = raw_bytes
                    if do_upscale:
                        progress_bar.progress(idx / len(image_entries), text=f"Memperbesar (Upscale {upscale_factor}x) #{idx+1} dari {len(image_entries)}: {filename}...")
                        import tempfile
                        from microstock.upscaler import run_upscale
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as in_f:
                            in_f.write(raw_bytes)
                            in_path = in_f.name
                        out_path = in_path.replace(".jpg", "_up.jpg")
                        success = await asyncio.to_thread(run_upscale, in_path, out_path, upscale_factor)
                        if success:
                            with open(out_path, "rb") as out_f:
                                target_bytes = out_f.read()
                            try: os.remove(out_path)
                            except: pass
                        else:
                            st.toast(f"Upscale gagal untuk {filename}, menggunakan resolusi asli.", icon="⚠️")
                        try: os.remove(in_path)
                        except: pass

                    progress_bar.progress(idx / len(image_entries), text=f"Menyiapkan resolusi & preview #{idx+1}...")
                    # Finalize image & thumbnail (Preserve original resolution, 300 DPI)
                    exp_bytes, prev_bytes, f_mime, w, h = await asyncio.to_thread(
                        finalize_image, target_bytes, "JPEG", False
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
            st.info(f"File dan CSV otomatis tersimpan di folder lokal komputer Anda:\n`{local_export_dir}`")

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
