"""Perceptual Hashing (dHash 64-bit) & Visual Duplicate Guard.

Protects stock contributors from agency account warnings or rejections caused
by uploading visually near-identical compositions.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Tuple, Union
from PIL import Image


def compute_phash(image_input: Union[Image.Image, bytes]) -> str:
    """Compute a 64-bit Difference Hash (dHash) formatted as a 16-character hex string.
    
    1. Converts image to grayscale ('L').
    2. Resizes to 9x8 pixels (72 pixels) using Lanczos resampling.
    3. Computes brightness difference between adjacent pixels in each row (64 comparisons).
    4. Packs 64 booleans into a 64-bit integer and returns 16-char hex string.
    """
    if isinstance(image_input, bytes):
        with Image.open(io.BytesIO(image_input)) as im:
            return _compute_dhash_from_pillow(im)
    elif isinstance(image_input, Image.Image):
        return _compute_dhash_from_pillow(image_input)
    raise TypeError(f"Expected PIL Image or bytes, got {type(image_input)}")


def _compute_dhash_from_pillow(im: Image.Image) -> str:
    gray = im.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    diff = []
    for row in range(8):
        for col in range(8):
            diff.append(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    val = 0
    for b in diff:
        val = (val << 1) | int(b)
    return f"{val:016x}"


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two 16-character hex hashes (0 to 64)."""
    if not hash1 or not hash2 or len(hash1) != 16 or len(hash2) != 16:
        return 64
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        return bin(val1 ^ val2).count("1")
    except ValueError:
        return 64


def similarity_percent(hash1: str, hash2: str) -> float:
    """Return visual similarity percentage based on Hamming distance (100.0% = identical)."""
    dist = hamming_distance(hash1, hash2)
    return max(0.0, round((1.0 - (dist / 64.0)) * 100, 1))


def evaluate_duplicate_risk(
    candidate_hash: str,
    stored_items: List[Tuple[str, str]],  # List of (item_id_or_name, hash_hex)
    threshold_distance: int = 5,
) -> List[Dict[str, Any]]:
    """Scan candidate hash against a list of stored hashes.
    
    Threshold:
    - distance <= 3: High Risk (Near clone / scaled duplicate)
    - distance <= 5: Medium Risk (Very close angle / composition variation)
    - distance > 5: Low Risk / Safe
    """
    matches = []
    for identifier, stored_h in stored_items:
        dist = hamming_distance(candidate_hash, stored_h)
        if dist <= threshold_distance:
            sim = similarity_percent(candidate_hash, stored_h)
            risk_level = "HIGH" if dist <= 3 else "MEDIUM"
            matches.append({
                "target": identifier,
                "distance": dist,
                "similarity": sim,
                "risk": risk_level,
            })
    matches.sort(key=lambda x: x["distance"])
    return matches
