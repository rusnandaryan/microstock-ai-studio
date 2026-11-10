# 🚀 Microstock AI Studio Pro

Selamat datang di **Microstock AI Studio Pro**! 🎉  
Aplikasi ini dirancang khusus untuk mempermudah siapa saja—bahkan yang **belum pernah jualan foto stok atau belum pernah coding sekalipun**—untuk memproduksi, memeriksa, memberi kata kunci (keywords), dan menjual karya visual AI ke agensi internasional seperti **Adobe Stock**, **Shutterstock**, dan **Freepik**.

---

## ✨ Apa Saja yang Bisa Dilakukan Aplikasi Ini?

Bayangkan memiliki asisten profesional pribadi yang bekerja 24 jam di komputer Anda:
1. 💡 **Membuat Prompt Siap Pakai:** Cukup ketik ide dalam bahasa Indonesia, AI akan meraciknya menjadi 5 variasi prompt bahasa Inggris komersial yang bebas dari penolakan (*anti-rejection*).
2. 🏷️ **50 Keywords Otomatis & Cerdas:** AI menganalisis gambar Anda dan menyusun 50 kata kunci SEO terbaik, dengan 10 kata kunci teratas dioptimalkan khusus untuk mendatangkan pembeli (*Buyer Intent Ranking*).
3. ⚡ **Injeksi Metadata Langsung ke File JPEG (Fitur Juara!):** Judul, deskripsi, dan 50 kata kunci **ditanam langsung ke dalam file gambar**. Saat Anda upload ke Adobe Stock atau Shutterstock, Anda **TIDAK PERLU LAGI** upload file CSV terpisah atau mengetik keyword satu per satu!
4. 🔍 **Perbesar Gambar Otomatis (AI Upscale Vulkan GPU):** Memastikan resolusi gambar Anda selalu memenuhi syarat wajib agensi ($\ge 4$ Megapiksel dan $\ge 4$ MB) langsung menggunakan kartu grafis komputer tanpa internet.
5. 🛡️ **Proteksi Akun (Anti-Banned Visual Hash):** Mendeteksi apakah gambar Anda terlalu mirip dengan gambar sebelumnya agar akun kontributor Anda aman dari sanksi spam agensi.
6. 🚀 **Kirim Langsung ke Agensi (Direct SFTP/FTP):** Unggah puluhan gambar langsung ke server kontributor Adobe Stock, Shutterstock, dan Freepik dalam satu klik.
7. 🔒 **Keamanan Kelas Enterprise:** Kata sandi agensi dan API Key Anda disimpan dengan aman di **Apple Keychain** (macOS) atau **Brankas Terenkripsi Lokal** (`chmod 0600`). Bebas risiko kebocoran data.

---

## 🎁 Langkah Awal: Dapatkan Google Gemini API Key Gratis (100% Gratis!)

Aplikasi ini menggunakan kecerdasan buatan resmi Google Gemini. Kunci API (*API Key*) ini disediakan gratis oleh Google:

