"""Reverse Prompting Engine: Analyzes an uploaded image via Gemini Vision to generate a clean commercial stock prompt."""
from __future__ import annotations

import asyncio
import os
import re
from typing import Callable, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_async

REVERSE_PROMPT_SYSTEM_INSTRUCTION = """\
You are an expert commercial microstock art director and master prompt engineer.
Your task is to analyze the user's uploaded image and generate ONE production-ready, highly detailed commercial image generation prompt in English that recreates the core subject, aesthetic, lighting, and composition of this image.

CRITICAL ADOBE STOCK COMPLIANCE & COMMERCIAL RULES (STRICT ENFORCEMENT):

1. ZERO FEMALE CHARACTERS (STRICT UNIVERSAL PROHIBITION):
   - ABSOLUTELY ZERO female figures, women, girls, or feminine representations in ANY form (human, cartoon, cyborg, robot, mascot, or illustration).
   - If the uploaded image contains female figures, TRANSLATE/REPLACE them into inanimate objects, architecture, food, tools, or male figures (strictly faceless).
   - You MUST explicitly include in the prompt: "strictly no women, no female characters, no visible facial features, completely faceless and clean".

2. ZERO TEXT & ZERO TYPOGRAPHY (STRICT CLEANLINESS):
   - Absolutely NO text, letters, words, numbers, typography, calligraphy, inscriptions, watermarks, signatures, logos, or UI labels anywhere in the image.
   - All surfaces, packaging, books, posters, and screens must be completely clean and blank.

3. MANDATORY FACELESS CREATURES & CHARACTERS (ZERO TOLERANCE):
   - ANY living creature (human, animal, insect) or humanoid robot MUST BE 100% FACELESS: zero visible eyes, zero facial features, zero expressions.
   - Use techniques: "shot from behind", "face hidden in deep shadow", "cropped at the neck/shoulders", "facing away from camera", or "deep silhouette".
   - For sticker packs, clipart, and icons: avoid characters/mascots with facial features; prioritize objects, food, tools, nature, and architecture.
   - If male figures are present, they MUST be viewed strictly from behind, cropped at the neck/hands, or in deep faceless silhouette.

4. UNBRANDED & GENERIC PROPS:
   - NO brands, logos, trademarks, or copyrighted gadget designs (no Apple logos, no recognizable smartphone/car designs).
   - Describe technology as "sleek minimalist unbranded matte aluminum chassis with clean blank displays".

5. COMMERCIAL COMPOSITION & NEGATIVE SPACE:
   - FOR STICKER PACKS / CLIPART / ICON SETS: ALWAYS arrange the stickers in a balanced, evenly-spaced grid (sticker sheet / knolling arrangement) neatly distributed across the canvas with equal margins on all sides, isolated on a clean solid white background. Each sticker MUST have its own distinct white die-cut contour cutline border and subtle shadow. NEVER leave a lopsided empty void on one side, and NEVER merge them into a borderless scenic full-frame picture.
   - FOR GENERAL SCENES: If the subject is an environment or pattern, ensure a balanced composition; for standard commercial stock, compose with clean copy space reserved for advertising headlines.

6. AUTHENTIC LIGHTING & ANTI-PLASTIC GLOW:
   - Use strictly real photographic lighting: "natural directional window sunlight", "diffused studio softbox", or "warm golden hour ambient illumination".
   - Avoid artificial neon glows, oversaturated plastic sheen, or waxy textures.

7. PHYSICAL MICRO-TEXTURES & CONTROLLED DEPTH OF FIELD:
   - Specify rich real-world physical textures (linen fabric weave, authentic wood grain, brushed aluminum, crisp glass reflections).
   - Use shallow depth of field (f/1.8 to f/2.8) with creamy, smooth background blur to isolate the subject cleanly.

8. MANDATORY ASPECT RATIO & ORIENTATION:
   - Detect the aspect ratio / framing of the input image (e.g. 16:9, 9:16, 1:1, 4:3, 3:4).
   - Explicitly mention the framing in the composition.
   - You MUST end the prompt with the text "[Aspect Ratio: {detected_ratio}]" (e.g. "[Aspect Ratio: 16:9]").

Output ONLY the final single paragraph prompt of 90-180 words in English ending with the Aspect Ratio tag.
No preamble, no markdown codeblocks, no bullet points, no commentary.
"""


def _detect_ratio(width: int, height: int) -> str:
    """Helper to detect the closest standard microstock aspect ratio."""
    if width <= 0 or height <= 0:
        return "16:9"
    ratio = width / height
    candidates = [
        (1.0, "1:1"),
        (16 / 9, "16:9"),
        (9 / 16, "9:16"),
        (4 / 3, "4:3"),
        (3 / 4, "3:4"),
    ]
    best_match = min(candidates, key=lambda c: abs(c[0] - ratio))
    return best_match[1]


async def generate_reverse_prompt_async(
    client: genai.Client,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    label: str = "Reverse Prompt",
    width: int = 0,
    height: int = 0,
    on_retry: Optional[Callable[[str], None]] = None,
) -> str:
    """Analyze image using Gemini Vision and return a production-ready prompt string."""
    from google.genai import types

    from .metadata import _prepare_vision_bytes
    detected_ratio = _detect_ratio(width, height)
    safe_bytes, safe_mime = _prepare_vision_bytes(image_bytes, mime_type)
    image_part = types.Part.from_bytes(data=safe_bytes, mime_type=safe_mime)
    
    user_instruction = (
        f"Analyze this image and write a detailed, compliant commercial microstock prompt in English. "
        f"Detected framing ratio is roughly {detected_ratio}. "
        f"Apply all strict compliance rules (faceless, no female, no text, clean copy space, unbranded props). "
        f"End with '[Aspect Ratio: {detected_ratio}]'."
    )
    contents = [image_part, user_instruction]

    def _call() -> str:
        last_err = None
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    config_obj = types.GenerateContentConfig(
                        system_instruction=REVERSE_PROMPT_SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=600,
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config_obj,
                    )
                    text = (response.text or "").strip()
                    if text:
                        # Clean up quotes or markdown wrapper if model added any
                        clean = text.strip('"').strip("'").strip()
                        if clean.startswith("```"):
                            clean = re.sub(r"^```[a-zA-Z]*\n?", "", clean)
                            clean = re.sub(r"\n?```$", "", clean)
                        if not re.search(r"\[Aspect Ratio:\s+\d+:\d+\]", clean, re.IGNORECASE):
                            clean = f"{clean} [Aspect Ratio: {detected_ratio}]"
                        return clean
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(term in err_str for term in ("503", "unavailable", "high demand", "404", "400", "invalid_argument", "invalid argument")):
                    continue
                raise
        if last_err:
            raise last_err
        raise TransientError("Empty response from reverse prompt generator")

    return await retry_async(
        lambda: asyncio.to_thread(_call),
        label=label,
        on_retry=on_retry,
    )


def save_prompt_to_file(prompt: str, original_filename: str) -> str:
    """Save the generated prompt to a local .txt file in exports/prompts/ directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_dir = os.path.join(base_dir, "exports", "prompts")
    os.makedirs(prompts_dir, exist_ok=True)

    clean_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", os.path.splitext(original_filename)[0])
    txt_filename = f"prompt_{clean_name}.txt"
    txt_path = os.path.join(prompts_dir, txt_filename)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    return txt_path
