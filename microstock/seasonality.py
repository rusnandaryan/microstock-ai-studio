"""Commercial Seasonality & Lead-Time Calendar Engine.

Calculates optimal microstock production windows using the industry-standard
60-90 day buyer lead-time rule (ad agencies and brands license seasonal content
2 to 3 months before public campaigns launch).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SeasonalOpportunity:
    event_name: str
    target_event_month: str
    production_window: str
    urgency: str
    commercial_reason: str
    suggested_themes: List[str]
    high_intent_keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


SEASONAL_CALENDAR_DATA = [
    {
        "active_months": [1, 2],  # Jan - Feb
        "opportunities": [
            SeasonalOpportunity(
                event_name="Musim Semi & Paskah (Spring & Easter)",
                target_event_month="Maret - April",
                production_window="Januari - Februari",
                urgency="Puncak Pencarian Pembeli",
                commercial_reason="Desainer dan ritel global sedang menyusun katalog promosi musim semi dan dekorasi pastel.",
                suggested_themes=[
                    "Bunga tulip segar dan dekorasi meja makan musim semi bernuansa pastel lembut",
                    "Komposisi flat lay telur hias kayu minimalis dengan negative space untuk copy",
                    "Piknik keluarga faceless di taman rumput hijau dengan pencahayaan natural softbox",
                ],
                high_intent_keywords=["spring", "easter", "floral", "pastel", "fresh", "copy space", "nature", "seasonal"],
            ),
            SeasonalOpportunity(
                event_name="Ramadan & Idul Fitri (Islamic Celebrations)",
                target_event_month="Maret - April",
                production_window="Januari - Februari",
                urgency="Sangat Tinggi (High Demand)",
                commercial_reason="Permintaan masif dari korporat, perbankan, dan e-commerce di Timur Tengah dan Asia Tenggara.",
                suggested_themes=[
                    "Lentera arabesque modern minimalis di atas meja kayu dengan kurma dan cangkir teh",
                    "Siluet masjid estetik 3D miniature dengan pencahayaan golden hour hangat",
                    "Ketupat ornamen modern dan amplop hadiah lebaran bersih unbranded",
                ],
                high_intent_keywords=["ramadan", "eid mubarak", "islamic", "lantern", "dates", "celebration", "arabesque", "copy space"],
            ),
        ],
    },
    {
        "active_months": [3, 4],  # Mar - Apr
        "opportunities": [
            SeasonalOpportunity(
                event_name="Liburan Musim Panas & Wisata (Summer Travel)",
                target_event_month="Juni - Juli",
                production_window="Maret - April",
                urgency="Puncak Pencarian Pembeli",
                commercial_reason="Biro perjalanan, maskapai, dan hotel menyiapkan kampanye liburan tengah tahun.",
                suggested_themes=[
                    "Kacamata hitam, topi jerami, dan kelapa di atas pasir pantai dengan sudut top-down flat lay",
                    "Minuman tropis segar berembun dingin di tepi kolam renang bernuansa biru jernih",
                    "Perlengkapan kamping petualangan minimalis di hutan pinus",
                ],
                high_intent_keywords=["summer", "travel", "vacation", "beach", "tropical", "holiday", "outdoor", "copy space"],
            ),
        ],
    },
    {
        "active_months": [5, 6],  # May - Jun
        "opportunities": [
            SeasonalOpportunity(
                event_name="Tahun Ajaran Baru (Back to School)",
                target_event_month="Agustus - September",
                production_window="Mei - Juni",
                urgency="Tinggi (Commercial Push)",
                commercial_reason="Perusahaan alat tulis, teknologi edukasi, dan ritel pakaian meluncurkan promo tahun ajaran baru.",
                suggested_themes=[
                    "Peralatan sekolah kayu rapi dalam susunan knolling seimbang dengan batas cutline bersih",
                    "Meja belajar minimalis dengan laptop dan buku catatan terbuka",
                    "Ransel sekolah polos dan botol minum di lantai kayu kelas modern",
                ],
                high_intent_keywords=["back to school", "education", "stationery", "study", "learning", "desk", "supplies", "copy space"],
            ),
        ],
    },
    {
        "active_months": [7, 8],  # Jul - Aug
        "opportunities": [
            SeasonalOpportunity(
                event_name="Halloween & Musim Gugur (Autumn & Halloween)",
                target_event_month="Oktober - November",
                production_window="Juli - Agustus",
                urgency="Puncak Pencarian Pembeli",
                commercial_reason="Pasar stok komersial Amerika dan Eropa mencari labu, dedaunan oranye, dan visual musim gugur.",
                suggested_themes=[
                    "Labu estetik bertekstur tanah liat atau keramik minimalis di atas kain linen",
                    "Secangkir pumpkin spice latte beruap hangat di tengah daun maple kering",
                    "Pola latar belakang abstrak dedaunan emas musim gugur elegan",
                ],
                high_intent_keywords=["autumn", "fall", "halloween", "pumpkin", "leaves", "cozy", "harvest", "thanksgiving", "copy space"],
            ),
        ],
    },
    {
        "active_months": [9, 10],  # Sep - Oct
        "opportunities": [
            SeasonalOpportunity(
                event_name="Natal & Tahun Baru (Christmas & Holiday Season)",
                target_event_month="Desember - Januari",
                production_window="September - Oktober",
                urgency="Sangat Tinggi (Terbesar Tahun Ini)",
                commercial_reason="Musim belanja belanja stok terbesar sepanjang tahun. Seluruh agensi dan periklanan membeli visual liburan.",
                suggested_themes=[
                    "Dekorasi pohon natal minimalis kayu dan ornamen kristal transparan",
                    "Kotak kado berbungkus kertas kraft alami dengan pita rami di samping cangkir cokelat panas",
                    "Latar belakang bokeh lampu perayaan emas mewah dengan copy space luas",
                ],
                high_intent_keywords=["christmas", "holiday", "winter", "xmas", "celebration", "gift", "new year", "festive", "copy space"],
            ),
            SeasonalOpportunity(
                event_name="Black Friday & Cyber Monday",
                target_event_month="November",
                production_window="September - Oktober",
                urgency="Tinggi (E-Commerce Push)",
                commercial_reason="Banner e-commerce, diskon flash sale, dan promosi retail online.",
                suggested_themes=[
                    "Kotak belanja hitam matte dengan pita emas mewah dan label diskon bersih",
                    "Smartphone dan tas belanja minimalis di atas podium studio 3D",
                    "Troli belanja mini dengan paket diskon modern",
                ],
                high_intent_keywords=["black friday", "cyber monday", "shopping", "discount", "sale", "ecommerce", "retail", "copy space"],
            ),
        ],
    },
    {
        "active_months": [11, 12],  # Nov - Dec
        "opportunities": [
            SeasonalOpportunity(
                event_name="Resolusi Tahun Baru & Kebugaran (New Year & Fitness)",
                target_event_month="Januari - Februari",
                production_window="November - Desember",
                urgency="Tinggi (Lifestyle & Health)",
                commercial_reason="Industri kesehatan, gym, asuransi, dan perencana keuangan meluncurkan resolusi tahun baru.",
                suggested_themes=[
                    "Sepatu lari, botol air mineral, dan matras yoga di lantai studio kayu bersih",
                    "Buku catatan resolusi tahun baru dengan pena di samping cangkir matcha",
                    "Sarapan mangkuk smoothie buah segar dengan komposisi flat lay",
                ],
                high_intent_keywords=["new year", "fitness", "healthy", "resolution", "wellness", "lifestyle", "workout", "copy space"],
            ),
        ],
    },
]


def get_current_seasonal_opportunities(month: Optional[int] = None) -> List[SeasonalOpportunity]:
    """Return seasonal opportunities that contributors should produce right now based on active lead-time."""
    cur_month = month or datetime.now().month
    for period in SEASONAL_CALENDAR_DATA:
        if cur_month in period["active_months"]:
            return period["opportunities"]

    # Fallback to November-December cycle if edge case
    return SEASONAL_CALENDAR_DATA[-1]["opportunities"]

