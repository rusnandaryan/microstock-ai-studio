# Visual-First Media Studio Redesign Specification

Tanggal: 2026-10-29  
Status: Draft (Pending User Approval)  
Pilihan Pendekatan: **Arah 3: Visual-First Media Studio (Gaya Behance Pro / Figma Studio)**

---

## 1. Intent & The Why

Aplikasi **Microstock AI Studio** adalah workstation khusus untuk kreator dan kontributor microstock komersial (Adobe Stock, Shutterstock, Freepik, Vecteezy). Pengguna membutuhkan antarmuka yang tidak hanya fungsional, tetapi juga memiliki estetika visual kelas atas, elegan, bebas distorsi, dan memberikan pengalaman studio media premium.

Desain sebelumnya terasa teknis dan konvensional. Desain baru ini dibangun **dari nol (ground-up)** dengan filosofi **Visual-First Media Studio**: menonjolkan visual aset, kontrol pemotretan sinematik, kartu kanvas bertekstur halus, tipografi geometris modern, dan hierarki informasi yang sangat nyaman dipandang dalam sesi kerja panjang di tema gelap.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **100% Functional Preservation:** Menjamin seluruh fungsi backend, state management, dan pemrosesan async berjalan normal tanpa error atau regresi.
  - Tab 1: Generator prompt dengan 5 arketipe visual bebas duplikasi.
  - Tab 2: Auto-sync folder downloads, inspeksi Gemini Vision (50 tags, judul komersial, kategori SS), NCNN 4x AI upscaler (Smart Microstock ~8 MP & Ultra 4x, Freepik 4MB enforcement), ekspor master CSV & ZIP.
  - Tab 3: Reverse prompt (image-to-prompt) dan transfer 1-klik ke Tab 1.
- **Visual-First Media Studio Aesthetic:** Mengadopsi palet OLED dark studio (`#06080D` canvas, `#0B0F19` cards), tipografi modern (*Space Grotesk* + *Plus Jakarta Sans* + *JetBrains Mono*), dan kartu preview gambar yang sinematik.
- **Ergonomi & Aksesibilitas:** Kontras teks rasio tinggi (WCAG AAA untuk teks utama), target klik minimal 44px, status feedback yang jelas.

### Non-Goals
- Tidak mengubah logika internal model AI atau algoritma upscaler (NCNN CLI, fallback LLM, tokenizer, Pillow padding).
- Tidak menambahkan dependensi pihak ketiga baru (tetap memanfaatkan Streamlit + standard library Python).

### Anti-Goals
- Tidak ada elemen dekoratif AI slop generik (bebas sparkle `✨`, bebas banner pembatas berulang, bebas frasa marketing klise).
- Tidak menggunakan tema terang (light mode ditiadakan sepenuhnya sesuai instruksi pengguna).

---

## 3. Approaches Considered & Trade-offs

Tiga pendekatan visual dipertimbangkan:

1. **Arah 1: Minimalist Precision Workstation (Linear / Raycast Style)**
   - *Kelebihan:* Sangat hemat ruang, berorientasi teks dan shortcut.
   - *Kekurangan:* Kurang menonjolkan preview gambar dan visual feedback yang krusial bagi fotografer stok.
2. **Arah 2: Creative DAW / Production Rack (DaVinci Resolve / Ableton Style)**
   - *Kelebihan:* Menonjolkan meteran teknis dan indikator hardware.
   - *Kekurangan:* Terlalu padat dan teknis, bisa melelahkan untuk kontributor yang fokus pada estetika visual gambar.
3. **Arah 3: Visual-First Media Studio (Behance Pro / Figma Studio Style) — DIPILIH**
   - *Kelebihan:* Keseimbangan sempurna antara estetika media studio dan fungsionalitas komersial. Latar belakang OLED pitch-dark dengan aksen cyan/emerald/violet, kartu preview gambar berukuran lapang, chip arketipe visual yang menarik, dan layout dua kolom yang ergonomis.
   - *Trade-off:* Membutuhkan penyesuaian CSS Streamlit yang presisi agar kartu kanvas dan grid hasil inspeksi tetap rapi di layar laptop maupun monitor ultrawide.

---

## 4. Design System & Component Architecture

### 4.1 Design Tokens (OLED Studio Palette)
```css
:root {
  color-scheme: dark !important;
  --bg-page: #06080D !important;        /* Pure deep obsidian studio background */
  --bg-card: #0B0F19 !important;        /* Elevated canvas card */
  --bg-sidebar: #05070B !important;     /* Deep sidebar container */
  --bg-input: #0E1424 !important;       /* Recessed input background */
  --bg-elevated: #131A2E !important;    /* Hover & popover elevated */
  --border-color: rgba(255, 255, 255, 0.08) !important;
  --border-subtle: rgba(255, 255, 255, 0.04) !important;
  --border-focus: #3B82F6 !important;
  --text-primary: #F8FAFC !important;
  --text-secondary: #94A3B8 !important;
  --text-muted: #64748B !important;
  --accent-blue: #2563EB !important;
  --accent-blue-hover: #1D4ED8 !important;
  --accent-emerald: #10B981 !important; /* Hardware status & success */
  --accent-violet: #8B5CF6 !important;  /* Gemini Vision AI */
  --accent-amber: #F59E0B !important;   /* SEO Keywords & Tags */
  --radius-sm: 6px !important;
  --radius-md: 10px !important;
  --radius-lg: 16px !important;
}
```

