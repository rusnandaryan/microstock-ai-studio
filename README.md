# Microstock AI Studio Pro

Microstock AI Studio Pro adalah aplikasi lokal untuk membantu alur kerja kontributor microstock: meracik prompt komersial, menganalisis gambar dengan Gemini Vision, menyusun metadata SEO, melakukan upscale, menyimpan riwayat aset, dan mengirim file ke agensi via FTP/SFTP.

Antarmuka utama tersedia dalam dua mode:
- **Web Studio (Streamlit):** `streamlit run app.py` atau `python cli.py gui`
- **Desktop Native (SPA lokal, ringan):** `python cli.py desktop`

---

## Fitur Utama (sesuai implementasi saat ini)

- **Prompt Studio (32 gaya visual):** Racik 5 variasi prompt komersial berurutan (*seri 5 sudut*) dari satu konsep, atau buat formula *image-to-image restyle* berdasarkan gaya yang dipilih. Hasil dapat langsung dibuka di Gemini Web.
- **Vision & Auto-Sync:** Pindai folder unduhan (default folder Downloads), impor gambar terbaru berdasarkan rentang waktu, atau unggah manual. Proses batch berjalan di latar belakang untuk analisis visual, pembuatan judul/deskripsi/keyword, dan persiapan paket ekspor.
- **Metadata & ekspor:** Hasil batch menghasilkan metadata (termasuk CSV) dan paket ZIP di folder `exports/batch_<timestamp>/`. Aplikasi menanamkan metadata ke file JPEG hasil proses (IPTC/XMP) agar siap unggah ke agensi.
- **Upscale & standar file:** Opsi upscale standar (target aman ≥ 4 MP) dan opsi paksaan ukuran file minimum 4 MB (untuk kebutuhan agensi seperti Freepik/Vecteezy). Mode pemrosesan CLI juga mendukung target cerdas (*Smart Microstock*, ~8.3 MP).
- **Reverse Prompt:** Ekstrak prompt komersial dari gambar referensi (Vision) dan simpan hasilnya ke `exports/prompts/`.
- **Database Aset Lokal (SQLite WAL):** Menyimpan riwayat aset, metadata, pHash, status injeksi metadata, serta log pengiriman. Tersedia ringkasan metrik, pembersihan entri file hilang, dan pengosongan database dari UI.
- **Distribusi ke Agensi (FTP/FTPS/SFTP):** Simpan kredensial per agensi (Adobe Stock, Shutterstock, Freepik), uji koneksi server, dan unggah aset. Tersedia juga perintah CLI untuk upload batch.
- **Penyimpanan kredensial:**
  - **Gemini API Key:** disimpan lokal di file `.env` pada root proyek (atau dapat dibaca dari environment/secrets) melalui menu **Pengaturan Studio** di sidebar.
  - **Kredensial agensi (username/password):** disimpan aman melalui modul keamanan aplikasi (prioritas **macOS Keychain** bila tersedia, dengan fallback **Encrypted Local Vault** di `exports/data/`). Database tidak menyimpan password plaintext.

---

## Prasyarat

