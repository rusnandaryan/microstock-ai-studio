"""Auto-Metadata Engine: Microstock-ready Title / Description / 50 Keywords."""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, List, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_async

# Adobe Stock category ids (official list used by the Adobe CSV "Category" column)
ADOBE_CATEGORIES = {
    1: "Animals", 2: "Buildings and Architecture", 3: "Business", 4: "Drinks",
    5: "The Environment", 6: "States of Mind", 7: "Food", 8: "Graphic Resources",
    9: "Hobbies and Leisure", 10: "Industry", 11: "Landscapes", 12: "Lifestyle",
    13: "People", 14: "Plants and Flowers", 15: "Culture and Religion", 16: "Science",
    17: "Social Issues", 18: "Sports", 19: "Technology", 20: "Transport", 21: "Travel",
}

# Adobe Stock Category Keywords Taxonomy for Deterministic Auto-Classification
ADOBE_CATEGORY_KEYWORDS: Dict[int, set] = {
    1: {"animal", "animals", "wildlife", "dog", "cat", "pet", "bird", "fish", "horse", "mammal", "fauna", "insect"},
    2: {"building", "architecture", "interior", "exterior", "house", "skyscraper", "facade", "urban", "room", "construction"},
    3: {"business", "office", "finance", "corporate", "money", "investment", "marketing", "work", "meeting", "economy"},
    4: {"drink", "drinks", "beverage", "coffee", "tea", "cocktail", "juice", "cup", "mug", "wine", "beer", "water", "smoothie"},
    5: {"environment", "climate", "ecology", "nature", "conservation", "pollution", "sustainability", "earth", "green energy"},
    6: {"emotion", "mood", "feeling", "thinking", "mind", "stress", "peace", "zen", "concept", "meditation", "dream"},
    7: {"food", "meal", "dish", "culinary", "restaurant", "breakfast", "dinner", "lunch", "snack", "bakery", "fruit", "vegetable", "dessert", "bread"},
    8: {"graphic", "resources", "texture", "pattern", "background", "abstract", "icon", "vector", "illustration", "banner", "frame", "element"},
    9: {"hobby", "leisure", "craft", "gaming", "music", "guitar", "painting", "reading", "gardening", "recreation"},
    10: {"industry", "factory", "manufacturing", "warehouse", "machinery", "engineering", "industrial", "steel", "oil"},
    11: {"landscape", "mountain", "ocean", "sea", "river", "forest", "desert", "sunset", "sunrise", "sky", "scenery", "valley"},
    12: {"lifestyle", "home", "daily", "wellness", "living", "family", "routine", "modern life", "relaxation", "cozy"},
    13: {"people", "person", "portrait", "hands", "crowd", "man", "woman", "human", "face", "gesture"},
    14: {"plant", "plants", "flower", "flowers", "botanical", "flora", "leaf", "leaves", "tree", "garden", "succulent"},
    15: {"culture", "religion", "tradition", "heritage", "ceremony", "festival", "temple", "spiritual", "cultural"},
    16: {"science", "laboratory", "chemistry", "physics", "biology", "research", "medical", "microscope", "healthcare"},
    17: {"social", "issues", "charity", "diversity", "community", "equality", "society", "volunteer", "activism"},
    18: {"sport", "sports", "fitness", "workout", "athlete", "running", "gym", "football", "soccer", "basketball", "training"},
    19: {"technology", "digital", "tech", "computer", "data", "cyber", "software", "network", "internet", "code", "ai", "hardware", "smartphone"},
    20: {"transport", "transportation", "car", "vehicle", "airplane", "flight", "train", "ship", "boat", "traffic", "road"},
    21: {"travel", "tourism", "vacation", "trip", "holiday", "destination", "landmark", "journey", "explore", "resort"},
}

# Shutterstock image categories
SHUTTERSTOCK_CATEGORIES = [
    "Abstract", "Animals/Wildlife", "Arts", "Backgrounds/Textures", "Beauty/Fashion",
    "Buildings/Landmarks", "Business/Finance", "Celebrities", "Education", "Food and drink",
    "Healthcare/Medical", "Holidays", "Industrial", "Interiors", "Miscellaneous", "Nature",
    "Objects", "Parks/Outdoor", "People", "Religion", "Science", "Signs/Symbols",
    "Sports/Recreation", "Technology", "Transportation", "Vintage",
]


def validate_adobe_category(val: Any) -> int:
    """Validate and normalize Adobe Stock category representation (returns int 1-21)."""
    if val is None:
        return config.DEFAULT_ADOBE_CATEGORY
    if isinstance(val, int) and 1 <= val <= 21:
        return val
    s = str(val).strip()
    if s.isdigit():
        num = int(s)
        if 1 <= num <= 21:
            return num
    # Match name
    s_lower = s.lower()
    for cat_id, cat_name in ADOBE_CATEGORIES.items():
        if cat_name.lower() == s_lower or s_lower in cat_name.lower():
            return cat_id
    return config.DEFAULT_ADOBE_CATEGORY


