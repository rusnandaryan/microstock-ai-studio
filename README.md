# Microstock AI Studio Pro

Workstation desktop lokal (*local-first*) bertenaga AI untuk kreator microstock profesional (**Adobe Stock**, **Shutterstock**, dan **Freepik**). Ditenagai oleh **Google Gemini AI**, **Real-ESRGAN Vulkan GPU**, **SQLite WAL Database**, injeksi metadata **Lossless Adobe XMP/IPTC**, proteksi akun **64-bit dHash (Perceptual Hash)**, dan **Direct SFTP/FTP Contributor Dispatcher**.

---

## 🏗️ Alur Kerja & Arsitektur Workstation (4 Modul Inti)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MICROSTOCK AI STUDIO PRO                                  │
├────────────────────┬─────────────────────────────┬─────────────────────┬────────────────────┤
│  Tab 1:            │  Tab 2:                     │  Tab 3:             │  Tab 4:            │
│  Prompt Generator  │  Inspeksi Visual & Metadata │  Reverse Prompt     │  Distribusi & DB   │
│  (Text to Prompt)  │  (Vision, XMP & pHash)      │  (Image to Prompt)  │  (SFTP, FTP & WAL) │
└────────────────────┴─────────────────────────────┴─────────────────────┴────────────────────┘
```

---

### Tab 1: Studio Pembuat Prompt (Text to Prompt)
Ubah ide singkat menjadi **5 variasi prompt bahasa Inggris komersial** yang telah disterilkan dari risiko penolakan (*rejection-free*).
- **Riset Tren Pasar Terkini:** Memindai 10 peluang momen komersial teratas Adobe Stock secara dinamis lengkap dengan tombol *1-Click Apply*.
- **Katalog 5 Kategori Gaya Visual:** Fotografi (Commercial, Documentary, Macro, Faceless), Ilustrasi & Lukisan (Watercolor, Oil, Sketch), Animasi & Kartun (Kawaii, Anime, 3D CGI Pixar-like), 3D & Render (Diorama, Isometric, Claymation, Octane), serta Desain (Sticker Sheet, App Icons, Flat Vector).
- **Framing Komersial:** *Negative Space for Copy* (30–40% area bersih), *Knolling Grid/Die-Cut*, dan *Full Frame*.
- **Lensa & Pencahayaan:** Pilihan lensa 85mm prime, 100mm macro, 24mm wide, top-down flat lay, studio softbox, dan golden hour.

---

### Tab 2: Pemeriksa Gambar, Upscale NCNN & Metadata XMP/IPTC (Gemini Vision)
- **Kernel Event Folder Watcher (0% CPU Idle):** Memantau folder `Downloads` Mac/PC secara event-driven (FSEvents/watchdog) tanpa lonjakan CPU. Mendeteksi file gambar baru secara instan dan mengabaikan file download sementara (`.crdownload`, `.part`).
- **Aturan Upscale Otomatis:**
  - *Minimal 4 Megapiksel (Otomatis & Wajib):* Output resolusi dihitung otomatis $\ge 4$ MP sesuai syarat mutlak Adobe Stock & Shutterstock.
  - *Minimal 4 Megabyte (Opsional):* Padding lossless agar ukuran fisik file $\ge 4$ MB untuk Freepik / Vecteezy.
  - *Akselerasi Vulkan GPU Lokal:* Real-ESRGAN NCNN memproses gambar secara lokal tanpa koneksi internet.
- **Injeksi Lossless Adobe XMP/IPTC (APP1):** Metadata *Title*, *Description*, *50 Keywords*, dan *Category* disuntikkan langsung ke segmen APP1 stream JPEG tanpa decode-reencode pixel. Saat diunggah ke Adobe Stock atau Shutterstock, metadata otomatis terbaca tanpa perlu upload CSV manual.
- **Visual Duplicate Guard (64-bit dHash):** Menghitung Difference Hash gambar dan mengukur jarak Hamming dengan aset sebelumnya. Memberikan peringatan dini (*Risiko Duplikat: HIGH/MEDIUM*) guna melindungi akun kontributor dari sanksi spam.
- **Klasifikasi Otomatis 21 Kategori Resmi Adobe Stock:** Memetakan aset secara deterministik ke ID 1–21 (Animals, Architecture, Business, Food, Lifestyle, Technology, dll.) dan kategori Shutterstock.

---

### Tab 3: Reverse Prompt Studio (Image to Prompt)
- **Bedah Visual Cerdas:** Gemini Vision membedah objek, pencahayaan, sudut kamera, tekstur, dan rasio aspek asli (16:9, 1:1, 9:16, 4:3, dsb.).
- **Auto-Save Lokal (`*.txt`):** Prompt komersial tersimpan rapi di `exports/prompts/prompt_[nama_file].txt` sehingga tidak hilang saat halaman di-refresh.
- **Zero Memory Clutter:** File referensi hanya dibaca sementara di memori tanpa membebani harddisk.

---

### Tab 4: Distribusi Contributor & Database Studio
- **Master Database SQLite WAL (`exports/data/studio.db`):** Menyimpan seluruh katalog aset lokal, resolusi, pHash, metadata SEO, dan riwayat kurasi agensi (Zero-Cloud lock-in, data 100% milik Anda).
- **Direct Contributor Delivery Hub (FTP / FTPS / SFTP):**
  - **Adobe Stock:** SFTP resmi (`sftp.contributor.adobestock.com:22`)
  - **Shutterstock:** FTPS aman (`ftps.shutterstock.com:21`)
  - **Freepik:** FTP resmi (`ftp.freepik.com:21`)
  - Fitur *Tes Koneksi Server* langsung dari antarmuka pengguna.
- **Enterprise Credential Security:** Kata sandi agensi dan API Key dikelola melalui **macOS Keychain** (`/usr/bin/security`) dengan fallback otomatis ke **Machine-Keyed Encrypted Local Vault** (PBKDF2 HMAC SHA-256 + permission `0600`). *Nol kata sandi plaintext di basis data atau log*.

---

## 🛡️ 7 Aturan Kepatuhan Mutlak (Universal Compliance Rules)

Semua prompt dan metadata yang dihasilkan secara otomatis memenuhi standar kurasi microstock internasional:

1. **Zero Female Characters (Universal Strict Prohibition):** 100% bebas figur wanita/feminin (manusia, kartun, robot). Mengutamakan objek mati (*inanimate objects*), arsitektur, makanan, alam, dan peralatan.
2. **Zero Text & Typography:** Bebas huruf, angka, tipografi, logo, watermark, dan kaligrafi.
3. **Mandatory Faceless Creatures:** Semua makhluk hidup dibuat 100% tanpa fitur wajah (*shot from behind*, siluet, fokus tangan).
4. **Unbranded & Generic Props:** Properti kendaraan, gawai, dan elektronik bersih tanpa merek dagang.
5. **Commercial Composition:** Menyediakan *copy space* bersih atau susunan knolling simetris.
6. **Authentic Photographic Lighting:** Cahaya alami atau studio nyata tanpa efek plastik waxy (*anti-plastic sheen*).
7. **Physical Micro-Textures:** Tekstur material nyata (serat kayu, kain linen, pantulan kaca) dengan depth of field terkontrol.

---

## 💻 Panduan Antarmuka Terminal (CLI)

Selain antarmuka web Streamlit, aplikasi menyediakan CLI lengkap untuk integrasi skrip dan otomatisasi:

```bash
# 1. Menampilkan ringkasan status master database SQLite
python cli.py db

