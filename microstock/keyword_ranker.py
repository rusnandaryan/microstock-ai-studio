"""Predictive Buyer Intent Keyword Ranking Engine.

Re-orders microstock keywords to position high-converting commercial buyer-intent
terms in the critical first 10 slots (heavily weighted by Adobe Stock and Shutterstock
search ranking algorithms).
"""
from __future__ import annotations

import re
from typing import List, Set

# Commercial terms frequently searched by ad agencies, art directors, and designers
HIGH_INTENT_BUYER_TERMS: Set[str] = {
    "copy space", "copyspace", "blank space", "negative space", "background",
    "minimalist", "isolated", "concept", "commercial", "advertising", "modern",
    "mockup", "template", "banner", "flat lay", "top view", "overhead", "hero",
    "lifestyle", "professional", "business", "design", "creative", "quality",
    "organic", "authentic", "workspace", "technology", "culinary", "sustainable",
}

SECONDARY_COMMERCIAL_TERMS: Set[str] = {
    "clean", "fresh", "healthy", "luxury", "wooden", "natural", "cozy", "warm",
    "vintage", "retro", "industrial", "traditional", "futuristic", "abstract",
    "textured", "interior", "exterior", "composition", "detail", "close up",
}


def rank_keywords_by_buyer_intent(
    keywords: List[str],
    title: str,
    description: str = "",
) -> List[str]:
    """Score and re-rank keywords so the top 10 positions contain highest-value buyer search queries."""
    if not keywords:
        return []

    title_words = set(re.findall(r"\b[a-z0-9]+\b", title.lower()))
    desc_words = set(re.findall(r"\b[a-z0-9]+\b", description.lower()))

    scored_list = []
    for idx, raw_kw in enumerate(keywords):
        kw = str(raw_kw).strip().lower()
        score = 0

        # 1. Exact or partial match with words in Title (+12 points: Primary subject)
        kw_parts = set(re.findall(r"\b[a-z0-9]+\b", kw))
        if kw in title.lower():
            score += 14
        elif kw_parts.intersection(title_words):
            score += 10

        # 2. Match with Description (+5 points)
        if kw_parts.intersection(desc_words):
            score += 5

        # 3. High-intent commercial buyer phrases (+8 points)
        if kw in HIGH_INTENT_BUYER_TERMS or any(term in kw for term in HIGH_INTENT_BUYER_TERMS):
            score += 8
        elif kw in SECONDARY_COMMERCIAL_TERMS:
            score += 4

        # 4. Multi-word phrase bonus (+2 points: long-tail buyer specificity)
        if " " in kw:
            score += 2

        # 5. Position preservation bias (preserves model's original subject focus)
        pos_bonus = max(0, 10 - (idx // 5))
        score += pos_bonus

        scored_list.append((score, idx, raw_kw))

    # Sort descending by score, ascending by original index for ties
    scored_list.sort(key=lambda x: (-x[0], x[1]))

    return [item[2] for item in scored_list]