### 4.2 Typography
- **Headings & Display:** `'Space Grotesk', -apple-system, sans-serif` (weight: 700/800, letter-spacing: -0.02em).
- **Body & UI Text:** `'Plus Jakarta Sans', -apple-system, sans-serif` (weight: 500/600, line-height: 1.5).
- **Code & Metadata:** `'JetBrains Mono', monospace` (weight: 500).

### 4.3 Component Specifications

#### A. Header Studio
- Header minimalis sinematik: Logo/Title "Microstock AI Studio", indikator hardware live ("Vulkan NCNN GPU Active"), dan sub-header penjelasan komersial yang ringkas.

#### B. Tab 1: Commercial Prompt Studio (2-Column Canvas)
- **Panel Kiri (Formulasi):**
  - Textarea konsep dasar yang lapang dengan placeholder kontekstual.
  - Selektor kategori & preset gaya fotografi dengan visual badge.
  - Kontrol pemotretan: Lighting, Camera/Lens, Komposisi Framing, dan Rasio Aspek (16:9, 1:1, 9:16, 4:3, 3:4).
  - Tombol aksi utama: `Generate Prompt Komersial` berukuran penuh dengan efek hover studio.
- **Panel Kanan (Output Arketipe):**
  - Header dengan status compliance (Faceless, Copy space, Zero trademark).
  - 5 Kartu Arketipe Visual terpisah:
    1. `🌐 Wide Context & Environment`
    2. `🔍 Macro & Material Detail`
    3. `⚡ In-Use Action & Interaction`
    4. `📐 Clean Copy Space / Ad Layout`
    5. `🧩 Flat Lay Knolling / Alternative Angle`
  - Setiap kartu memiliki badge visual berwarna, box prompt dengan syntax styling gelap, dan tombol cepat ke Gemini Web.

#### C. Tab 2: Visual Inspection & Microstock Pack (Gemini Vision)
- **Section 1: Ingestion Hub**
  - Modul Auto-Sync Folder Download: Kartu pemantauan folder dengan tombol "Pindai Sekarang" dan badge total antrean.
  - Modul Drag-and-Drop: Dropzone manual bergaris putus-putus halus untuk berkas lokal.
- **Section 2: Microstock Standards & Upscale Engine**
  - Checkbox aktivasi NCNN AI Upscaler.
  - Segmented radio: `Smart Microstock (~8 MP · Standar 4K)` vs `Ultra 4x (~16-25 MP · Resolusi Penuh)`.
  - Checkbox penegakan standar Freepik/Vecteezy: `Wajibkan ukuran file fisik minimal 4 MB`.
  - Tombol eksekusi: `Mulai Analisis Visual & Susun Paket Microstock`.
- **Section 3: Results & Export Hub**
  - Download Hub: Tombol `Download Master ZIP` dan `Download CSV Metadata`.
  - Ringkasan tabel dataframe metadata.
  - Grid kartu inspeksi visual: Thumbnail gambar tajam di kiri, rincian teknis (dimensi, megapiksel, rasio), judul komersial, kategori Shutterstock, dan 50 tag SEO dalam bentuk chip interaktif.

#### D. Tab 3: Reverse Prompt Studio
- File uploader gambar referensi.
- Grid hasil dekonstruksi: Gambar referensi berdampingan dengan prompt rekonstruksi komersial, tombol copy, link Gemini Web, dan tombol transfer langsung `📥 Kirim ke Tab 1`.

#### E. Sidebar Studio
- Input API key yang elegan dengan status tersimpan.
- Indikator engine: Model teks aktif, model vision aktif, hardware upscaler detection.
- Quick microstock compliance cheat sheet (Adobe Stock & Shutterstock specs).

---

## 5. Verification Plan

1. **Syntax & Unit Tests:** Seluruh 13 unit tests (`tests/`) harus lulus 100%.
2. **Import & Module Integrity:** `python3 -c "import app"` sukses tanpa warning/error.
3. **Cross-Feature Walkthrough:**
   - Formulir prompt di Tab 1 dapat menghasilkan 5 prompt dengan arketipe berbeda.
   - Tab 2 mampu membaca antrean Auto-Sync atau manual upload, menjalankan NCNN upscaler, dan menghasilkan ZIP/CSV.
   - Tab 3 mampu membaca gambar dan mengirim prompt ke Tab 1.
