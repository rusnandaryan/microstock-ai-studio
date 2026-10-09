"""Auto-Metadata Engine: Microstock-ready Title / Description / 50 Keywords."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, List, Optional

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

# Shutterstock image categories
SHUTTERSTOCK_CATEGORIES = [
    "Abstract", "Animals/Wildlife", "Arts", "Backgrounds/Textures", "Beauty/Fashion",
    "Buildings/Landmarks", "Business/Finance", "Celebrities", "Education", "Food and drink",
    "Healthcare/Medical", "Holidays", "Industrial", "Interiors", "Miscellaneous", "Nature",
    "Objects", "Parks/Outdoor", "People", "Religion", "Science", "Signs/Symbols",
    "Sports/Recreation", "Technology", "Transportation", "Vintage",
]

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
            "minItems": config.KEYWORD_COUNT,
            "maxItems": config.KEYWORD_COUNT,
            "description": "Exactly 50 keywords, broad to specific.",
        },
        "adobe_category": {"type": "string", "enum": [str(k) for k in ADOBE_CATEGORIES.keys()]},
        "shutterstock_categories": {
            "type": "array",
            "items": {"type": "string", "enum": SHUTTERSTOCK_CATEGORIES},
            "minItems": 1,
            "maxItems": 2,
        },
    },
    "required": ["title", "description", "keywords", "adobe_category", "shutterstock_categories"],
}

SUPPLEMENT_SCHEMA = {
    "type": "object",
    "properties": {"keywords": {"type": "array", "items": {"type": "string"}}},
    "required": ["keywords"],
}


@dataclass
class ImageMetadata:
    title: str
    description: str
    keywords: List[str] = field(default_factory=list)
    adobe_category: int = 8
    shutterstock_categories: List[str] = field(default_factory=list)

    @property
    def keywords_csv(self) -> str:
        return ", ".join(self.keywords)

    @property
    def adobe_category_name(self) -> str:
        return ADOBE_CATEGORIES.get(self.adobe_category, "")

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Normalisation / validation helpers
# --------------------------------------------------------------------------- #
_BANNED = {"ai", "ai generated", "ai-generated", "generated", "gemini", "prompt", "generative ai"}


def _clean_keyword(kw: str) -> str:
    kw = re.sub(r"[#\"'`]", "", str(kw)).replace(",", " ").strip().lower()
    return re.sub(r"\s+", " ", kw)


def normalize_keywords(raw: List[str]) -> List[str]:
    """Lowercase, strip, de-duplicate (incl. naive plural duplicates), keep order."""
    seen: set = set()
    out: List[str] = []
    for kw in raw:
        k = _clean_keyword(kw)
        if not k or k in _BANNED:
            continue
        stem = k[:-1] if k.endswith("s") and len(k) > 3 else k
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


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TransientError(f"Malformed JSON from model: {exc}") from exc
    if not isinstance(data, dict):
        raise TransientError("Model returned non-object JSON")
    return data


# --------------------------------------------------------------------------- #
# Gemini calls
# --------------------------------------------------------------------------- #
def build_metadata_input(enhanced_prompt: str, style_name: str, variation: str) -> str:
    style = config.STYLES[style_name]
    kind = "illustration / digital artwork" if style.is_illustration else "photograph"
    return (
        "Create microstock metadata for the following image.\n\n"
        f"IMAGE PROMPT (what the image depicts):\n{enhanced_prompt}\n\n"
        f"VARIATION / COMPOSITION: {variation}\n"
        f"AESTHETIC STYLE: {style.name} ({kind}) — {style.directive}\n"
    )


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
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=cfg,
                )
                parsed = _parse_json(response.text or "")
                if parsed:
                    return parsed
            elif hasattr(client, "interactions"):
                prompt_text = contents if isinstance(contents, str) else str(contents)
                interaction = client.interactions.create(
                    model=model_name,
                    system_instruction=system_instruction,
                    input=prompt_text,
                    response_format={"type": "text", "mime_type": "application/json", "schema": schema},
                    store=False,
                )
                parsed = _parse_json(interaction.output_text or "")
                if parsed:
                    return parsed
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "404" in err_str:
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
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
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
                    _create_json, client, METADATA_SYSTEM_INSTRUCTION, [image_part, sup_prompt], SUPPLEMENT_SCHEMA),
                label=f"{label} (top-up)", on_retry=on_retry,
            )
            keywords = normalize_keywords(keywords + list(extra.get("keywords", [])))
        except Exception:
            break

    try:
        adobe_cat = int(data.get("adobe_category", 12))
    except (ValueError, TypeError):
        adobe_cat = 12

    if adobe_cat not in ADOBE_CATEGORIES:
        adobe_cat = 12

    ss_cats = [c for c in data.get("shutterstock_categories", []) if c in SHUTTERSTOCK_CATEGORIES][:2]

    return ImageMetadata(
        title=clamp_title(data.get("title", "")),
        description=clamp_description(str(data.get("description", ""))),
        keywords=keywords[: config.KEYWORD_COUNT],
        adobe_category=int(adobe_cat),
        shutterstock_categories=ss_cats or ["Miscellaneous"],
    )


async def generate_metadata_async(
    client: genai.Client,
    enhanced_prompt: str,
    style_name: str,
    variation: str,
    label: str = "Metadata",
    on_retry: Optional[Callable[[str], None]] = None,
) -> ImageMetadata:
    """Generate + validate metadata from prompt text."""
    prompt = build_metadata_input(enhanced_prompt, style_name, variation)

    data = await retry_async(
        lambda: asyncio.to_thread(_create_json, client, METADATA_SYSTEM_INSTRUCTION, prompt, METADATA_SCHEMA),
        label=label, on_retry=on_retry,
    )

    keywords = normalize_keywords(data.get("keywords", []))

    # Top-up pass if de-duplication left us short of 50 (max 2 attempts)
    for _ in range(2):
        if len(keywords) >= config.KEYWORD_COUNT:
            break
        missing = config.KEYWORD_COUNT - len(keywords)
        sup_prompt = (
            f"{prompt}\nExisting keywords (do NOT repeat any of these): {', '.join(keywords)}\n"
            f"Return {missing + 8} NEW, unique, relevant, lowercase keywords, most relevant first."
        )
        try:
            extra = await retry_async(
                lambda: asyncio.to_thread(
                    _create_json, client, METADATA_SYSTEM_INSTRUCTION, sup_prompt, SUPPLEMENT_SCHEMA),
                label=f"{label} (keyword top-up)", on_retry=on_retry,
            )
            keywords = normalize_keywords(keywords + list(extra.get("keywords", [])))
        except Exception:  # noqa: BLE001 - best effort
            break

    try:
        adobe_cat = int(data.get("adobe_category", 0))
    except (ValueError, TypeError):
        adobe_cat = 0

    if adobe_cat not in ADOBE_CATEGORIES:
        adobe_cat = 8 if config.STYLES[style_name].is_illustration else 12
    ss_cats = [c for c in data.get("shutterstock_categories", []) if c in SHUTTERSTOCK_CATEGORIES][:2]

    return ImageMetadata(
        title=clamp_title(data.get("title", "")),
        description=clamp_description(str(data.get("description", ""))),
        keywords=keywords[: config.KEYWORD_COUNT],
        adobe_category=int(adobe_cat),
        shutterstock_categories=ss_cats or ["Miscellaneous"],
    )
