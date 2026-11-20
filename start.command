#!/usr/bin/env bash
# Double-clickable macOS Launcher
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo " Memulai Microstock AI Studio Precision"
echo " URL: http://localhost:8501/"
echo "============================================"

(sleep 1 && open "http://localhost:8501/") &
exec ./.venv/bin/python server.py
