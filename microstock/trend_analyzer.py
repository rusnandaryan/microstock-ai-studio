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
Tugas Anda adalah menganalisis dan memprediksi 4 kategori aset komersial yang saat ini SEDANG TRENDING dan PALING BANYAK DIUNDUH di Adobe Stock & Shutterstock berdasarkan kalender pemasaran global dan tren kreatif.

Untuk setiap tren, berikan:
1. "category": Nama kategori tren (contoh: "AI & Otomasi Hijau", "Kuliner Artisan Lokal").
2. "reason": Penjelasan ringkas mengapa aset ini sangat diminati oleh pembeli agensi.
3. "base_idea": Ide dasar (base idea) konkret, 100% AMAN hak cipta, TANPA wanita, TANPA teks, faceless/objek/arsitektur.
4. "market_status": Status potensi pasar, pilih salah satu yang paling relevan:
   - "🔥 High Demand / Low Competition"
   - "⭐ Evergreen Best Seller"
   - "🚀 Rising Market Trend"
5. "recommended_cat": Kategori visual yang paling cocok, WAJIB salah satu dari:
   ["Fotografi (Photorealism)", "Ilustrasi & Seni Lukis", "Animasi & Kartun", "3D & Render", "Desain & Digital Art"]
6. "recommended_style": Sub-gaya yang direkomendasikan (misal: "📷 Foto Komersial Bersih (Commercial Advertising)", "📐 3D Isometric Illustration (Tech & Business)", "🏷️ Paket Stiker Die-Cut (Die-Cut Sticker Pack)", dll).
7. "recommended_ratio": Rasio aspek terbaik, pilih salah satu dari: ["16:9", "1:1", "9:16", "4:3"].

Keluarkan HANYA array JSON yang valid berisi 4 objek tanpa markdown formatting.
"""

def _parse_trends_json(text: str, now_str: str) -> Optional[Dict[str, Any]]:
    clean = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    if not clean:
        return None
    data = json.loads(clean)
    if isinstance(data, list) and len(data) > 0:
        return {"period": now_str, "trends": data}
    if isinstance(data, dict) and "trends" in data:
        return {"period": now_str, "trends": data["trends"]}
    return None


def get_trending_ideas(
    client: Any,
    on_retry: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Call Gemini to get trending microstock ideas with detailed market metadata."""
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
                    prompt_query = f"Analisis 4 tren komersial teratas Adobe Stock untuk periode {now_str}."
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
                        input="Berikan 4 trend gambar microstock paling laris saat ini.",
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
