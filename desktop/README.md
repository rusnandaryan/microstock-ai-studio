# Microstock AI Studio Pro — Desktop Native Shell

Struktur proyek desktop native resmi berbasis **Tauri 2.0 (Rust backend shell + OS Native Windowing)**.

## Menjalankan Desktop Mode Langsung (Zero Dependency)
Anda dapat langsung menjalankan antarmuka desktop native berkecepatan tinggi tanpa perlu memasang Rust menggunakan perintah:

```bash
# Meluncurkan Desktop Native App Mode
python cli.py desktop
```
Perintah ini akan menjalankan server lokal ultra-ringan pada port `8505` dan secara otomatis membuka jendela native desktop app.

## Mengompilasi Biner Mandiri (.app / .dmg / .exe) dengan Tauri
Jika compiler Rust telah terpasang di komputer Anda (`cargo` dan `rustc`):

```bash
# 1. Masuk ke direktori tauri
cd desktop/src-tauri

# 2. Pasang Tauri CLI (jika belum ada)
cargo install tauri-cli --version "^2.0"

# 3. Build biner mandiri desktop
cargo tauri build
```
File biner executable mandiri akan dihasilkan di `desktop/src-tauri/target/release/bundle/`.
