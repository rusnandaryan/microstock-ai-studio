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
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]

# Image models: Google Gemini Nano Banana & Imagen models
IMAGE_MODELS: Dict[str, str] = {
    "Gemini 3.1 Flash Lite Image (Nano Banana 2 Lite · Hemat Kuota Free Tier)": "gemini-3.1-flash-lite-image",
    "Gemini Nano Banana 2.1 (Nano Banana 2.1 · Kualitas Tinggi)": "gemini-nano-banana-2.1",
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
MIN_FILE_SIZE_BYTES = 4_194_304  # 4 MB (4 * 1024 * 1024 bytes) for sites like Freepik / Vecteezy

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


STYLE_CATEGORIES: Dict[str, List[str]] = {
    "Fotografi (Photorealism)": [
        "📷 Foto Komersial Bersih (Commercial Advertising)",
        "📰 Foto Dokumenter & Human Interest",
        "🔍 Macro Photography (Extreme Detail)",
        "👤 Portrait Studio Faceless",
        "🚶 Street Photography Candid",
        "🎞️ Sinematik Film 35mm Retro",
        "🍽️ Food & Culinary Editorial",
        "🏛️ Arsitektur & Interior Minimalis",
    ],
    "Ilustrasi & Seni Lukis": [
        "🖌️ Cat Air & Gouache (Watercolor)",
        "🎨 Cat Minyak Klasik (Oil Painting)",
        "✏️ Sketsa Pensil & Arang (Pencil Sketch)",
        "🎭 Impresionisme Bertekstur (Impressionism)",
        "🌌 Surealisme Modern (Surrealism)",
        "🌀 Seni Abstrak Kontemporer (Abstract Art)",
        "✂️ Ilustrasi Stiker Die-Cut (Die-Cut Sticker)",
    ],
    "Animasi & Kartun": [
        "🌸 Pastel Kawaii Mascot Design",
        "⛩️ Anime Jepang Kontemporer",
        "📖 Manga Tinta Hitam Putih (Ink Manga)",
        "👶 Chibi & Karakter Imut (Cute Chibi)",
        "📺 Kartun Klasik Retro (Classic Toon)",
        "💥 Komik Pop Art (Comic Book & Halftone)",
        "🍃 Whimsical Studio Anime (Ghibli-Inspired Aesthetic)",
        "🧸 3D Animated Feature (Pixar-Inspired Stylized CGI)",
    ],
    "3D & Render": [
        "🏝️ 3D Miniature Diorama (Miniature World)",
        "🧊 3D Commercial Studio Render",
        "📐 3D Isometric Illustration (Tech & Business)",
        "🧱 3D Claymation (Tanah Liat Taktil)",
        "🔷 Low-Poly 3D Minimalist",
        "✨ Octane Render Photorealistic (CGI Ultra-Detail)",
        "🪟 3D Glassmorphism & Akrilik Transparan",
    ],
    "Desain & Digital Art": [
        "🏷️ Paket Stiker Die-Cut (Die-Cut Sticker Pack)",
        "📱 Icon Desain Aplikasi & Web (App Icon Set)",
        "📄 Flat Design Vector Minimalist",
        "🔶 Logo Monogram & Geometris",
        "🌃 Cyberpunk & Futuristic Neon",
        "⚙️ Steampunk Vintage Mekanikal",
        "📼 Synthwave & Retrowave 80s",
        "👾 Pixel Art Klasik 16-bit",
        "🧙 Digital Concept Art Fantasi & Sci-Fi",
    ],
}

STYLES: Dict[str, StylePreset] = {
    # 1. Fotografi
    "📷 Foto Komersial Bersih (Commercial Advertising)": StylePreset(
        name="📷 Foto Komersial Bersih",
        directive=(
            "Commercial advertising stock photography, shot on Hasselblad H6D-100c prime lens, "
            "tack-sharp focus, professional studio multi-point balanced lighting, vibrant true-to-life colors, "
            "highest commercial quality, zero artifacts, pristine clean atmosphere."
        ),
        is_illustration=False,
    ),
    "📰 Foto Dokumenter & Human Interest": StylePreset(
        name="📰 Foto Dokumenter & Human Interest",
        directive=(
            "Authentic photojournalistic documentary style, environmental natural light, candid human moment, "
            "emotional storytelling, genuine lifelike texture, shot on 35mm f/1.8 lens, unposed real-life atmosphere."
        ),
        is_illustration=False,
    ),
    "🔍 Macro Photography (Extreme Detail)": StylePreset(
        name="🔍 Macro Photography (Extreme Detail)",
        directive=(
            "Cinematic macro photograph, 100mm f/2.8 macro lens, extreme close-up revealing intricate microscopic textures, "
            "razor-thin depth of field with ultra creamy bokeh, directional rim lighting, pinpoint sharpness."
        ),
        is_illustration=False,
    ),
    "👤 Portrait Studio Faceless": StylePreset(
        name="👤 Portrait Studio Faceless",
        directive=(
            "Editorial studio fashion/workplace portrait of male figure shot strictly from behind or in dramatic silhouette, "
            "faceless framing, high-end studio strobe lighting, elegant wardrobe texture, clean background."
        ),
        is_illustration=False,
    ),
    "🚶 Street Photography Candid": StylePreset(
        name="🚶 Street Photography Candid",
        directive=(
            "Dynamic street photography, urban atmospheric lighting, natural shadows, authentic city life, "
            "shot on Leica M11 28mm lens, realistic grit, timeless urban composition."
        ),
        is_illustration=False,
    ),
    "🎞️ Sinematik Film 35mm Retro": StylePreset(
        name="🎞️ Sinematik Film 35mm Retro",
        directive=(
            "Authentic 35mm analog film aesthetic, Kodak Portra 400 color tones, organic subtle film grain, "
            "natural gentle halation on highlights, warm nostalgic mood, cinematic depth."
        ),
        is_illustration=False,
    ),
    "🍽️ Food & Culinary Editorial": StylePreset(
        name="🍽️ Food & Culinary Editorial",
        directive=(
            "High-end culinary editorial photography, appetizing presentation, fresh glistening textures, "
            "rustic tabletop surfaces, directional soft window light, shallow depth of field, gourmet styling."
        ),
        is_illustration=False,
    ),
    "🏛️ Arsitektur & Interior Minimalis": StylePreset(
        name="🏛️ Arsitektur & Interior Minimalis",
        directive=(
            "Architectural Digest interior photography, wide tilt-shift perspective, perfectly straight verticals, "
            "minimalist Scandinavian design, soft natural ambient illumination, harmonious peaceful layout."
        ),
        is_illustration=False,
    ),

    # 2. Ilustrasi & Seni Lukis
    "🖌️ Cat Air & Gouache (Watercolor)": StylePreset(
        name="🖌️ Cat Air & Gouache",
        directive=(
            "Expressive loose watercolor and gouache artwork, visible wet-on-wet paint bleeds, rough cold-press paper grain, "
            "translucent gradient washes, subtle organic paint splatters, handcrafted artistic feel."
        ),
        is_illustration=True,
    ),
    "🎨 Cat Minyak Klasik (Oil Painting)": StylePreset(
        name="🎨 Cat Minyak Klasik",
        directive=(
            "Masterpiece fine art oil painting, rich visible impasto brushstrokes, textured canvas substrate, "
            "luminous glazed layers, classical chiaroscuro lighting, museum-grade fine art depth."
        ),
        is_illustration=True,
    ),
    "✏️ Sketsa Pensil & Arang (Pencil Sketch)": StylePreset(
        name="✏️ Sketsa Pensil & Arang",
        directive=(
            "Detailed graphite pencil and charcoal drawing, delicate cross-hatching, smudged shadows, "
            "textured heavy sketch paper, monochrome artistic elegance, expressive hand-drawn linework."
        ),
        is_illustration=True,
    ),
    "🎭 Impresionisme Bertekstur (Impressionism)": StylePreset(
        name="🎭 Impresionisme Bertekstur",
        directive=(
            "Impressionist artistic painting, rapid dabs of pure vibrant pigment, thick textured oil paint, "
            "emphasis on changing natural light and atmosphere, evocative poetic visual rhythm."
        ),
        is_illustration=True,
    ),
    "🌌 Surealisme Modern (Surrealism)": StylePreset(
        name="🌌 Surealisme Modern",
        directive=(
            "Dreamlike modern surrealism art, poetic juxtaposition of unexpected symbolic elements, "
            "hyper-detailed realism blended with metaphysical imagination, ethereal soft lighting, evocative fine art."
        ),
        is_illustration=True,
    ),
    "🌀 Seni Abstrak Kontemporer (Abstract Art)": StylePreset(
        name="🌀 Seni Abstrak Kontemporer",
        directive=(
            "Contemporary non-representational abstract art, dynamic geometric and organic shapes, "
            "rich mixed-media textured surfaces, harmonious curated color palette, modern gallery wall-art aesthetic."
        ),
        is_illustration=True,
    ),
    "✂️ Ilustrasi Stiker Die-Cut (Die-Cut Sticker)": StylePreset(
        name="✂️ Ilustrasi Stiker Die-Cut",
        directive=(
            "Die-cut sticker illustration, crisp clean white contour outline border, isolated on plain solid background, "
            "vibrant smooth color fills, bold playful graphic design, commercial clipart aesthetic."
        ),
        is_illustration=True,
    ),

    # 3. Animasi & Kartun
    "⛩️ Anime Jepang Kontemporer": StylePreset(
        name="⛩️ Anime Jepang Kontemporer",
        directive=(
            "High-end contemporary Japanese anime style, crisp cel-shaded lines, cinematic lighting with sun rays, "
            "lush painted background scenery, rich vibrant color grading, high production anime movie aesthetic."
        ),
        is_illustration=True,
    ),
    "📖 Manga Tinta Hitam Putih (Ink Manga)": StylePreset(
        name="📖 Manga Tinta Hitam Putih",
        directive=(
            "Authentic Japanese black and white manga page art, sharp G-pen ink lines, screentone dot shading, "
            "high contrast monochrome values, dynamic comic panel composition, dramatic storytelling."
        ),
        is_illustration=True,
    ),
    "👶 Chibi & Karakter Imut (Cute Chibi)": StylePreset(
        name="👶 Chibi & Karakter Imut",
        directive=(
            "Adorable chibi character styling, oversized expressive head, tiny body, pastel color scheme, "
            "playful cute rounded contours, delightful kawaii mascot aesthetic, isolated clean background."
        ),
        is_illustration=True,
    ),
    "📺 Kartun Klasik Retro (Classic Toon)": StylePreset(
        name="📺 Kartun Klasik Retro",
        directive=(
            "Vintage mid-century classic cartoon animation style, rubber hose limbs, hand-inked line work, "
            "technicolor warm palette, charming retro nostalgic charm."
        ),
        is_illustration=True,
    ),
    "💥 Komik Pop Art (Comic Book & Halftone)": StylePreset(
        name="💥 Komik Pop Art",
        directive=(
            "Vintage comic book pop art illustration, bold heavy black outlines, Ben-Day halftone dots, "
            "high-saturation primary colors, dynamic graphic impact, Roy Lichtenstein inspired aesthetic."
        ),
        is_illustration=True,
    ),
    "🍃 Whimsical Studio Anime (Ghibli-Inspired Aesthetic)": StylePreset(
        name="🍃 Whimsical Studio Anime",
        directive=(
            "Enchanting hand-painted whimsical anime background art, lush watercolor painted clouds and nature, "
            "nostalgic warm sunlight, tranquil peaceful countryside atmosphere, soft hand-drawn aesthetic."
        ),
        is_illustration=True,
    ),
    "🌸 Pastel Kawaii Mascot Design": StylePreset(
        name="🌸 Pastel Kawaii Mascot Design",
        directive=(
            "Adorable kawaii character mascot design, soft pastel color palette (mint, lavender, butter yellow, soft pink), "
            "chubby rounded forms, cheerful friendly expression, clean cute stickers style, isolated plain background."
        ),
        is_illustration=True,
    ),
    "🧸 3D Animated Feature (Pixar-Inspired Stylized CGI)": StylePreset(
        name="🧸 3D Animated Feature",
        directive=(
            "Premium stylized 3D animation feature CGI, subsurface scattering skin/materials, expressive appealing shapes, "
            "rich volumetric lighting, cinematic color grading, studio animated blockbuster quality."
        ),
        is_illustration=True,
    ),

    # 4. 3D & Render
    "🏝️ 3D Miniature Diorama (Miniature World)": StylePreset(
        name="🏝️ 3D Miniature Diorama",
        directive=(
            "Intricate 3D miniature diorama, floating miniature island or cutaway isometric room, "
            "tilt-shift photography perspective, charming tiny detailed props, realistic miniature textures, "
            "volumetric warm lighting, whimsical tiny world aesthetic, clean plain background."
        ),
        is_illustration=True,
    ),
    "🧊 3D Commercial Studio Render": StylePreset(
        name="🧊 3D Commercial Studio Render",
        directive=(
            "Sleek commercial 3D render, minimalist studio podium setting, soft diffused lighting, "
            "matte ceramic and brushed metal materials, perfect smooth geometry, elegant product advertising look."
        ),
        is_illustration=True,
    ),
    "📐 3D Isometric Illustration (Tech & Business)": StylePreset(
        name="📐 3D Isometric Illustration",
        directive=(
            "Orthographic 3D isometric illustration, precise geometric alignment, clean modular components, "
            "modern tech and business aesthetic, soft ambient occlusion shadows, vibrant gradient palette."
        ),
        is_illustration=True,
    ),
    "🧱 3D Claymation (Tanah Liat Taktil)": StylePreset(
        name="🧱 3D Claymation",
        directive=(
            "Charming tactile stop-motion claymation, handmade polymer clay texture with subtle fingerprints, "
            "soft physical studio lighting, miniature world feel, whimsical handcrafted warmth."
        ),
        is_illustration=True,
    ),
    "🔷 Low-Poly 3D Minimalist": StylePreset(
        name="🔷 Low-Poly 3D Minimalist",
        directive=(
            "Stylized low-poly 3D art, visible clean polygon facets, vibrant flat shading, "
            "playful geometric simplicity, game asset aesthetic, crisp directional lighting."
        ),
        is_illustration=True,
    ),
    "✨ Octane Render Photorealistic (CGI Ultra-Detail)": StylePreset(
        name="✨ Octane Render Photorealistic",
        directive=(
            "Hyper-detailed Octane Render CGI, photorealistic raytraced caustic reflections, complex physical shaders, "
            "cinematic depth of field, dramatic illumination, 8K ultra-realistic digital sculpture."
        ),
        is_illustration=True,
    ),
    "🪟 3D Glassmorphism & Akrilik Transparan": StylePreset(
        name="🪟 3D Glassmorphism & Akrilik",
        directive=(
            "Modern 3D glassmorphism aesthetic, frosted translucent glass, iridescent acrylic reflections, "
            "soft pastel refraction gradients, floating geometric elements, ultra-clean futuristic design."
        ),
        is_illustration=True,
    ),

    # 5. Desain & Digital Art
    "🏷️ Paket Stiker Die-Cut (Die-Cut Sticker Pack)": StylePreset(
        name="🏷️ Paket Stiker Die-Cut",
        directive=(
            "Commercial die-cut sticker sheet collection, multiple individual graphic stickers arranged in a neat balanced grid across the entire canvas, "
            "each sticker surrounded by a crisp clean white die-cut cutline border with subtle soft drop shadow, "
            "isolated on a seamless clean solid white background, knolling organization, commercial microstock clipart pack, evenly spaced layout with equal margins."
        ),
        is_illustration=True,
    ),
    "📱 Icon Desain Aplikasi & Web (App Icon Set)": StylePreset(
        name="📱 Icon Desain Aplikasi & Web",
        directive=(
            "Modern vector app icon design, clean glyph geometry, squircle silhouette, balanced minimalist symbol, "
            "crisp pixel-perfect contours, professional UI/UX graphic resource."
        ),
        is_illustration=True,
    ),
    "📄 Flat Design Vector Minimalist": StylePreset(
        name="📄 Flat Design Vector Minimalist",
        directive=(
            "Clean modern flat design vector illustration, bold geometric shapes, no gradients, curated limited color palette, "
            "minimalist negative space, corporate Memphis tech editorial aesthetic."
        ),
        is_illustration=True,
    ),
    "🔶 Logo Monogram & Geometris": StylePreset(
        name="🔶 Logo Monogram & Geometris",
        directive=(
            "High-end corporate logo and monogram design, golden ratio geometry, elegant minimalist line art, "
            "isolated on solid plain background, luxury branding graphic asset."
        ),
        is_illustration=True,
    ),
    "🌃 Cyberpunk & Futuristic Neon": StylePreset(
        name="🌃 Cyberpunk & Futuristic Neon",
        directive=(
            "High-tech cyberpunk digital art, glowing cyan and magenta neon rim lighting, dark rainy asphalt reflections, "
            "futuristic architectural backdrop, cinematic sci-fi contrast, atmospheric volumetric fog."
        ),
        is_illustration=True,
    ),
    "⚙️ Steampunk Vintage Mekanikal": StylePreset(
        name="⚙️ Steampunk Vintage Mekanikal",
        directive=(
            "Intricate Victorian steampunk digital art, ornate brass gears, copper pipes, glowing amber vacuum tubes, "
            "rich leather textures, industrial steam atmosphere, retro-futuristic craftsmanship."
        ),
        is_illustration=True,
    ),
    "📼 Synthwave & Retrowave 80s": StylePreset(
        name="📼 Synthwave & Retrowave 80s",
        directive=(
            "Vibrant 1980s synthwave retrowave aesthetic, glowing perspective wireframe grid, purple-pink sunset gradient, "
            "neon wireframes, chrome reflections, vintage CRT glow, nostalgic arcade vibe."
        ),
        is_illustration=True,
    ),
    "👾 Pixel Art Klasik 16-bit": StylePreset(
        name="👾 Pixel Art Klasik 16-bit",
        directive=(
            "Masterful 16-bit pixel art, crisp pixel grid with no anti-aliasing blur, nostalgic retro video game aesthetic, "
            "expertly dithered shading, vibrant curated color palette."
        ),
        is_illustration=True,
    ),
    "🧙 Digital Concept Art Fantasi & Sci-Fi": StylePreset(
        name="🧙 Digital Concept Art Fantasi & Sci-Fi",
        directive=(
            "Epic digital concept art, cinematic sweeping landscape, textured digital brushwork, dramatic atmospheric haze, "
            "masterful storytelling scale, industry production concept piece."
        ),
        is_illustration=True,
    ),
}

DEFAULT_STYLE_CATEGORY = "Fotografi (Photorealism)"
DEFAULT_STYLE = "📷 Foto Komersial Bersih (Commercial Advertising)"

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
    "Grid Simetris Seimbang (Sticker Sheet / Icon Pack)": "Neatly organized symmetrical grid layout, elements evenly distributed across the entire canvas with balanced margins on all sides, knolling arrangement, isolated on solid white background, no lopsided empty space.",
    "Full Frame / Edge-to-Edge (Tanpa Ruang Kosong)": "Full-bleed edge-to-edge dynamic composition, no empty negative space, frame is completely filled with rich visual elements and high detail.",
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
