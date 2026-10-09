"""API configuration, model registry and static option tables.

Everything that is "configuration" (model names, style presets, aspect-ratio
mappings, concurrency defaults) lives here so the rest of the code base stays
free of magic strings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from google import genai

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
# Text models for prompt enhancement & metadata SEO (with fallbacks if 503 high demand)
TEXT_MODEL = "gemini-3.1-flash-lite"
TEXT_MODEL_FALLBACKS = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
]

# Image models: Google Gemini Nano Banana & Imagen models
IMAGE_MODELS: Dict[str, str] = {
    "Gemini 3.1 Flash Lite Image (Nano Banana 2 Lite · Hemat Kuota Free Tier)": "gemini-3.1-flash-lite-image",
    "Gemini 3.1 Flash Image (Nano Banana 2 · Kualitas Tinggi)": "gemini-3.1-flash-image",
    "Gemini 3 Pro Image (Nano Banana Pro)": "gemini-3-pro-image",
    "Imagen 4 (imagen-4.0-generate-001)": "imagen-4.0-generate-001",
    "Pollinations AI (Alternatif Bebas Kuota)": "pollinations",
}
DEFAULT_IMAGE_MODEL_LABEL = "Gemini 3.1 Flash Lite Image (Nano Banana 2 Lite · Hemat Kuota Free Tier)"

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# Supported `image_size` values, highest first.
IMAGE_SIZES = ["4K", "2K", "1K"]
DEFAULT_IMAGE_SIZE = "1K"

# --------------------------------------------------------------------------- #
# Microstock Resolution Standards (Adobe Stock & Shutterstock Requirements)
# Minimum: 4 Megapixels (MP)
# Maximum: 100 Megapixels (MP)
# --------------------------------------------------------------------------- #
MIN_IMAGE_MEGAPIXELS = 4.0
MAX_IMAGE_MEGAPIXELS = 100.0
TARGET_MIN_PIXELS = 4_200_000  # Safe upscale target (e.g. 2050x2050) to guarantee >= 4MP

# --------------------------------------------------------------------------- #
# Aspect ratios -> API value + resulting pixel dimensions (per image_size)
# Source: Gemini image-generation docs (3.1 Flash Image / 3 Pro Image tables).
# --------------------------------------------------------------------------- #
ASPECT_RATIOS: Dict[str, Dict[str, str]] = {
    "1:1": {"1K": "1024x1024", "2K": "2048x2048", "4K": "4096x4096"},
    "9:16": {"1K": "768x1376", "2K": "1536x2752", "4K": "3072x5504"},
    "16:9": {"1K": "1376x768", "2K": "2752x1536", "4K": "5504x3072"},
    "4:3": {"1K": "1200x896", "2K": "2400x1792", "4K": "4800x3584"},
    "3:4": {"1K": "896x1200", "2K": "1792x2400", "4K": "3584x4800"},
}
ASPECT_RATIO_LABELS: Dict[str, str] = {
    "1:1": "1:1 · Square",
    "9:16": "9:16 · Vertical / Stories",
    "16:9": "16:9 · Widescreen / Banner",
    "4:3": "4:3 · Classic Landscape",
    "3:4": "3:4 · Classic Portrait",
}


def dimensions_for(aspect_ratio: str, image_size: str) -> str:
    """Return expected output dimensions, e.g. '5504x3072'."""
    return ASPECT_RATIOS.get(aspect_ratio, {}).get(image_size, "unknown")


# --------------------------------------------------------------------------- #
# Aesthetic / style presets
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StylePreset:
    name: str
    directive: str          # injected into the image prompt
    is_illustration: bool


# --------------------------------------------------------------------------- #
# Aesthetic / style presets (Expanded library of 18 high-demand microstock styles)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StylePreset:
    name: str
    directive: str          # injected into the image prompt
    is_illustration: bool


STYLES: Dict[str, StylePreset] = {
    "📷 Commercial Stock Photography": StylePreset(
        name="📷 Commercial Stock Photography",
        directive=(
            "Commercial stock photography, shot on Hasselblad H6D-100c with prime lens, "
            "crisp clean focus, professional studio or authentic environmental lighting, "
            "true-to-life colors, clean composition with negative space for copy, "
            "authentic candid feel, highest commercial advertising quality, no watermarks, no logos."
        ),
        is_illustration=False,
    ),
    "🍽️ Food & Beverage Editorial": StylePreset(
        name="🍽️ Food & Beverage Editorial",
        directive=(
            "High-end culinary editorial photography, appetizing presentation, fresh textures, "
            "glistening highlights, shallow depth of field, rustic tabletop surfaces, "
            "directional side window lighting, natural garnish, mouth-watering restaurant grade."
        ),
        is_illustration=False,
    ),
    "📦 Overhead Flat Lay / Product": StylePreset(
        name="📦 Overhead Flat Lay / Product",
        directive=(
            "Organized overhead knolling flat lay photograph, top-down 90 degree perspective, "
            "neatly arranged elements with precise spacing, clean matte pastel background, "
            "diffused even lighting without harsh shadows, generous blank negative space for text."
        ),
        is_illustration=False,
    ),
    "💼 Modern Workplace & Corporate": StylePreset(
        name="💼 Modern Workplace & Corporate",
        directive=(
            "Authentic modern corporate lifestyle photography, diverse team in bright contemporary office, "
            "natural collaborative moments, floor-to-ceiling glass windows, warm natural daylight, "
            "subtle cinematic depth of field, professional business casual attire."
        ),
        is_illustration=False,
    ),
    "🔍 Cinematic Macro Photography": StylePreset(
        name="🔍 Cinematic Macro Photography",
        directive=(
            "Cinematic macro photograph, 100mm macro lens, extreme close-up revealing intricate fine textures, "
            "micro details, razor-thin focal plane with dreamy creamy bokeh, directional rim lighting, "
            "high dynamic range, tack-sharp focal point."
        ),
        is_illustration=False,
    ),
    "🏛️ Architectural & Interior Editorial": StylePreset(
        name="🏛️ Architectural & Interior Editorial",
        directive=(
            "Architectural Digest style interior photography, wide tilt-shift lens, straight vertical lines, "
            "airy minimalist scandinavian aesthetic, beautiful natural ambient lighting, stylish designer furniture, "
            "balanced symmetry, peaceful atmosphere."
        ),
        is_illustration=False,
    ),
    "🎞️ Vintage 35mm Retro Film": StylePreset(
        name="🎞️ Vintage 35mm Retro Film",
        directive=(
            "Authentic 35mm film photography, Kodak Portra 400 aesthetic, organic film grain, warm nostalgic tones, "
            "soft halation on highlights, natural lens flare, timeless storytelling vibe, rich shadows."
        ),
        is_illustration=False,
    ),
    "🧸 3D Claymation & Tactile": StylePreset(
        name="🧸 3D Claymation & Tactile",
        directive=(
            "Charming tactile claymation 3D render, handmade plasticine clay texture with subtle fingerprints, "
            "soft rounded shapes, cute stylized characters, warm studio softbox lighting, gentle ambient occlusion."
        ),
        is_illustration=True,
    ),
    "💎 Polished 3D Octane / Blender": StylePreset(
        name="💎 Polished 3D Octane / Blender",
        directive=(
            "High-end 3D isometric render, Octane Render engine, physically based materials, subsurface scattering, "
            "glass and metallic reflections, studio rim lights, hyper-detailed clean composition, premium aesthetic."
        ),
        is_illustration=True,
    ),
    "📐 Isometric 3D Diorama": StylePreset(
        name="📐 Isometric 3D Diorama",
        directive=(
            "Isometric 3D diorama illustration, clean 30-degree isometric projection, tidy miniature scene, "
            "vibrant harmonious color scheme, soft drop shadows, clean geometric forms, tech or lifestyle theme."
        ),
        is_illustration=True,
    ),
    "🎨 Clean Flat Vector & Icons": StylePreset(
        name="🎨 Clean Flat Vector & Icons",
        directive=(
            "Modern flat vector illustration, Behance / Dribbble trending, harmonious curated color palette, "
            "clean geometric shapes, smooth clean edges, minimal aesthetic, generous padding, versatile commercial look."
        ),
        is_illustration=True,
    ),
    "✏️ Minimalist Continuous Line Art": StylePreset(
        name="✏️ Minimalist Continuous Line Art",
        directive=(
            "Minimalist single-line art, fluid continuous black ink stroke on warm off-white canvas, "
            "elegant abstract forms, subtle earthy watercolor washes, abundant negative space, refined and chic."
        ),
        is_illustration=True,
    ),
    "💥 2D Expressive Comic & Pop Art": StylePreset(
        name="💥 2D Expressive Comic & Pop Art",
        directive=(
            "Dynamic 2D expressive comic illustration, bold black ink outlines, cel shading, halftone dot pattern, "
            "vibrant high-contrast primary colors, energetic action lines, expressive character design."
        ),
        is_illustration=True,
    ),
    "📄 Layered Papercraft & Cutout": StylePreset(
        name="📄 Layered Papercraft & Cutout",
        directive=(
            "Intricate layered papercraft art, paper cutout sculpture, multi-layered depth with realistic soft shadows, "
            "textured craft paper materials, pastel and vibrant gradients, creative artisanal craftsmanship."
        ),
        is_illustration=True,
    ),
    "🖌️ Watercolor & Gouache Artistic": StylePreset(
        name="🖌️ Watercolor & Gouache Artistic",
        directive=(
            "Expressive loose watercolor and gouache painting, visible wet-on-wet paint bleeds, rough cold-press paper texture, "
            "soft translucent washes, artistic splatter details, evocative emotional mood."
        ),
        is_illustration=True,
    ),
    "🌃 Cyberpunk & Futuristic Neon": StylePreset(
        name="🌃 Cyberpunk & Futuristic Neon",
        directive=(
            "Futuristic cyberpunk aesthetic, glowing neon cyan and magenta rim lighting, rainy reflective surfaces, "
            "holographic displays, dark moody atmosphere, ultra-detailed sci-fi technology, cinematic contrast."
        ),
        is_illustration=False,
    ),
    "🌸 Pastel Kawaii Mascot Design": StylePreset(
        name="🌸 Pastel Kawaii Mascot Design",
        directive=(
            "Adorable kawaii character mascot, soft pastel color palette (pink, mint, lavender), chubby rounded forms, "
            "sparkling expressive eyes, cheerful friendly expression, clean cute stickers style."
        ),
        is_illustration=True,
    ),
}
DEFAULT_STYLE = "📷 Commercial Stock Photography"

# Lighting Conditions
LIGHTING_OPTIONS = {
    "Natural Soft Daylight": "Natural soft daylight, gentle diffused shadows, luminous and airy feel.",
    "Golden Hour / Warm Sunset": "Warm golden hour sunlight, low sun angle, rich amber glow, long soft shadows.",
    "Studio Softbox (Clean Commercial)": "Professional multi-point studio softbox lighting, perfectly balanced exposure, crisp highlights.",
    "Dramatic Rim Lighting": "Dramatic directional rim lighting, sharp edge contours, dark moody background.",
    "High Key (Pure Bright White)": "Bright high-key lighting, clean white luminous ambiance, minimal shadows, commercial catalog look.",
    "Moody Chiaroscuro (Dark & Moody)": "Moody chiaroscuro lighting, deep rich shadows, selective beam of spotlight, fine art editorial feel.",
}
DEFAULT_LIGHTING = "Studio Softbox (Clean Commercial)"

# Camera Framing & Lenses
CAMERA_OPTIONS = {
    "85mm Prime (Portrait Bokeh)": "Shot on 85mm f/1.4 prime lens, sharp subject with soft creamy background bokeh.",
    "35mm Street (Authentic Environmental)": "Shot on 35mm f/2 lens, natural field of view showing surrounding environment candidly.",
    "100mm Macro (Extreme Detail)": "100mm macro lens, tack-sharp micro details, shallow focal plane.",
    "24mm Wide Angle (Expansive Scene)": "24mm wide angle lens, expansive perspective, strong sense of scale and atmosphere.",
    "Top-Down Overhead Flat Lay": "Straight-down 90-degree flat lay angle, perfectly planar and geometric.",
}
DEFAULT_CAMERA = "85mm Prime (Portrait Bokeh)"

# Composition Types
COMPOSITION_OPTIONS = {
    "Negative Space for Copy / Headline": "Clean composition with generous empty negative space dedicated for advertising text and copy.",
    "Centered Hero Framing": "Centered focal point, powerful hero framing, immediate visual impact.",
    "Rule of Thirds (Left-Aligned)": "Rule-of-thirds composition, primary focal subject positioned on the left third with breathing room on the right.",
    "Rule of Thirds (Right-Aligned)": "Rule-of-thirds composition, primary focal subject positioned on the right third with breathing room on the left.",
    "Balanced Symmetry": "Symmetrical architectural composition, harmonious balance, clean linear perspective.",
}
DEFAULT_COMPOSITION = "Negative Space for Copy / Headline"

# --------------------------------------------------------------------------- #
# Concurrency / rate limiting defaults
# --------------------------------------------------------------------------- #
DEFAULT_MAX_CONCURRENCY = 1
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 60.0

TITLE_MAX_CHARS = 100
KEYWORD_COUNT = 50


# --------------------------------------------------------------------------- #
# Client factory
# --------------------------------------------------------------------------- #
def get_env_file_path() -> str:
    """Return absolute path to .env file in the project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, ".env")


