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

1. ZERO FEMALE CHARACTERS (STRICT RULE):
   - NO female characters, women, girls, or feminine figures in ANY form (human, silhouette, cyborg, humanoid robot, or illustration).
   - If the uploaded image contains female figures, TRANSLATE/REPLACE them into male figures (faceless), gender-neutral hands/silhouettes, or purely focus on inanimate objects, architecture, food, nature, tools, or concepts.

2. ZERO TEXT & ZERO TYPOGRAPHY (STRICT CLEANLINESS):
   - Absolutely NO text, letters, words, numbers, typography, calligraphy, inscriptions, watermarks, signatures, logos, or UI labels anywhere in the image.
   - All surfaces, packaging, books, posters, and screens must be completely clean and blank.

3. MANDATORY FACELESS CHARACTERS (ZERO TOLERANCE):
   - If ANY living creature (human, animal) or humanoid robot is present, their face MUST NEVER be fully visible.
   - Use techniques: "shot from behind", "face hidden in cinematic shadow", "cropped at the neck/shoulders", "over-the-shoulder view", "focus strictly on hands", or "deep silhouette".

4. UNBRANDED & GENERIC PROPS:
   - NO brands, logos, trademarks, or copyrighted gadget designs (no Apple logos, no recognizable smartphone/car designs).
   - Describe technology as "sleek minimalist unbranded matte aluminum chassis with clean blank displays".

5. COMMERCIAL COPY SPACE / NEGATIVE SPACE:
   - Always compose the scene with 30% to 40% clean, uncluttered negative space (clean wall, soft sky, or smooth creamy bokeh background) on one side, reserved for advertising headlines and copy.

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

    detected_ratio = _detect_ratio(width, height)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    
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
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
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
                if "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "404" in err_str:
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
