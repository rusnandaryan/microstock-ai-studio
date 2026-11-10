"""AI Commercial Compliance & Release Shield.

Analyzes microstock assets for commercial risk factors:
- Identifies if Model Release is required (identifiable faces vs faceless).
- Identifies if Property Release is required (private property, architecture, logos).
- Detects banned commercial trademarks.
- Computes a Commercial Safety Score (0-100%).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


KNOWN_BRANDS: Set[str] = {
    "apple", "iphone", "ipad", "macbook", "samsung", "galaxy", "sony", "playstation",
    "microsoft", "xbox", "nike", "adidas", "puma", "gucci", "chanel", "louis vuitton",
    "rolex", "ferrari", "porsche", "bmw", "mercedes", "audi", "tesla", "toyota", "honda",
    "coca-cola", "pepsi", "starbucks", "mcdonalds", "disney", "marvel", "lego", "barbie",
    "google", "instagram", "tiktok", "facebook", "twitter", "youtube", "amazon", "netflix",
}

RESTRICTED_LANDMARKS: Set[str] = {
    "eiffel tower night", "louvre pyramid", "disneyland", "disney world",
    "sydney opera house", "hollywood sign", "empire state building",
    "chrysler building", "rockefeller center", "burj khalifa",
}

FACELESS_INDICATORS: Set[str] = {
    "faceless", "shot from behind", "back view", "silhouette", "unrecognizable",
    "no face", "hands only", "cropped face", "obscured", "anonymous",
}

HUMAN_INDICATORS: Set[str] = {
    "man", "woman", "person", "people", "portrait", "model", "face", "girl",
    "boy", "child", "worker", "businessman", "athlete", "doctor", "chef",
}


@dataclass
class ComplianceReport:
    requires_model_release: bool = False
    requires_property_release: bool = False
    is_commercial_safe: bool = True
    commercial_safety_score: int = 100  # 0 to 100
    editorial_only: bool = False
    detected_risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_commercial_compliance(
    title: str,
    description: str,
    keywords: List[str],
    prompt: Optional[str] = None,
) -> ComplianceReport:
    """Evaluate asset text, metadata, and prompt for microstock legal and commercial risks."""
    report = ComplianceReport()
    score = 100
    corpus = f"{title} {description} {' '.join(keywords)} {prompt or ''}".lower()
    tokens = set(re.findall(r"\b[a-z0-9\-]+\b", corpus))

    # 1. TRADEMARK AND BRAND CHECK (Critical Failure for Commercial Stock)
    found_brands = []
    for brand in KNOWN_BRANDS:
        if brand in tokens or brand in corpus:
            found_brands.append(brand)

    if found_brands:
        report.is_commercial_safe = False
        report.editorial_only = True
        score -= 40
        report.detected_risks.append(f"Terdeteksi nama merek/trademark terlarang: {', '.join(found_brands)}")
        report.recommendations.append("Hapus nama merek dari judul, deskripsi, dan keyword, atau tandai sebagai konten Editorial.")

    # 2. RESTRICTED ARCHITECTURE / PROPERTY CHECK
    found_landmarks = []
    for landmark in RESTRICTED_LANDMARKS:
        if landmark in corpus:
            found_landmarks.append(landmark)

    if found_landmarks:
        report.requires_property_release = True
        score -= 20
        report.detected_risks.append(f"Terdeteksi landmark/arsitektur berhak cipta: {', '.join(found_landmarks)}")
        report.recommendations.append("Wajibkan Property Release resmi dari pemilik lokasi atau gunakan hanya untuk Editorial.")

    # 3. MODEL RELEASE & FACELESS COMPLIANCE CHECK
    has_human = any(h in tokens for h in HUMAN_INDICATORS)
    is_faceless = any(f in corpus for f in FACELESS_INDICATORS)

    if has_human and not is_faceless:
        report.requires_model_release = True
        score -= 15
        report.detected_risks.append("Subjek manusia tampak dapat dikenali tanpa penanda 'faceless'.")
        report.recommendations.append("Unggah Model Release bertanda tangan atau pastikan visual berorientasi faceless / tampak belakang.")
    elif is_faceless:
        report.requires_model_release = False

    # 4. KEYWORD QUALITY & DENSITY CHECK
    if len(keywords) < 20:
        score -= 10
        report.detected_risks.append(f"Jumlah keyword terlalu sedikit ({len(keywords)}/50).")
        report.recommendations.append("Lengkapi hingga minimal 40-50 keywords untuk memaksimalkan visibilitas pencarian.")

    # Final score clamping
    report.commercial_safety_score = max(0, min(100, score))
    if report.commercial_safety_score < 70:
        report.is_commercial_safe = False

    return report