def load_saved_api_key() -> Optional[str]:
    """Read saved GEMINI_API_KEY from local .env file or environment."""
    env_path = get_env_file_path()
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def save_api_key(api_key: str) -> None:
    """Save GEMINI_API_KEY to local .env file."""
    api_key = api_key.strip()
    if not api_key:
        return
    env_path = get_env_file_path()
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    lines.append(f'GEMINI_API_KEY="{api_key}"\n')
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f'GEMINI_API_KEY="{api_key}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ["GEMINI_API_KEY"] = api_key


def delete_saved_api_key() -> None:
    """Remove GEMINI_API_KEY from local .env file and environment."""
    env_path = get_env_file_path()
    if os.path.exists(env_path):
        lines = []
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip().startswith("GEMINI_API_KEY="):
                    lines.append(line)
        if any(line.strip() for line in lines):
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        else:
            try:
                os.remove(env_path)
            except Exception:
                pass
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)


def resolve_api_key(user_supplied: Optional[str] = None) -> Optional[str]:
    """Priority: user input > saved .env > Streamlit secrets > environment variables."""
    if user_supplied and user_supplied.strip():
        return user_supplied.strip()
    saved = load_saved_api_key()
    if saved:
        return saved
    try:
        import streamlit as st  # local import keeps this module UI-agnostic
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            if key in st.secrets:
                return str(st.secrets[key])
    except Exception:
        pass
    return None


def resolve_hf_api_key(user_supplied: Optional[str] = None) -> Optional[str]:
    """Resolve Hugging Face API key."""
    if user_supplied and user_supplied.strip():
        return user_supplied.strip()
    try:
        import streamlit as st
        if "HF_API_TOKEN" in st.secrets:
            return str(st.secrets["HF_API_TOKEN"])
    except Exception:
        pass
    return HF_API_TOKEN


def get_client(api_key: str) -> genai.Client:
    """Create a Gemini client. The sync client is thread-safe and is driven
    concurrently via `asyncio.to_thread` in the batch engine."""
    if not api_key:
        raise ValueError("A Gemini API key is required.")
    return genai.Client(api_key=api_key)