def classify_adobe_category(
    title: str,
    description: str,
    keywords: List[str],
) -> Tuple[int, str]:
    """Classify asset text and keywords into the best matching Adobe Stock category (1-21)."""
    text_corpus = f"{title} {description} {' '.join(keywords)}".lower()
    tokens = set(re.findall(r"\b[a-z]{3,}\b", text_corpus))

    scores: Dict[int, int] = {cat_id: 0 for cat_id in ADOBE_CATEGORIES}
    for cat_id, target_keywords in ADOBE_CATEGORY_KEYWORDS.items():
        overlap = tokens.intersection(target_keywords)
        title_lower = title.lower()
        title_bonus = sum(2 for kw in overlap if kw in title_lower)
        scores[cat_id] = len(overlap) + title_bonus

    best_cat_id = max(scores, key=lambda k: scores[k])
    if scores[best_cat_id] == 0:
        best_cat_id = config.DEFAULT_ADOBE_CATEGORY
    return best_cat_id, ADOBE_CATEGORIES[best_cat_id]


def classify_shutterstock_categories(
    title: str,
    description: str,
    keywords: List[str],
    max_cats: int = 2,
) -> List[str]:
    """Classify asset into 1 or 2 standard Shutterstock categories."""
    adobe_id, _ = classify_adobe_category(title, description, keywords)
    # Mapping Adobe categories to corresponding Shutterstock categories
    mapping: Dict[int, List[str]] = {
        1: ["Animals/Wildlife"],
        2: ["Buildings/Landmarks", "Interiors"],
        3: ["Business/Finance"],
        4: ["Food and drink"],
        5: ["Nature"],
        6: ["Abstract"],
        7: ["Food and drink"],
        8: ["Backgrounds/Textures", "Abstract"],
        9: ["Sports/Recreation", "Arts"],
        10: ["Industrial"],
        11: ["Nature", "Parks/Outdoor"],
        12: ["People"],
        13: ["People"],
        14: ["Nature"],
        15: ["Religion"],
        16: ["Science"],
        17: ["People"],
        18: ["Sports/Recreation"],
        19: ["Technology"],
        20: ["Transportation"],
        21: ["Parks/Outdoor", "Nature"],
    }
    cats = mapping.get(adobe_id, ["Objects", "Miscellaneous"])
    return cats[:max_cats]

METADATA_SYSTEM_INSTRUCTION = f"""\
You are a senior microstock SEO specialist with years of top-seller experience on
Adobe Stock and Shutterstock, strictly following the official Adobe Stock Generative AI Content Guidelines.

Produce metadata that maximizes commercial discoverability while adhering strictly to submission policies:

1. Title Rules (Adobe Stock Compliant):
- Compelling, natural-language, descriptive, max {config.TITLE_MAX_CHARS} characters.
- Clearly describe the primary subject, action, and setting.
- NO keyword stuffing, NO repetitive words, NO artist names, NO brand names/trademarks, NO trailing periods, NO quotes.

2. Description Rules:
- 1-3 sentences (150-200 characters ideal, max 200) clearly explaining the visual elements:
  subject, action, setting, mood, colors, style, and composition.
- If the style is an illustration, 3D render, or vector, explicitly declare it.

3. Keywords Rules (Strict Adobe Stock & Shutterstock Standard):
- EXACTLY {config.KEYWORD_COUNT} unique, lowercase, single words or short 2-word phrases.
- Sorted strictly by relevance: First 10 keywords MUST be the most critical, primary subject terms.
- Proceed from BROAD concepts to SPECIFIC niche details.
- Include: subject, action, concept, emotion, setting, color, composition, and commercial buyer use-cases.
- ZERO TOLERANCE: NO brand names (e.g. no iPhone, Lego, Nike), NO artist names (e.g. no Picasso, Van Gogh),
  NO celebrity/notable names, NO camera model names, NO irrelevant spam, NO hashtags, NO duplicate singular/plural pairs.
- NEVER mention "AI", "generative AI", "artificial intelligence", "generated", "Gemini", or "prompt" in title, description, or keywords (agencies use checkboxes for AI disclosure; putting AI in metadata is penalized as keyword spam).

4. Categories:
- adobe_category: the single best Adobe Stock category id.
- shutterstock_categories: 1 or 2 best Shutterstock categories.
"""

METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Max 100 characters."},
        "description": {"type": "string"},
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "50 unique keywords, broad to specific.",
        },
        "adobe_category": {
            "type": "integer",
            "description": "Single best Adobe Stock category id (integer 1-21).",
        },
        "shutterstock_categories": {
            "type": "array",
            "items": {"type": "string", "enum": SHUTTERSTOCK_CATEGORIES},
            "description": "1 or 2 best Shutterstock categories.",
        },
    },
    "required": ["title", "description", "keywords", "adobe_category", "shutterstock_categories"],
}

SUPPLEMENT_SCHEMA = {
    "type": "object",
    "properties": {"keywords": {"type": "array", "items": {"type": "string"}}},
    "required": ["keywords"],
}

TOPUP_SYSTEM_INSTRUCTION = """\
You are a senior microstock SEO specialist. Return ONLY a JSON object containing additional unique, relevant, lowercase keywords based on the image and existing keywords list.
"""


@dataclass
class ImageMetadata:
    title: str
    description: str
    keywords: List[str] = field(default_factory=list)
    adobe_category: int = config.DEFAULT_ADOBE_CATEGORY
    shutterstock_categories: List[str] = field(default_factory=list)

    def __post_init__(self):
        from .keyword_ranker import rank_keywords_by_buyer_intent
        self.adobe_category = validate_adobe_category(self.adobe_category)
        if not self.shutterstock_categories:
            self.shutterstock_categories = classify_shutterstock_categories(
                self.title, self.description, self.keywords
            )
        if self.keywords:
            self.keywords = rank_keywords_by_buyer_intent(self.keywords, self.title, self.description)

    @property
    def keywords_csv(self) -> str:
        return ", ".join(self.keywords)

    @property
    def adobe_category_name(self) -> str:
        return ADOBE_CATEGORIES.get(self.adobe_category, "")

    def to_dict(self) -> dict:
        return asdict(self)


_BANNED = {"ai", "ai generated", "ai-generated", "generated", "gemini", "prompt", "generative ai"}


def _clean_keyword(kw: str) -> str:
    kw = re.sub(r"[#\"'`]", "", str(kw)).replace(",", " ").strip().lower()
    return re.sub(r"\s+", " ", kw)


def _get_stem(k: str) -> str:
    if len(k) <= 3:
        return k
    if k.endswith(("sses", "shes", "ches", "xes")):
        return k[:-2]
    if k.endswith("ies") and len(k) > 4:
        return k[:-3] + "y"
    if k.endswith("s") and not k.endswith(("ss", "us", "is")):
        return k[:-1]
    return k


def normalize_keywords(raw: List[str]) -> List[str]:
    """Lowercase, strip, de-duplicate (incl. singular/plural duplicates), keep order."""
    seen: set = set()
    out: List[str] = []
    for kw in raw:
        k = _clean_keyword(kw)
        if not k or k in _BANNED:
            continue
        stem = _get_stem(k)
        if k in seen or stem in seen:
            continue
        seen.update({k, stem})
        out.append(k)
    return out


def clamp_title(title: str, limit: int = config.TITLE_MAX_CHARS) -> str:
    title = re.sub(r"\s+", " ", title.strip().strip('"').strip()).rstrip(".")
    if len(title) <= limit:
        return title
    cut = title[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:-– ")


def clamp_description(desc: str, limit: int = 200) -> str:
    desc = re.sub(r"\s+", " ", desc.strip().strip('"').strip())
    if len(desc) <= limit:
        return desc
    cut = desc[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-– ")
    return cut + "."


def create_fallback_metadata(filename: str) -> ImageMetadata:
    """Create basic microstock metadata from filename when Gemini Vision fails."""
    clean_title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip().title()
    title = clean_title or "Commercial Microstock Asset"
    keywords = [w.lower() for w in clean_title.split() if len(w) > 2] + [
        "stock", "commercial", "concept", "isolated", "quality", "modern"
    ]
    return ImageMetadata(
        title=title,
        description=f"High quality commercial microstock asset: {title}.",
        keywords=normalize_keywords(keywords),
        adobe_category=config.DEFAULT_ADOBE_CATEGORY,
        shutterstock_categories=["Objects", "Miscellaneous"],
    )


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    elif not (text.startswith("{") and text.endswith("}")):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TransientError(f"Malformed JSON from model: {exc}") from exc
    if not isinstance(data, dict):
        raise TransientError("Model returned non-object JSON")
    return data


def _prepare_vision_bytes(raw_bytes: bytes, orig_mime: str) -> tuple[bytes, str]:
    """Sanitize, normalize, and compress image to guaranteed RGB JPEG under 2048px.
    
    Protects against:
    - Invalid MIME types (e.g. image/jpg, image/pjpeg) -> normalized to 'image/jpeg'
    - Large inline payloads (> 20MB limit in Gemini API) -> compressed to < 1.5MB
    - Unsupported color modes (RGBA, CMYK, P, 16-bit) -> converted to standard RGB
    - Corrupt EXIF or non-standard JPEG headers
    """
    import io
    from PIL import Image

    try:
        with Image.open(io.BytesIO(raw_bytes)) as im:
            if im.mode != "RGB":
                im = im.convert("RGB")
            # Downscale for vision analysis if larger than 2048px (Gemini Vision needs max 1536-2048px)
            max_side = max(im.size)
            if max_side > 2048:
                im.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=90, optimize=True)
            return buf.getvalue(), "image/jpeg"
    except Exception:
        mime = (orig_mime or "").lower().strip()
        if mime in ("image/jpg", "image/pjpeg", ""):
            mime = "image/jpeg"
        elif mime == "image/x-png":
            mime = "image/png"
        return raw_bytes, mime


def _create_json(client: genai.Client, system_instruction: str, contents: Any, schema: dict) -> dict:
    last_err = None
    for model_name in config.TEXT_MODEL_FALLBACKS:
        try:
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                from google.genai import types
                cfg = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.3,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=cfg,
                )
                parsed = _parse_json(response.text or "")
                if parsed:
                    return parsed
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if any(term in err_str for term in (
                "503", "unavailable", "high demand", "404", "not found",
                "400", "invalid_argument", "invalid argument",
                "429", "quota", "resource_exhausted", "rate limit",
                "malformed json", "empty json",
            )):
                continue
            raise

    if last_err:
        raise last_err
    raise TransientError("Empty JSON response from metadata model")