1. Buka situs [Google AI Studio](https://aistudio.google.com/) di peramban Anda.
2. Masuk (*Sign in*) menggunakan akun Google / Gmail Anda.
3. Klik tombol biru **"Get API key"** di pojok kiri atas.
4. Klik tombol **"Create API key"**.
5. Salin kode yang muncul (panjangnya sekitar 39 karakter, berawalan `AIzaSy...`).
6. Simpan kode ini, nanti akan kita masukkan ke dalam aplikasi.

---

## 💻 Panduan Instalasi (Pilih Sesuai Komputer Anda)

### A. Panduan untuk Pengguna Windows

#### 1. Pasang Python (Jika Belum Ada)
- Buka situs resmi [python.org/downloads](https://www.python.org/downloads/) dan unduh installer Python terbaru (versi 3.10, 3.11, atau 3.12).
- Saat membuka file installer, **PENTING: Centang kotak "Add python.exe to PATH"** di bagian paling bawah sebelum menekan tombol *Install Now*.

#### 2. Buka Folder Proyek di Command Prompt
- Buka folder `microstock-ai-studio` di File Explorer.
- Klik pada bilah alamat (*address bar*) di bagian atas folder, ketik `cmd`, lalu tekan tombol **Enter**.
- Jendela hitam Command Prompt akan terbuka langsung di folder tersebut.

#### 3. Pasang Dependensi
Salin dan tempel perintah berikut satu per satu ke jendela Command Prompt, lalu tekan Enter:

```bat
:: 1. Buat lingkungan virtual
python -m venv .venv

:: 2. Aktifkan lingkungan virtual
.venv\Scripts\activate

:: 3. Pasang semua kebutuhan aplikasi
pip install -r requirements.txt
```

#### 4. Jalankan Aplikasi!
Ketik perintah ini untuk membuka antarmuka visual:
```bat
streamlit run app.py
```
Peramban web Anda (Chrome/Edge) akan otomatis terbuka dan menampilkan aplikasi di alamat `http://localhost:8501`.

---

### B. Panduan untuk Pengguna macOS (MacBook / iMac / Mac mini)

#### 1. Buka Terminal
- Tekan tombol **Command (⌘) + Spasi** di keyboard Anda untuk membuka Spotlight.
- Ketik `Terminal`, lalu tekan **Enter**.

#### 2. Masuk ke Folder Aplikasi
- Ketik `cd ` (tambahkan satu spasi setelah cd).
- Seret (*drag and drop*) folder `microstock-ai-studio` dari Finder ke dalam jendela Terminal, lalu tekan **Enter**.

#### 3. Pasang Dependensi
Salin dan tempel perintah berikut ke Terminal, lalu tekan Enter:

```bash
# 1. Buat lingkungan virtual
python3 -m venv .venv

# 2. Aktifkan lingkungan virtual
source .venv/bin/activate

# 3. Pasang dependensi
pip install -r requirements.txt
```

#### 4. Jalankan Aplikasi!
Pilih cara yang Anda sukai:
```bash
# Pilihan 1: Antarmuka Web Lengkap (Streamlit)
streamlit run app.py

# Pilihan 2: Mode Aplikasi Desktop Super Ringan (< 35 MB RAM, Buka Instan)
python cli.py desktop
```

---

## 🎯 Panduan Praktis Pemakaian 4 Tab Workstation

Setelah aplikasi terbuka, masukkan **Gemini API Key** Anda pada kolom di sidebar kiri, lalu klik **Simpan API Key**. Anda sudah siap berkreasi!

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

### Tab 1: Commercial Prompt Studio (Meracik Prompt Bernilai Jual)
Gunakan tab ini saat Anda ingin membuat gambar baru dari ide tulisan.
1. **Ketik Ide Anda:** Tulis apa saja di kotak ide (contoh: *"cangkir kopi espresso di atas meja kayu kafe minimalis"*).
2. **Pilih Gaya Visual:** Pilih kategori gaya yang diinginkan (Fotografi, 3D Render, Ilustrasi Stiker Die-Cut, Cat Air, atau Animasi).
3. **Pilih Komposisi & Rasio:** Pilih rasio aspek (16:9 untuk banner web, 1:1 untuk postingan, atau 9:16 untuk story). Jika ingin gambar mudah ditambahi teks iklan oleh pembeli, pilih framing *Negative Space for Copy*.
4. **Klik "Racik 5 Prompt Komersial":** Dalam 3 detik, Anda akan mendapatkan 5 variasi prompt bahasa Inggris profesional yang siap Anda salin ke alat generate gambar favorit Anda (Midjourney, Gemini, Flux, atau Stable Diffusion).

---

### Tab 2: Pemeriksa Gambar, Upscale & Auto-Keywords
Gunakan tab ini setelah Anda selesai men-generate gambar dan menyimpannya di komputer.
1. **Otomatis Pantau Folder Download:** Aplikasi otomatis mendeteksi gambar yang baru saja Anda unduh di folder `Downloads` Mac/Windows Anda. Cukup pilih rentang waktu (*15 Menit Terakhir / Hari Ini*) lalu klik **Pindai Folder**.
2. **Centang Opsi Upscale:**
   - *Wajibkan minimal 4 MP:* Menjamin gambar Anda otomatis diperbesar ke $\ge 4$ Megapiksel agar tidak ditolak Adobe Stock.
   - *Wajibkan minimal 4 MB:* Memastikan ukuran file cukup besar untuk standar Freepik.
3. **Klik "Mulai Proses Batch":**
   - AI akan melihat gambar Anda dan menyusun judul komersial serta **50 kata kunci SEO anti-reject**.
   - 10 kata kunci teratas otomatis ditata berdasarkan kata kunci yang paling sering dicari pembeli (*Buyer Intent Ranking*).
   - Seluruh metadata ini **ditanam langsung ke dalam file gambar JPEG**.
   - File hasil proses tersimpan rapi di folder `exports/batch_[tanggal]/`.

---

### Tab 3: Reverse Prompt Studio (Membongkar Estetika Gambar)
Punya gambar referensi yang sangat bagus di internet dan ingin tahu cara membuat gambar dengan gaya serupa?
1. Unggah gambar referensi Anda ke kotak unggah di Tab 3.
2. AI Gemini Vision akan membedah komposisi, pencahayaan, tekstur, sudut kamera, dan rasio aspek aslinya.
3. Hasil prompt bahasa Inggris otomatis tersimpan ke komputer Anda dalam format teks (`exports/prompts/prompt_[nama].txt`).

---

### Tab 4: Distribusi Contributor & Database Studio
Gunakan tab ini untuk melihat riwayat aset lokal dan mengirim gambar langsung ke agensi stok.
1. **Katalog Aset Lokal:** Melihat seluruh gambar yang pernah Anda proses, lengkap dengan status resolusi, tanggal, dan kode hash duplikasi.
2. **Kirim via FTP/SFTP Langsung:**
   - Pilih agensi target (**Adobe Stock**, **Shutterstock**, atau **Freepik**).
   - Masukkan ID/Username dan Password kontributor Anda (dapat dilihat di menu upload FTP pada akun kontributor resmi masing-masing agensi).
   - Klik **Simpan Kredensial Agensi** (data tersimpan di brankas aman terenkripsi komputer Anda).
   - Klik **Tes Koneksi Server** untuk memastikan komputer Anda terhubung ke server agensi.
   - Masukkan nama folder hasil batch dari Tab 2, lalu klik **Kirim ke Agensi**. Gambar Anda akan terunggah otomatis di latar belakang!

---

## ⚡ Perintah Cepat Lewat Terminal (CLI)

Bagi Anda yang menyukai efisiensi kerja tanpa membuka peramban web:

```bash
# 1. Buka Workstation Desktop Native (Sangat ringan, RAM < 35 MB)
python cli.py desktop

# 2. Buka Workstation Versi Web (Streamlit)
python cli.py gui

# 3. Buat prompt komersial kilat dari terminal
python cli.py prompt "cangkir teh herbal hangat di meja kayu" --style "Fotografi (Photorealism)"

# 4. Proses otomatis seluruh isi folder unduhan:
python cli.py process ~/Downloads --upscale

# 5. Cek ringkasan database aset yang tersimpan di komputer
python cli.py db

# 6. Kirim seluruh gambar di folder langsung ke Adobe Stock via SFTP
python cli.py upload adobe_stock exports/batch_20261110_103000/
```

---

## ❓ Tanya Jawab & Kendala Umum (FAQ)

<details>
<summary><b>1. Muncul pesan "'python' is not recognized as an internal or external command" di Windows?</b></summary>
Ini terjadi jika Anda lupa mencentang kotak <i>"Add python.exe to PATH"</i> saat menginstal Python. Solusinya: buka kembali installer Python, pilih <b>Modify</b>, dan pastikan opsi <i>Add to PATH</i> dicentang, lalu restart Command Prompt Anda.
</details>

<details>
<summary><b>2. Apakah gambar dan data saya aman?</b></summary>
<b>100% Aman!</b> Aplikasi ini menganut filosofi <i>Local-First</i>. Seluruh data, basis data SQLite, gambar, dan kata sandi Anda tersimpan secara lokal di harddisk komputer Anda sendiri. Aplikasi tidak pernah mengirim data ke server pihak ketiga manapun selain endpoint resmi Google Gemini AI (hanya untuk analisis teks/metadata) dan server resmi agensi stok yang Anda tuju.
</details>

<details>
<summary><b>3. Mengapa saya tidak perlu lagi mengunggah file CSV ke Adobe Stock?</b></summary>
Karena aplikasi ini memiliki modul <b>Lossless Adobe XMP Injector</b>. Judul, deskripsi, dan 50 kata kunci sudah tertanam di dalam segmen header file JPEG Anda. Begitu Anda mengunggah file gambar ke portal Adobe Stock Contributor atau Shutterstock, server mereka akan otomatis membaca data tersebut dari dalam file gambarnya secara instan!
</details>

<details>
<summary><b>4. Apakah ada biaya bulanan untuk menggunakan aplikasi ini?</b></summary>
<b>Nol rupiah alias Gratis Selamanya!</b> Aplikasi ini adalah perangkat lunak sumber terbuka (open-source). Penggunaan Gemini AI API juga gratis dalam batas kuota harian dari Google AI Studio yang lebih dari cukup untuk memproses ratusan gambar setiap hari.
</details>

---

## 📜 7 Aturan Kepatuhan Komersial Microstock (Universal Commercial Rules)

Setiap prompt dan metadata yang dihasilkan oleh aplikasi ini secara otomatis disterilkan dari 7 penyebab penolakan kurator agensi:
- ❌ **Zero Female Characters:** Bebas dari karakter wanita/feminin (fokus pada objek, kuliner, alam, arsitektur).
- ❌ **Zero Text / Typography:** Bebas dari huruf, angka, kata, logo, dan watermark.
- ❌ **Mandatory Faceless:** Makhluk hidup dibuat tanpa ekspresi wajah (*shot from behind*, siluet, fokus tangan).
- ❌ **Unbranded Props:** Properti gawai, mobil, dan perlengkapan bersih dari merek dagang terdaftar.
- ✅ **Negative Copy Space:** Komposisi lapang untuk penempatan materi iklan oleh pembeli.
- ✅ **Authentic Photographic Lighting:** Pencahayaan alami foto asli tanpa kilau plastik waxy (*anti-plastic sheen*).
- ✅ **Physical Micro-Textures:** Tekstur material nyata (serat kayu, kain linen, pantulan kaca bersih).

---

*Dibuat dengan cinta untuk kemerdekaan finansial kreator microstock di seluruh dunia.* 🌟
