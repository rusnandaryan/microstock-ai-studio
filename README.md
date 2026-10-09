# 📸 Microstock AI Studio

Aplikasi cerdas berbasis **Streamlit** yang dirancang secara khusus untuk membantu kontributor **Adobe Stock** dan **Shutterstock** bekerja jauh lebih cepat dan efisien. Aplikasi ini memanfaatkan **Google Gemini API** (Gemini Text & Gemini Vision) untuk meracik prompt fotografi komersial berkualitas tinggi, serta melakukan inspeksi visual pada gambar untuk menghasilkan metadata SEO (Title, Description, 50 Keywords) yang sangat akurat.

![Tampilan UI](https://img.shields.io/badge/UI-Neo_Pop-FF5436?style=flat-square) ![Streamlit](https://img.shields.io/badge/Built_with-Streamlit-FF4B4B?style=flat-square) ![Gemini](https://img.shields.io/badge/Powered_by-Google_Gemini-4285F4?style=flat-square)

---

## ✨ Fitur Utama & Alur Kerja Aplikasi

Aplikasi ini dibagi menjadi 2 alat utama (Tab) yang bekerja berkesinambungan:

### 🎯 Tab 1: Magic Prompt Studio (Generator Prompt Komersial)
Fitur ini mengubah ide singkat Anda (misalnya: *"Barista membuat kopi"*) menjadi sebuah *prompt* bahasa Inggris standar produksi (production-ready) yang panjang, sangat detail, dan siap dieksekusi oleh AI Image Generator manapun (terutama Gemini).
* **Kustomisasi Lengkap:** Anda dapat memilih Gaya Visual (Cinematic, Macro, dll), Pencahayaan (Golden hour, Studio lighting), Lensa Kamera, Komposisi (Rule of thirds, Symmetrical), hingga Aspek Rasio (16:9, 9:16, 1:1).
* **Anti-Copyright Strike:** Prompt yang dihasilkan diprogram dengan aturan ketat untuk *TIDAK* memasukkan nama tokoh asli, nama seniman (style of artists), merek dagang (Apple, Nike, dll), dan selalu meminta anatomi tubuh yang realistis (5 jari tangan proporsional). Ini sangat penting agar gambar Anda tidak ditolak (reject) oleh agensi Microstock.
* **Output:** Teks prompt siap salin yang dapat Anda *paste* langsung ke [Gemini Web](https://gemini.google.com).

### 🔍 Tab 2: Inspeksi Visual & Paket Microstock (Gemini Vision)
Setelah Anda mendapatkan gambar hasil generate (dari Gemini Web atau AI lain), unggah gambar tersebut ke tab ini. 
* **Analisis Visual Akurat:** Gemini Vision akan memindai isi gambar secara nyata untuk mengenali objek, suasana, dan detail di dalamnya.
* **Auto-Metadata SEO:** Menghasilkan Judul (Title) di bawah 100 karakter, Deskripsi, dan **tepat 50 Keywords** relevan (anti-reject, de-duplicated, tanpa merek) yang memaksimalkan penemuan gambar Anda di mesin pencari agensi.
* **Tidak Merusak Resolusi:** Gambar Anda dipertahankan dalam resolusi aslinya yang tinggi tanpa kompresi berlebih (support hingga batas resolusi agensi).
* **Download Lengkap (Batch & ZIP):** Menyusun CSV format standar Adobe Stock dan Shutterstock beserta gambar-gambarnya dalam satu file ZIP. Tinggal upload!

---

## 🚀 Prasyarat Sistem

Sebelum menjalankan aplikasi, pastikan Anda telah memiliki:
1. **Python:** Versi 3.9 atau yang lebih baru (sangat disarankan 3.10+). Dapat diunduh di [python.org](https://www.python.org/).
2. **Google Gemini API Key:** Dapatkan kunci API ini secara **GRATIS** di [Google AI Studio](https://aistudio.google.com/). Kunci ini diperlukan agar aplikasi dapat berkomunikasi dengan mesin kecerdasan Google.
3. **Git (Opsional):** Untuk mengunduh repositori ini.

---

## 💻 Panduan Instalasi Lengkap (Langkah demi Langkah)

Ikuti langkah-langkah di bawah ini untuk menginstal dan menjalankan aplikasi di komputer lokal Anda (Windows maupun Mac/Linux).

### Langkah 1: Unduh Kode Aplikasi (Clone Repository)
Buka aplikasi **Terminal** (bagi pengguna Mac/Linux) atau **Command Prompt / PowerShell** (bagi pengguna Windows), lalu jalankan perintah berikut:
```bash
git clone https://github.com/username-anda/microstock-ai-studio.git
```
Setelah proses unduh selesai, masuk ke dalam folder proyek:
```bash
cd microstock-ai-studio
```

### Langkah 2: Buat Lingkungan Virtual (Virtual Environment)
*Virtual environment* (venv) adalah folder khusus untuk menyimpan library aplikasi ini agar tidak bentrok dengan aplikasi Python lain di komputer Anda. Jalankan perintah ini:
```bash
python -m venv .venv
```
*(Catatan: Jika Anda menggunakan Mac/Linux dan perintah `python` tidak dikenali, coba gunakan `python3 -m venv .venv`)*

### Langkah 3: Aktifkan Virtual Environment
Sebelum menginstal paket yang dibutuhkan, aktifkan venv yang baru saja dibuat.

**Bagi Pengguna Mac & Linux:**
```bash
source .venv/bin/activate
```

**Bagi Pengguna Windows (Command Prompt / CMD):**
```cmd
.venv\Scripts\activate
```

**Bagi Pengguna Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```
*(Jika berhasil, Anda akan melihat tulisan `(.venv)` muncul di sebelah kiri baris perintah Terminal Anda).*

### Langkah 4: Instal Library yang Dibutuhkan
Setelah venv aktif, instal semua dependensi (seperti Streamlit, Pillow, Google GenAI) yang terdaftar di `requirements.txt`:
```bash
pip install -r requirements.txt
```
Tunggu proses unduh dan instalasi selesai.

### Langkah 5: Jalankan Aplikasi
Sekarang, Anda sudah bisa menjalankan aplikasi dengan perintah:
```bash
streamlit run app.py
```
Browser web Anda akan otomatis membuka tab baru dengan alamat `http://localhost:8501`. Jika tidak terbuka otomatis, silakan salin URL tersebut dan *paste* di browser Anda.

---

## 🎨 Panduan Penggunaan Harian (Alur Kerja)

1. **Masukkan API Key:** Saat pertama kali membuka aplikasi, lihat panel (sidebar) di sebelah kiri. Masukkan *Gemini API Key* Anda ke dalam kolom yang tersedia, lalu tekan Enter. Anda dapat menyimpannya agar tidak perlu mengetik ulang setiap saat.
2. **Buat Prompt (Tab 1):** Tuliskan ide kasar Anda (misal: "Kucing bermain bola salju"). Pilih estetika yang diinginkan. Klik **Generate Magic Prompt**.
3. **Salin & Bawa ke Gemini Web:** Salin prompt bahasa Inggris yang dihasilkan. Buka tab browser baru, kunjungi **gemini.google.com**, dan perintahkan Gemini untuk menggambar sesuai prompt tersebut.
4. **Download Gambar:** Setelah gambar jadi di web Gemini, klik tombol unduh (download) pada gambar tersebut.
5. **Inspeksi (Tab 2):** Kembali ke aplikasi ini, buka **Tab 2**. Seret (drag & drop) gambar yang baru saja Anda download ke dalam kotak unggahan. Anda bisa memasukkan hingga 10+ gambar sekaligus.
6. **Mulai Analisis:** Klik tombol **Mulai Analisis**. Gemini Vision akan bekerja mencari keyword, membuat CSV, dan menyatukannya dalam satu paket.
7. **Selesai!** Klik **Download Semua (ZIP)**. Anda kini mendapatkan gambar dan file CSV yang 100% siap diunggah ke portal kontributor microstock.

---

## 🔐 Keamanan API Key & File Sementara (Penting)

* **Keamanan API Key:** Demi kemudahan, aplikasi ini menyimpan API Key Anda di komputer Anda sendiri secara lokal dalam file tersembunyi bernama `.env`. File `.env` ini **sudah diatur untuk diabaikan (ignore)** oleh Git, sehingga jika Anda mempublikasikan (push) repositori ini ke GitHub, kunci rahasia Anda **TIDAK AKAN** ikut terupload.
* **Penyimpanan Lokal & Ukuran Folder:** Setiap kali Anda melakukan analisis gambar di Tab 2, aplikasi akan menyimpan salinan cadangan gambar dan file CSV Anda ke dalam folder lokal bernama `exports/`. Hal ini bertujuan agar data Anda tidak hilang jika browser tertutup secara tidak sengaja. Namun, **ini akan membuat ukuran folder proyek membengkak seiring waktu.** Anda sangat disarankan untuk **menghapus isi folder `exports/` secara berkala** untuk mengosongkan ruang penyimpanan (disk space) di komputer Anda. Folder `exports/` ini juga tidak akan ikut terupload ke GitHub karena sudah diblokir di konfigurasi Git.

---
*Dikembangkan untuk efisiensi tinggi kontributor microstock. Happy Contrib!*