- **Python** 3.10+ (disarankan 3.11/3.12)
- **Google Gemini API Key** (dari [Google AI Studio](https://aistudio.google.com/))
- Koneksi internet untuk pemanggilan Gemini API, pengujian koneksi agensi, dan upload
- (Opsional) Dependensi sistem untuk fitur upscale/binary tertentu sesuai environment Anda (`upscayl_bin/` tersedia di proyek)

---

## Instalasi

### macOS

```bash
# Dari folder proyek
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows

```bat
:: Dari folder proyek
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Pastikan saat instalasi Python di Windows opsi **"Add python.exe to PATH"** dicentang.

---

## Menjalankan Aplikasi

### 1. Web Studio (Streamlit)

```bash
# Pastikan virtual environment aktif
streamlit run app.py
# atau
python cli.py gui
```

Aplikasi akan terbuka di browser (default `http://localhost:8501`).

### 2. Desktop Native (ringan, jendela app lokal)

```bash
python cli.py desktop
# opsi port:
python cli.py desktop --port 8505
```

Server lokal akan berjalan (default `http://127.0.0.1:8505`) dan aplikasi dibuka sebagai jendela app/browser.

---

## Pengaturan Aplikasi (UI)

### Sidebar: Pengaturan Studio
- **Gemini API Key**
  - Jika belum tersimpan: tempel API key lalu klik **Simpan di Perangkat Ini**.
  - Jika sudah tersimpan: status "Siap" ditampilkan (key dimasker) dan tersedia tombol **Hapus API Key**.
- **Utilitas Sistem:** **Bersihkan Cache** untuk membersihkan cache Streamlit.

### Workspace Utama
- **Prompt Studio (kolom kiri)**
  - Input **Konsep Subjek**.
  - Pilih **Style Visual (32 pilihan)**.
  - Aksi: **Racik 5 Sudut Seri** (butuh API key) atau **Format Foto Restyle**.
  - Hasil: daftar prompt seri/restyle dengan opsi salin (code block) dan tombol **Buka Gemini Web**.
- **Vision & Auto-Sync (kolom kanan)**
  - **Folder Unduhan** + **Rentang** waktu scan, tombol **Pindai Folder**, deteksi file yang masih diunduh browser.
  - Pilih/impor gambar hasil scan atau **unggah manual** (JPG/PNG/WEBP).
  - Opsi proses batch:
    - **Upscale resolusi standar (≥ 4 MP)**
    - **Wajib file fisik ≥ 4 MB (Freepik/Vecteezy)** (muncul saat upscale aktif)
  - Tombol **Analisis … Gambar & Susun Metadata** menjalankan job di latar belakang (progress & status ditampilkan).
  - Setelah selesai: **Paket Ekspor Siap Unduh** (ZIP/CSV) dan tinjauan grid hasil.

### Panel Bawah (collapsible)
- **Reverse Prompt (Ekstrak Prompt dari Gambar Referensi)**
  - Unggah satu/lebih gambar referensi, klik **Analisis … Gambar & Buat Prompt**.
  - Hasil prompt dapat dikirim kembali ke Prompt Studio.
- **Database Aset & Distribusi Kontributor (FTP / SFTP)**
  - Ringkasan metrik aset & pengiriman, tabel aset terbaru, aksi **Bersihkan File Hilang** / **Kosongkan Database**.
  - **Pengaturan Agensi Kontributor:** pilih agensi, atur **Server Host/Port/Username/Password**, lalu:
    - **Simpan Kredensial**
    - **Tes Koneksi**
  - Tersedia tombol **Buka Folder Exports**.

> Catatan: struktur UI saat ini menggunakan layout dua kolom + panel bawah (bukan tab 1–4 terpisah seperti versi dokumentasi lama).

---

## Perintah CLI

Semua perintah dijalankan dari root proyek (dengan virtual environment aktif):

```bash
# Bantuan umum
python cli.py --help

# Buka Web Studio (Streamlit)
python cli.py gui

# Buka Desktop Native (SPA lokal)
python cli.py desktop
python cli.py desktop --port 8505

# Racik prompt komersial
python cli.py prompt "cangkir teh herbal hangat di meja kayu"
python cli.py prompt "flat lay perlengkapan baking minimalis" --style "Foto Studio" --series
python cli.py prompt "potret produk skincare" --style "Foto Studio" --restyle

# Analisis & proses batch gambar (metadata, upscale opsional, ekspor ZIP/CSV)
python cli.py process ~/Downloads
python cli.py process ~/Downloads --upscale
python cli.py process ~/Downloads --upscale --freepik
python cli.py process ~/Downloads --limit 20

# Reverse prompt dari gambar
python cli.py reverse path/ke/gambar.jpg

# Tren / momen mendatang untuk ide microstock
python cli.py trends

# Ringkasan database aset lokal
python cli.py db
python cli.py db --limit 50

# Upload batch ke agensi (adobe_stock | shutterstock | freepik)
python cli.py upload adobe_stock exports/batch_YYYYMMDD-HHMMSS/
python cli.py upload shutterstock path/ke/folder-atau-file.jpg
```

### Opsi penting `process`
- `source` (opsional): path folder/file; default ke folder Downloads (sesuai deteksi sistem)
- `--limit`: batas jumlah gambar yang dipindai (default 50)
- `--upscale`: aktifkan AI upscale jika resolusi di bawah ambang aman
- `--smart`: batasi target resolusi cerdas ~8.3 MP (default aktif)
- `--freepik`: paksa ukuran file minimal 4 MB

---

## Struktur Folder (ringkas)

- `app.py` — entry point Web Studio (Streamlit)
- `cli.py` — antarmuka command line
- `microstock/` — modul inti (config, prompt, vision/metadata, export, queue, db, security, distributor, server, UI, dll.)
- `exports/` — hasil batch, metadata CSV/ZIP, database lokal (`exports/data/studio.db`), dan file pendukung
- `tests/` — pengujian
- `.streamlit/` — konfigurasi tema/server Streamlit
- `desktop/` — komponen pendukung mode desktop

---

## Catatan Keamanan & Data

- Aplikasi berjalan **local-first**: file, database, dan konfigurasi lokal disimpan di komputer Anda.
- **API Key Gemini** disimpan lokal (file `.env` di root proyek). Lindungi perangkat dan file konfigurasi Anda.
- **Kredensial agensi** disimpan melalui mekanisme aman aplikasi (Keychain macOS bila tersedia, atau vault terenkripsi lokal sebagai fallback).
- Data dikirim keluar hanya saat diperlukan (mis. panggilan Gemini API, uji koneksi/upload ke server agensi yang Anda pilih).

---

## FAQ Singkat

**Di mana hasil proses batch disimpan?**  
Di folder `exports/batch_<timestamp>/` (berisi file hasil, `metadata.csv`, dan paket ZIP).

**Apakah metadata perlu CSV terpisah saat upload?**  
File JPEG hasil proses sudah disisipi metadata (IPTC/XMP). Beberapa alur agensi tetap dapat memanfaatkan CSV sesuai kebijakan masing-masing platform.

**Kenapa analisis batch tidak langsung selesai?**  
Pemrosesan berjalan sebagai job latar belakang agar UI tetap responsif; pantau status/progress pada panel Vision & Auto-Sync.

**Kredensial agensi tersimpan di mana?**  
Disimpan melalui modul keamanan aplikasi (Keychain/vault terenkripsi) dan direferensikan oleh database lokal; password tidak disimpan plaintext di tabel.

---

*Dokumentasi ini disesuaikan dengan struktur UI dan pengaturan aplikasi versi saat ini.*
