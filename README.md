# 📸 Microstock AI Studio

Selamat datang di **Microstock AI Studio**!  
Aplikasi komprehensif ini dirancang khusus untuk mempermudah dan mempercepat alur kerja (*workflow*) kontributor microstock (seperti **Adobe Stock** dan **Shutterstock**). Dengan dukungan kecerdasan buatan **Google Gemini AI**, Anda dapat meriset tren, membuat prompt komersial berkualitas tinggi, memeriksa visual gambar secara otomatis, hingga menyusun metadata SEO 50 kata kunci bebas penolakan (*anti-rejection*).

---

## ✨ Fitur-Fitur Utama & Alur Kerja

Aplikasi ini dibagi menjadi 3 modul kerja utama yang rapi dan terisolasi:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MICROSTOCK AI STUDIO                            │
├────────────────────┬─────────────────────────────┬─────────────────────┤
│  🎯 Tab 1:         │  🔍 Tab 2:                  │  🖼️ Tab 3:          │
│  Prompt Generator  │  Inspeksi Visual & Metadata │  Reverse Prompt     │
│  (Text to Prompt)  │  (Vision & Auto-Cleanup)    │  (Image to Prompt)  │
└────────────────────┴─────────────────────────────┴─────────────────────┘
```

---

### 🎯 Tab 1: Studio Pembuat Prompt (Text to Prompt)

Ubah ide singkat Anda menjadi **5 variasi prompt bahasa Inggris profesional** siap generate yang telah disterilkan sesuai standar ketat microstock internasional.

1. **Riset Tren Pasar Terkini (Dynamic Market Trends):**
   - Menampilkan analisa tren komersial teratas Adobe Stock berdasarkan tanggal/periode dinamis saat ini.
   - Menyajikan data lengkap: alasan permintaan pasar (*market reason*), status peluang (*High Demand / Low Competition, Evergreen, Rising Trend*), serta rekomendasi gaya visual dan rasio aspek.
   - **Fitur 1-Click Apply:** Cukup klik tombol pada kartu tren, semua parameter (ide dasar, kategori gaya, sub-gaya, dan rasio) langsung otomatis terisi ke form pembuatan prompt!

2. **Katalog Gaya Visual Terlengkap (Menu Bertingkat 5 Kategori):**
   - **📸 Fotografi (Photorealism):** Commercial Advertising, Dokumenter & Human Interest, Macro Photography, Portrait Faceless, Street Photography, Sinematik Film 35mm, Food Editorial, Arsitektur Minimalis.
   - **🎨 Ilustrasi & Seni Lukis:** Cat Air & Gouache, Cat Minyak Klasik, Sketsa Pensil & Arang, Impresionisme Bertekstur, Surealisme Modern, Seni Abstrak Kontemporer, Ilustrasi Stiker Die-Cut.
   - **🎬 Animasi & Kartun:** Pastel Kawaii Mascot Design, Anime Jepang Kontemporer, Manga Tinta Hitam Putih, Chibi & Karakter Imut, Kartun Klasik Retro, Komik Pop Art Halftone, Whimsical Studio Anime (Ghibli-inspired), 3D Animated Feature (Pixar-inspired).
   - **🧊 3D & Render:** 3D Miniature Diorama (Miniature World), 3D Commercial Studio Render, 3D Isometric Illustration, 3D Claymation (Tanah Liat Taktil), Low-Poly 3D Minimalist, Octane Render Photorealistic, 3D Glassmorphism & Akrilik Transparan.
   - **⚡ Desain & Digital Art:** Paket Stiker Die-Cut (Die-Cut Sticker Pack), Icon Desain Aplikasi & Web, Flat Design Vector Minimalist, Logo Monogram & Geometris, Cyberpunk & Futuristic Neon, Steampunk Vintage Mekanikal, Synthwave 80s, Pixel Art 16-bit, Digital Concept Art Sci-Fi/Fantasi.

3. **Pilihan Komposisi & Framing Fleksibel:**
   - **Negative Space for Copy / Headline:** Ruang kosong bersih 30%–40% untuk penempatan teks promosi/iklan.
   - **Grid Simetris Seimbang (Sticker Sheet / Icon Pack):** Penataan grid seimbang (*knolling layout*) dengan batas kontur potong putih (*die-cut cutline*) rapi di setiap elemen, tanpa ruang kosong sepihak.
   - **Full Frame / Edge-to-Edge (Tanpa Ruang Kosong):** Komposisi padat visual dari tepi ke tepi tanpa area kosong.
   - Serta opsi komposisi klasik: *Centered Hero Framing, Rule of Thirds (Left/Right),* dan *Balanced Symmetry*.

4. **Kondisi Pencahayaan & Lensa Kamera:**
   - Pencahayaan: *Studio Softbox, Natural Soft Daylight, Golden Hour, Dramatic Rim Lighting, High Key, Moody Chiaroscuro*.
   - Lensa: *85mm Prime (Bokeh Lembut), 35mm Street, 100mm Macro (Detail Ekstrem), 24mm Wide Angle, Top-Down Flat Lay (90°)*.

---

### 🔍 Tab 2: Pemeriksa Gambar, Upscale & SEO Metadata (Gemini Vision)

Pemeriksaan konten visual nyata dengan AI, upscale cerdas dengan standar microstock komersial, dan penyusunan metadata SEO 50 keywords.

1. **⚡ Auto-Sync dari Folder Download (Filter Waktu Sesi & Akumulasi Cerdas):**
   - Menghilangkan proses upload manual yang membosankan! Aplikasi memantau folder `Downloads` Mac Anda secara cerdas.
   - **Filter Jendela Waktu Sesi:** Pilihan rentang waktu (*15 Menit Terakhir / 30 Menit / 1 Jam / Hari Ini*) sehingga 30+ gambar yang baru diunduh langsung terjaring semua tanpa terganggu file lama.
   - **Akumulasi Cerdas Anti-Duplikat:** Jika Anda mengunduh bertahap, cukup klik *Pindai* lagi—gambar baru akan otomatis ditambahkan ke antrean tanpa menduplikasi file yang sudah ada.
   - **Deteksi Download Aktif:** Otomatis memperingatkan jika browser masih memproses file `.crdownload` yang belum tuntas.
   - Masih tersedia kotak unggah manual jika Anda ingin memasukkan gambar dari folder lain.

2. **🛡️ Aturan Upscale Cerdas (Standar Adobe Stock & Freepik Tanpa Perlu Pilih Skala Manual):**
   - **Minimal 4 Megapiksel (WAJIB & Otomatis):** Sistem menghitung skala yang tepat secara otomatis agar output selalu $\ge$ **4 MP** ($\ge 4.000.000$ piksel) sesuai syarat minimum Adobe Stock & Shutterstock tanpa perlu memilih angka 2x/3x/4x secara manual.
   - **Minimal 4 Megabyte (OPSIONAL):** Kotak centang khusus *"Wajibkan ukuran file fisik minimal 4 MB"*. Jika dicentang, file dipastikan berukuran $\ge 4$ MB di disk untuk memenuhi standar Freepik / Vecteezy. Jika tidak dicentang, kompresi normal dipertahankan agar hemat penyimpanan lokal Mac Anda.
   - **Auto-Upscaler NCNN Lokal:** Ditenagai mesin AI Real-ESRGAN Vulkan langsung di GPU komputer Anda tanpa koneksi internet.

3. **Hemat Memori Komputer (Smart Auto-Cleanup):**
   - **Tanpa Upscale (Default):** Jika Anda hanya butuh metadata CSV dan tidak mencentang perbesaran, file gambar mentah hanya diproses di RAM dan **tidak disimpan ke disk**, menjaga harddisk Anda tetap bersih dan lega.
   - **Dengan Upscale:** Gambar hasil upscale disimpan rapi bersama file `metadata.csv` di folder lokal `exports/batch_[timestamp]/`.

4. **Inspeksi Visual & Metadata 50 Keywords Anti-Reject:**
   - **Judul Komersial:** Ringkas, menjual, dan di bawah 100 karakter.
   - **Tepat 50 Keywords SEO:** Diurutkan dari yang paling relevan, bebas nama merek, bebas istilah terlarang (*anti-rejection*).
   - **Export Hub:** Ekspor langsung dalam bentuk file **CSV** siap impor atau paket arsip **ZIP**.

---

### 🖼️ Tab 3: Reverse Prompt Studio (Image to Prompt)

Punya gambar referensi yang menarik dan ingin membuat prompt serupa untuk di-generate ulang?

1. **Bedah Visual Otomatis (Gemini Vision):**
   - Membedah objek, pencahayaan, sudut pandang kamera, tekstur, dan mendeteksi rasio aspek asli gambar (16:9, 1:1, 9:16, 4:3, dsb.).
2. **Penyimpanan Lokal Otomatis (`*.txt`):**
   - Hasil prompt otomatis disimpan ke komputer Anda di folder `exports/prompts/prompt_[nama_file].txt`. Prompt tidak akan hilang meskipun browser di-refresh!
3. **Penyimpanan Bebas Beban (Zero Clutter):**
   - Gambar referensi yang Anda unggah hanya dibaca saat proses analisis dan tidak disimpan ke harddisk, menghemat ruang penyimpanan secara maksimal.

---

## 🛡️ 7 Aturan Kepatuhan Mutlak (Universal Compliance Rules)

Semua prompt yang dihasilkan oleh aplikasi ini (baik di Tab 1 maupun Tab 3) secara otomatis disterilkan dengan 7 aturan komersial universal:

1. **Zero Female Characters (Universal Strict Prohibition):**
   - Bersih tanpa pengecualian dari segala bentuk figur wanita/feminin (manusia, kartun, robot, maskot, maupun ilustrasi).
   - Setiap prompt wajib memuat klausul pengaman universal:  
     `"strictly no women, no female characters, no visible facial features, completely faceless and clean"`.
   - Mengutamakan benda mati (*inanimate objects*), arsitektur, makanan, alam, dan peralatan.

2. **Zero Text & Typography:**
   - 100% bebas dari huruf, angka, kata, tipografi, logo, tanda tangan, watermark, atau kaligrafi di seluruh permukaan objek.

3. **Mandatory Faceless Creatures & Characters (Zero Tolerance):**
   - Semua makhluk hidup (manusia, hewan) maupun karakter/maskot dibuat **100% tanpa wajah** (*zero visible eyes, zero facial features, zero expressions*).
   - Menggunakan teknik tampak belakang (*shot from behind*), siluet pekat, atau fokus pada tangan/benda.

4. **Unbranded & Generic Props:**
   - Seluruh gawai, teknologi, kendaraan, dan properti dibuat minimalis tanpa merek dagang terdaftar (*clean unbranded minimalist matte finish*).

5. **Commercial Composition:**
   - Mengatur penempatan *copy space* bersih atau susunan grid stiker yang simetris dan rapi.

6. **Authentic Photographic Lighting:**
   - Menggunakan pencahayaan natural atau studio nyata untuk menghindari kilau plastik waxy (*anti-plastic sheen*) khas AI murahan.

7. **Physical Micro-Textures & Controlled Depth of Field:**
   - Tekstur material nyata (serat kayu, kain linen, pantulan kaca bersih) dengan isolasi fokus lensa f/1.8 hingga f/2.8.

---

## 💻 Panduan Instalasi & Penggunaan

### 1. Prasyarat
- Komputer dengan **Python 3.9** ke atas.
- Kunci API gratis (**Gemini API Key**) dari [Google AI Studio](https://aistudio.google.com/).

### 2. Pemasangan

Buka **Terminal** (macOS/Linux) atau **Command Prompt / PowerShell** (Windows), lalu jalankan:

```bash
# 1. Masuk ke direktori proyek
cd /lokasi/folder/microstock-ai-studio

# 2. Buat virtual environment
python -m venv .venv

# 3. Aktifkan virtual environment
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. Instal dependensi yang dibutuhkan
pip install -r requirements.txt
```

### 3. Menjalankan Aplikasi

Jalankan perintah berikut:
```bash
streamlit run app.py
```

Aplikasi akan otomatis terbuka di browser Anda pada alamat `http://localhost:8501`.  
Masukkan **Gemini API Key** Anda pada kolom di sidebar kiri, dan simpan agar otomatis digunakan setiap kali membuka aplikasi.

---

## 📁 Struktur Penyimpanan Lokal

- `exports/prompts/` : Menyimpan file prompt hasil Reverse Prompt (format `*.txt`).
- `exports/batch_[timestamp]/` : Menyimpan metadata `metadata.csv` (serta gambar hasil *upscale* jika diaktifkan).
- `.env` : Menyimpan API Key Anda secara aman di komputer lokal (tidak diunggah ke internet).

---

*Dibuat untuk memaksimalkan produktivitas kontributor microstock profesional.*
