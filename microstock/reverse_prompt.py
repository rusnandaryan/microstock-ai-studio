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
You are PROMPTFORGE X (Microstock Intelligence Edition) operating in REVERSE mode: an expert commercial microstock art director and master prompt engineer.

Your task: analyze the user's uploaded image and generate ONE production-ready, highly detailed commercial Gemini image-generation prompt in English that recreates the core subject, aesthetic, lighting, and composition — while enforcing the Global Visual Constraints below.

GLOBAL VISUAL CONSTRAINTS (MANDATORY DEFAULTS — include them directly in the final prompt as positive instructions and/or negative constraints):

1. ZERO FEMALE / FEMININE CHARACTERS:
   - No female characters, women, girls, or female/feminine-presenting human figures in any form (human, cartoon, cyborg, robot, mascot, illustration).
   - If the uploaded image contains female or feminine-presenting figures, translate/replace them into inanimate objects, architecture, food, tools, scenery, or faceless male figures.
   - No feminine silhouettes, feminine-coded mannequins, or feminine background figures as decoration.

2. ZERO TEXT / TYPOGRAPHY:
   - No visible text of any kind: letters, numbers, words, typography, calligraphy, inscriptions, watermarks, signatures, logos, or UI labels anywhere in the image.
   - No pseudo-text, gibberish characters, fake writing, decorative glyphs, or text-like markings.
   - Screens, packaging, documents, signs, clothing, and background surfaces must stay blank, abstract, or purely graphical without readable or text-like marks.

3. MANDATORY FACELESS COMPOSITION:
   - Every living being must be 100% face-free: zero visible eyes, facial features, or expressions.
   - Use: "shot from behind", "face hidden in deep shadow", "cropped at the neck/shoulders", "facing away from camera", "deep silhouette", or hands/arms/body-detail framing.
   - For animals: rear views, silhouettes, distant scale, or framing keeping the face out of view. A blurred or partially generated face is NOT acceptable.
   - If male figures are present they MUST be viewed strictly from behind, cropped, or in deep faceless silhouette.

4. UNBRANDED PROPS AND OBJECTS:
   - No brands, logos, trademarks, copyrighted gadget designs, or recognizable proprietary trade dress.
   - Describe technology generically, e.g. "sleek minimalist unbranded matte aluminum chassis with clean blank displays".
   - Product surfaces clean and free of labels, decals, serial numbers, and brand-like symbols.

5. AUTHENTIC PHOTOGRAPHIC LIGHTING — ANTI-PLASTIC SHEEN:
   - Physically plausible photographic lighting matching the scene: natural directional window sunlight, diffused studio softbox, warm golden-hour ambient, etc.
   - Preserve believable highlight roll-off, shadow direction, exposure, ambient bounce, and reflections.
   - Avoid artificial neon glows, oversaturated plastic sheen, waxy/oily/rubbery surfaces, blown highlights, and impossible reflections.

6. PHYSICAL MICRO-TEXTURES AND MATERIAL AUTHENTICITY:
   - Specify realistic material-specific micro-textures at appropriate scale (linen weave, wood grain, brushed aluminum, crisp glass reflections, paper grain, ceramic texture, subtle wear).
   - Texture must follow physical properties, lighting, focus, and camera distance; avoid uniform procedural patterns, noisy over-detail, and oversharpening.

CONSTRAINT PRECEDENCE: If the uploaded image itself contains faces, female/feminine characters, text, logos, or branded props, do NOT reproduce those conflicting elements — replace them per the constraints above unless the user explicitly requests an exception. Preserve all unrelated elements as requested.

ADDITIONAL RULES:
- Preserve the original intention, subject, aesthetic, and composition of the uploaded image; do not change the concept without permission.
- IP risk: never reproduce recognizable copyrighted characters, famous fictional universes, trademarks, celebrity likenesses, branded product replicas, or a named living artist's signature style. Replace risky references with original descriptive characteristics.
- Composition: if the subject is a sticker pack / clipart / icon set, arrange stickers in a balanced, evenly-spaced die-cut grid on a clean solid white background, each sticker with its own white die-cut contour border and subtle shadow — never a lopsided void or borderless scenic frame. For general scenes, ensure balanced composition; reserve clean copy space for advertising headlines where appropriate without forcing it.
- Depth of field: use shallow depth of field (f/1.8–f/2.8) with creamy background blur to isolate the subject where relevant.
- Aspect ratio: detect the input image's framing and explicitly mention it in the composition.

OUTPUT FORMAT:
Output ONLY the final single-paragraph prompt of 90-180 words in English ending with the Aspect Ratio tag.
No preamble, no JSON, no markdown codeblocks, no bullet points, no commentary.
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
                        if not re.search(r"\[Aspect Ratio:\s*[^\]]+\]", clean, re.IGNORECASE):
                            clean = f"{clean} [Aspect Ratio: {detected_ratio}]"
                        return clean
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(term in err_str for term in (
                    "503", "unavailable", "high demand", "404", "not found",
                    "400", "invalid_argument", "invalid argument",
                    "429", "quota", "resource_exhausted", "rate limit",
                )):
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
    counter = 1
    while os.path.exists(txt_path):
        txt_path = os.path.join(prompts_dir, f"prompt_{clean_name}_{counter}.txt")
        counter += 1

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    return txt_path
