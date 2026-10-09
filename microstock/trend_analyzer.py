"""Trend analyzer for Adobe Stock using Gemini."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync

TREND_SYSTEM_INSTRUCTION = """\
Anda adalah Analis Data Adobe Stock Profesional dan Pakar Microstock.
Tugas Anda adalah menganalisis dan memprediksi 4 kategori gambar komersial yang saat ini SEDANG TRENDING dan PALING BANYAK DIUNDUH di Adobe Stock atau Shutterstock.

Untuk setiap kategori, berikan:
1. "category": Nama kategori tren tersebut.
2. "reason": Penjelasan singkat MENGAPA ini sangat laku di pasaran saat ini.
3. "base_idea": Satu ide dasar (base idea) gambar yang spesifik, sangat komersial, 100% AMAN dari hak cipta, TANPA karakter wanita, TANPA teks/tulisan apapun, dan berorientasi faceless / objek / arsitektur / teknologi.

Keluarkan HANYA array JSON yang valid tanpa markdown formatting. Contoh:
[
  {
    "category": "Teknologi Hijau & Keberlanjutan",
    "reason": "Banyak perusahaan membutuhkan aset visual untuk laporan ESG dan kampanye ramah lingkungan.",
    "base_idea": "Seorang arsitek pria tampak belakang sedang mengamati maket kota ramah lingkungan dengan pencahayaan alami jendela"
  }
]
"""

def get_trending_ideas(
    client: genai.Client,
    on_retry: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, str]]:
    """Call Gemini to get trending microstock ideas."""
    
    def _call() -> List[Dict[str, str]]:
        last_err = None
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=TREND_SYSTEM_INSTRUCTION,
                        temperature=0.9, # Higher temperature for creative/varied trends
                        response_mime_type="application/json",
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents="Berikan 4 trend gambar microstock paling laris saat ini.",
                        config=config_obj,
                    )
                    text = (response.text or "").strip()
                    if text:
                        # Clean up markdown if model ignored instruction
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.startswith("```"):
                            text = text[3:]
                        if text.endswith("```"):
                            text = text[:-3]
                            
                        data = json.loads(text.strip())
                        if isinstance(data, list) and len(data) > 0:
                            return data
                elif hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        system_instruction=TREND_SYSTEM_INSTRUCTION,
                        input="Berikan 4 trend gambar microstock paling laris saat ini.",
                        store=False,
                    )
                    text = (interaction.output_text or "").strip()
                    if text:
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.startswith("```"):
                            text = text[3:]
                        if text.endswith("```"):
                            text = text[:-3]
                            
                        data = json.loads(text.strip())
                        if isinstance(data, list) and len(data) > 0:
                            return data
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "404" in err_str:
                    continue
                # If json parsing fails, let it raise or continue? We should retry on TransientError
                raise TransientError(f"Failed to parse JSON: {e}")

        if last_err:
            raise last_err
        raise TransientError("Empty response from trend analyzer")

    return retry_sync(_call, label="Trend analysis", on_retry=on_retry)
