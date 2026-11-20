#!/usr/bin/env bash
# Microstock Studio Launcher
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo " Memulai Microstock AI Studio Precision"
echo " URL: http://localhost:8501/"
echo "============================================"

# Buka browser secara otomatis di macOS
(sleep 1 && open "http://localhost:8501/") &

# Jalankan server dengan Python virtual environment
exec ./.venv/bin/python server.py
