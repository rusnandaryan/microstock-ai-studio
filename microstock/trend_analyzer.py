"""Trend analyzer for Adobe Stock using Gemini."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from . import config
from .rate_limit import TransientError, retry_sync

TREND_SYSTEM_INSTRUCTION = """\
Anda adalah Analis Data Adobe Stock Profesional dan Pakar Riset Pasar Microstock.
Tugas Anda adalah mengidentifikasi 10 momen dan hari peringatan besar (global/internasional/nasional) yang AKAN DATANG dalam 2 hingga 8 minggu ke depan dari tanggal analisis.
Agensi periklanan, desainer grafis, dan penerbit media massa selalu mengunduh aset visual komersial 2-8 minggu sebelum hari peringatan tiba.

Untuk setiap momen atau hari peringatan (total 10 item), berikan:
1. "event_name": Nama hari peringatan / momen besar (contoh: "Hari Bumi Sedunia / Earth Day", "Hari Lingkungan Hidup", "World Oceans Day").
2. "category": Sama dengan event_name.
3. "target_date": Perkiraan tanggal atau bulan perayaan (contoh: "22 April", "Minggu ke-3 Mei").
4. "market_status": Estimasi tingkat atensi publik dan media:
   - "🔥 Viral / Liputan Global Masif"
   - "⭐ Tradisi Tahunan Best-Seller"
   - "🚀 Momen Baru / Rising Awareness"
5. "reason": Penjelasan ringkas mengapa momen ini menarik atensi media dan aset visualnya sangat dicari pengiklan saat ini.
6. "base_idea": Ide gambar komersial konkret, 100% AMAN hak cipta, TANPA wanita, TANPA teks/tulisan/angka/logo, fokus faceless/objek/lanskap/arsitektur/hands-in-action.
7. "recommended_cat": Kategori visual yang paling cocok, WAJIB salah satu dari:
   ["Fotografi (Photorealism)", "Ilustrasi & Seni Lukis", "Animasi & Kartun", "3D & Render", "Desain & Digital Art"]
8. "recommended_style": Sub-gaya yang direkomendasikan (misal: "📷 Foto Komersial Bersih (Commercial Advertising)", "📐 3D Isometric Illustration (Tech & Business)", "🏷️ Paket Stiker Die-Cut (Die-Cut Sticker Pack)", dll).
9. "recommended_ratio": Rasio aspek terbaik, pilih salah satu dari: ["16:9", "1:1", "9:16", "4:3"].

Keluarkan HANYA array JSON yang valid berisi 10 objek tanpa markdown formatting.
"""

def _parse_trends_json(text: str, now_str: str) -> Optional[Dict[str, Any]]:
    clean = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    if not clean:
        return None
    data = json.loads(clean)
    trends = None
    if isinstance(data, list) and len(data) > 0:
        trends = data
    elif isinstance(data, dict) and "trends" in data and isinstance(data["trends"], list):
        trends = data["trends"]

    if trends:
        for t in trends:
            if isinstance(t, dict):
                if "category" not in t and "event_name" in t:
                    t["category"] = t["event_name"]
                elif "event_name" not in t and "category" in t:
                    t["event_name"] = t["category"]
        return {"period": now_str, "trends": trends}
    return None


def get_trending_ideas(
    client: Any,
    on_retry: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Call Gemini to get 10 upcoming global moments and microstock commercial ideas."""
    now_str = datetime.now().strftime("%d %B %Y")

    def _call() -> Dict[str, Any]:
        last_err = None
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=TREND_SYSTEM_INSTRUCTION,
                        temperature=0.85,
                        response_mime_type="application/json",
                    )
                    prompt_query = f"Analisis 10 momen dan hari peringatan mendatang dalam 2-8 minggu dari {now_str} untuk kebutuhan aset visual komersial Adobe Stock."
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_query,
                        config=config_obj,
                    )
                    parsed = _parse_trends_json(response.text or "", now_str)
                    if parsed:
                        return parsed
                elif hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        system_instruction=TREND_SYSTEM_INSTRUCTION,
                        input=f"Analisis 10 momen dan hari besar mendatang dalam 2-8 minggu dari {now_str} untuk microstock.",
                        store=False,
                    )
                    parsed = _parse_trends_json(interaction.output_text or "", now_str)
                    if parsed:
                        return parsed
            except json.JSONDecodeError as e:
                raise TransientError(f"Failed to parse JSON: {e}") from e
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(term in err_str for term in ("503", "unavailable", "high demand", "404")):
                    continue
                raise

        if last_err:
            raise last_err
        raise TransientError("Empty response from trend analyzer")

    return retry_sync(_call, label="Trend analysis", on_retry=on_retry)
