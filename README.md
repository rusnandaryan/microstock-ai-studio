# 📸 Microstock AI Studio

Selamat datang di **Microstock AI Studio**! 
Aplikasi ini dibuat khusus untuk membantu Anda yang ingin berjualan gambar AI (seperti di Adobe Stock atau Shutterstock) agar bisa bekerja jauh lebih cepat dan terhindar dari pelanggaran hak cipta. Aplikasi ini menggunakan otak pintar **Google Gemini AI**.

---

## ✨ Apa Saja yang Bisa Dilakukan Aplikasi Ini?

Aplikasi ini dibagi menjadi 3 bagian utama:

### 🎯 Tab 1: Studio Pembuat Prompt (Text to Prompt)
Ubah ide singkat Anda (misal: "arsitek mengamati maket") menjadi 5 pilihan kalimat perintah (*prompt*) bahasa Inggris tingkat profesional.
* **Fitur Cek Tren:** Melihat daftar gambar apa saja yang sedang laris manis didownload orang di Adobe Stock saat ini.
* **Aturan Ketat Otomatis:** Prompt dijamin bebas wanita (*no female*), tanpa teks (*zero typography*), dan karakter selalu tanpa wajah (*faceless*).
* **5 Pilihan Prompt:** Disediakan 5 variasi sudut pandang berbeda untuk 1 ide dasar.

### 🔍 Tab 2: Pemeriksa Gambar, Upscale & SEO Metadata (Gemini Vision)
Unggah gambar hasil AI Anda untuk dianalisis dan dibungkus menjadi paket siap jual.
* **Auto-Upscaler Lokal (NCNN):** Pilihan memperbesar resolusi gambar hingga 4K secara otomatis langsung dari kartu grafis komputer Anda.
* **Hemat Memori (Auto-Cleanup):** Jika Anda memilih tidak melakukan *upscale*, file gambar asli tidak akan disimpan di disk (hanya menyimpan CSV-nya saja), menjaga penyimpanan komputer Anda tetap lega.
* **50 Keywords Anti-Reject:** Menghasilkan Judul (<100 karakter), Deskripsi, dan tepat 50 keywords yang siap dimasukkan ke Adobe Stock & Shutterstock.

### 🖼️ Tab 3: Reverse Prompt Studio (Image to Prompt)
Punya gambar referensi yang bagus dan ingin membuat prompt serupa?
* **Bedah Visual Otomatis:** Gemini Vision membaca pencahayaan, lensa, dan komposisi dari gambar referensi Anda.
* **Prompt Bersih Standar Microstock:** Menghasilkan 1 prompt komersial yang telah disterilkan sesuai 7 aturan ketat.
* **Auto-Save ke `.txt`:** Prompt otomatis tersimpan di komputer Anda pada folder `exports/prompts/prompt_[nama_file].txt` agar tidak hilang.

---

## ⚠️ PERHATIAN PENTING (Wajib Dibaca)

1. **Ukuran Gambar Harus Diperbesar (Upscale):** 
   Gambar asli yang Anda unduh langsung dari website AI (seperti Gemini Web) **ukurannya terlalu kecil** untuk dijual. Anda **WAJIB** memperbesar resolusi gambar tersebut (melakukan *Upscale*) menggunakan aplikasi pihak ketiga (seperti *Upscayl*, *Topaz*, atau *Magnific*) SEBELUM diunggah ke website microstock.
2. **Memakan Memori Komputer Anda:** 
   Setiap kali Anda menggunakan Tab 2, aplikasi ini akan menyimpan salinan gambar dan file CSV di komputer Anda (di dalam folder bernama `exports/`). **Folder ini akan semakin membengkak dan membuat penyimpanan komputer Anda penuh.** Pastikan Anda sering mengecek dan menghapus isi folder `exports/` secara berkala!

---

## 💻 Panduan Instalasi (Untuk Pemula Pemula)

Jangan khawatir jika Anda tidak terlalu paham komputer. Ikuti langkah ini pelan-pelan secara berurutan.

### 1. Persiapan Awal
1. Pastikan komputer Anda sudah terinstal **Python** (versi 3.9 ke atas). Jika belum, download dari [python.org](https://www.python.org/) dan instal (saat instalasi, **wajib centang kotak "Add Python to PATH"**).
2. Dapatkan kunci rahasia (**API Key**) dari Google secara **Gratis**. Buka [Google AI Studio](https://aistudio.google.com/), login dengan akun Google Anda, klik "Get API Key", lalu buat kunci baru. Simpan kuncinya baik-baik.

### 2. Membuka Aplikasi di Komputer Anda
1. Download seluruh file aplikasi ini, atau gunakan perintah `git clone https://github.com/username/microstock-ai-studio.git` jika Anda paham Git.
2. Buka aplikasi **Terminal** (jika Anda pakai Mac) atau **Command Prompt / CMD** (jika Anda pakai Windows).
3. Ketik perintah ini untuk masuk ke folder aplikasi Anda (ubah tulisan yang didalam kurung sesuai lokasi folder di komputer Anda):
   ```bash
   cd C:\Lokasi\Folder\microstock-ai-studio
   ```
4. Buat ruang khusus (Virtual Environment) dengan mengetik:
   ```bash
   python -m venv .venv
   ```
5. Aktifkan ruang khusus tersebut:
   * **Pengguna Windows:** ketik `.venv\Scripts\activate`
   * **Pengguna Mac:** ketik `source .venv/bin/activate`
6. Pasang mesinnya dengan mengetik:
   ```bash
   pip install -r requirements.txt
   ```
   *(Tunggu sampai proses download selesai 100%)*

### 3. Menjalankan Aplikasi
Setiap kali Anda ingin menggunakan aplikasi ini di hari-hari berikutnya, Anda hanya perlu membuka Terminal/CMD, masuk ke foldernya (Langkah 3), aktifkan ruang khususnya (Langkah 5), lalu ketik:
```bash
streamlit run app.py
```
Aplikasi akan otomatis terbuka di browser Anda (seperti Google Chrome) seperti membuka website biasa! Masukkan **API Key** yang sudah Anda buat di sebelah kiri layar, dan Anda siap bekerja.

*(Tenang saja, API Key Anda sangat aman tersimpan di komputer Anda sendiri dan tidak akan bocor ke internet).*