async def generate_metadata_from_vision_async(
    client: genai.Client,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    label: str = "Vision Metadata",
    on_retry: Optional[Callable[[str], None]] = None,
) -> ImageMetadata:
    """Inspect actual image pixels via Gemini Vision to create 100% accurate microstock metadata."""
    from google.genai import types
    safe_bytes, safe_mime = _prepare_vision_bytes(image_bytes, mime_type)
    image_part = types.Part.from_bytes(data=safe_bytes, mime_type=safe_mime)
    vision_prompt = (
        "Carefully analyze all visible elements in this image:\n"
        "- Subject (who/what, appearance, expression, action, clothing, props)\n"
        "- Environment & background (setting, interior/exterior, textures, lighting, shadows, colors)\n"
        "- Artistic medium / style (commercial photography, 3D render, flat vector, watercolor, etc.)\n"
        "- Commercial stock concepts and potential buyer use-cases\n\n"
        "Generate compliant, high-ranking microstock Title, Description, and EXACTLY 50 Keywords based on what is genuinely visible."
    )
    contents = [image_part, vision_prompt]

    data = await retry_async(
        lambda: asyncio.to_thread(_create_json, client, METADATA_SYSTEM_INSTRUCTION, contents, METADATA_SCHEMA),
        label=label, on_retry=on_retry,
    )

    keywords = normalize_keywords(data.get("keywords", []))

    # Top-up pass if needed
    for _ in range(2):
        if len(keywords) >= config.KEYWORD_COUNT:
            break
        missing = config.KEYWORD_COUNT - len(keywords)
        sup_prompt = (
            f"Existing keywords: {', '.join(keywords)}\n"
            f"Based on this image, return {missing + 8} NEW, unique, relevant, lowercase keywords."
        )
        try:
            extra = await retry_async(
                lambda: asyncio.to_thread(
                    _create_json, client, TOPUP_SYSTEM_INSTRUCTION, [image_part, sup_prompt], SUPPLEMENT_SCHEMA),
                label=f"{label} (top-up)", on_retry=on_retry,
            )
            keywords = normalize_keywords(keywords + list(extra.get("keywords", [])))
        except Exception:
            break

    raw_cat = data.get("adobe_category", config.DEFAULT_ADOBE_CATEGORY)
    try:
        adobe_cat = int(raw_cat)
    except (ValueError, TypeError):
        name_map = {name.lower(): cid for cid, name in ADOBE_CATEGORIES.items()}
        adobe_cat = name_map.get(str(raw_cat).strip().lower(), config.DEFAULT_ADOBE_CATEGORY)

    if adobe_cat not in ADOBE_CATEGORIES:
        adobe_cat = config.DEFAULT_ADOBE_CATEGORY

    ss_cats = [c for c in data.get("shutterstock_categories", []) if c in SHUTTERSTOCK_CATEGORIES][:2]

    return ImageMetadata(
        title=clamp_title(data.get("title", "")),
        description=clamp_description(str(data.get("description", ""))),
        keywords=keywords[: config.KEYWORD_COUNT],
        adobe_category=int(adobe_cat),
        shutterstock_categories=ss_cats or ["Miscellaneous"],
    )