# 2. Membuat prompt komersial dari ide teks
python cli.py prompt "cangkir kopi espresso di meja kayu minimalis" --style "Fotografi (Photorealism)"

# 3. Memproses folder gambar: Vision SEO + Injeksi XMP + dHash + Auto-Save DB
python cli.py process ~/Downloads --upscale

# 4. Reverse prompt dari file gambar referensi
python cli.py reverse path/ke/gambar.jpg

# 5. Pindai tren komersial teratas
python cli.py trends

# 6. Unggah langsung ke endpoint kontributor agensi via SFTP/FTP
python cli.py upload adobe_stock exports/batch_20261110_103000/
python cli.py upload shutterstock exports/batch_20261110_103000/
python cli.py upload freepik exports/batch_20261110_103000/

# 7. Menjalankan GUI Streamlit Pro
python cli.py gui
```

---

## ⚙️ Pemasangan & Persyaratan Sistem

### Prasyarat
- Komputer dengan **Python 3.9** atau lebih baru (macOS / Linux / Windows).
- Kunci API gratis (**Gemini API Key**) dari [Google AI Studio](https://aistudio.google.com/).

### Langkah Instalasi
```bash
# 1. Masuk ke direktori proyek
cd microstock-ai-studio

# 2. Buat dan aktifkan virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# 3. Pasang dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi
streamlit run app.py
```
Aplikasi akan terbuka otomatis di peramban Anda pada alamat `http://localhost:8501`.

---

## 📂 Struktur Penyimpanan Lokal

- `exports/data/studio.db` : Basis data master SQLite WAL (aset, pHash, log pengiriman).
- `exports/data/.vault.enc` : Brankas kredensial terenkripsi mesin (izin berkas `0600`).
- `exports/prompts/` : Arsip teks prompt hasil bedah gambar reverse prompt (`*.txt`).
- `exports/batch_[timestamp]/` : Folder paket hasil ekspor gambar ber-XMP dan file `metadata.csv`.
- `.env` : Tempat penyimpanan lokal kunci API Gemini Anda.
