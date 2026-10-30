"""AI Prompt Enhancer: expands a short base idea into 1 pro image prompt."""
from __future__ import annotations

import json
import re
from typing import Callable, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync


ENHANCER_SYSTEM_INSTRUCTION = """\
You are an elite commercial art director and prompt engineer specializing in top-selling microstock imagery for Adobe Stock & Shutterstock.

Rewrite the user's base concept into ONE highly detailed, production-ready, ultra-clean image generation prompt.

CRITICAL PARAMETER FIDELITY (STRICT ENFORCEMENT):
The prompt must STRICTLY adhere to the user's selected camera perspective, composition framing, lighting condition, aesthetic style, and aspect ratio.

CRITICAL ADOBE STOCK COMPLIANCE & COMMERCIAL RULES:

1. ZERO FEMALE CHARACTERS (STRICT UNIVERSAL PROHIBITION):
   - ABSOLUTELY ZERO female figures, women, girls, or feminine representations in ANY form (human, cartoon, cyborg, robot, mascot, or illustration).
   - When people are not explicitly requested by the user, focus strictly on inanimate objects, architecture, food, nature, tools, and scenery.
   - If people are requested, depict ONLY male figures that are completely faceless.
   - You MUST explicitly include: "strictly no women, no female characters, no visible facial features, completely faceless and clean".

2. ZERO TEXT & ZERO TYPOGRAPHY (STRICT CLEANLINESS):
   - Absolutely NO text, letters, words, numbers, typography, calligraphy, inscriptions, watermarks, signatures, logos, or UI labels anywhere in the image.
   - All surfaces, packaging, books, posters, and screens must be completely clean and blank.

3. MANDATORY FACELESS CREATURES & CHARACTERS (ZERO TOLERANCE):
   - ANY living creature (human, animal, insect) or humanoid robot MUST BE 100% FACELESS: zero visible eyes, zero facial features, zero expressions.
   - Use techniques: "shot from behind", "face hidden in deep shadow", "cropped at the neck/shoulders", "facing away from camera", or "deep silhouette".
   - For sticker packs, clipart, and icons: avoid characters/mascots with facial features; prioritize objects, food, tools, nature, and architecture.

4. UNBRANDED & GENERIC PROPS:
   - NO brands, logos, trademarks, or copyrighted gadget designs (no Apple logos, no recognizable smartphone/car designs).
   - Describe technology as "sleek minimalist unbranded matte aluminum chassis with clean blank displays".

5. COMMERCIAL COMPOSITION & NEGATIVE SPACE:
   - FOR STICKER PACKS / CLIPART / ICON SETS: ALWAYS arrange the stickers in a balanced, evenly-spaced grid (sticker sheet / knolling arrangement) neatly distributed across the canvas with equal margins on all sides, isolated on a clean solid white background. Each sticker MUST have its own distinct white die-cut contour cutline border and subtle shadow.
   - FOR GENERAL SCENES: Faithfully apply the user's chosen composition framing (e.g. Negative Space for Copy, Golden Ratio, Rule of Thirds, Center Framed, or Symmetrical).

6. AUTHENTIC LIGHTING & ANTI-PLASTIC GLOW:
   - Use strictly real photographic lighting matching the user's chosen lighting condition.
   - Avoid artificial neon glows, oversaturated plastic sheen, or waxy textures.

7. PHYSICAL MICRO-TEXTURES:
   - Specify rich real-world physical textures (linen fabric weave, authentic wood grain, brushed aluminum, crisp glass reflections).

8. MANDATORY ASPECT RATIO & ORIENTATION:
   - Explicitly describe framing matching the target aspect ratio.
   - You MUST end the prompt with the text "[Aspect Ratio: {aspect_ratio}]".

OUTPUT FORMAT:
Output ONLY the final single-paragraph prompt of 90-180 words in English ending with the Aspect Ratio tag.
No preamble, no JSON, no markdown codeblocks, no bullet points, no commentary.
"""


def _format_with_aspect_ratio(raw_text: str, aspect_ratio: str) -> str:
    """Ensure the prompt ends with the proper [Aspect Ratio: ...] tag."""
    clean = (raw_text or "").strip().strip('"').strip()
    if not clean:
        return ""
    if re.search(r"\[Aspect Ratio:\s*[^\]]+\]", clean, re.IGNORECASE):
        clean = re.sub(r"\[Aspect Ratio:\s*[^\]]+\]", f"[Aspect Ratio: {aspect_ratio}]", clean, flags=re.IGNORECASE)
    else:
        clean = f"{clean} [Aspect Ratio: {aspect_ratio}]"
    return clean


def parse_enhancer_response(text: str, aspect_ratio: str) -> str:
    """Parse Gemini response into a clean single prompt string."""
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
        clean_text = re.sub(r"\n?```$", "", clean_text).strip()

    # Try parsing if the model returned JSON
    try:
        data = json.loads(clean_text)
        if isinstance(data, list) and data:
            item = data[0]
            clean_text = item.get("prompt", "") if isinstance(item, dict) else str(item)
        elif isinstance(data, dict):
            for k in ("prompt", "text", "result"):
                if k in data and isinstance(data[k], str):
                    clean_text = data[k]
                    break
            else:
                for k in ("prompts", "items", "results"):
                    if k in data and isinstance(data[k], list) and data[k]:
                        item = data[k][0]
                        clean_text = item.get("prompt", "") if isinstance(item, dict) else str(item)
                        break
    except Exception:
        pass

    formatted = _format_with_aspect_ratio(clean_text, aspect_ratio)
    if not formatted:
        raise TransientError("Empty prompt returned by enhancer")
    return formatted


def build_enhancer_input(
    base_idea: str,
    style_name: str,
    aspect_ratio: str,
    lighting: str = "",
    camera: str = "",
    composition: str = "",
) -> str:
    style = config.STYLES.get(style_name, config.STYLES[config.DEFAULT_STYLE])
    light_desc = config.LIGHTING_OPTIONS.get(lighting, "")
    cam_desc = config.CAMERA_OPTIONS.get(camera, "")
    comp_desc = config.COMPOSITION_OPTIONS.get(composition, "")

    ratio_desc = {
        "1:1": "1:1 square format",
        "16:9": "16:9 widescreen horizontal format",
        "9:16": "9:16 vertical stories/reels format",
        "4:3": "4:3 classic landscape format",
        "3:4": "3:4 classic portrait format",
    }.get(aspect_ratio, f"{aspect_ratio} format")

    parts = [
        f"Base concept/subject: {base_idea.strip()}",
        f"Aesthetic/Style: {style.name}: {style.directive}",
        f"Target Aspect Ratio: {aspect_ratio} ({ratio_desc}), append '[Aspect Ratio: {aspect_ratio}]' at the end of the prompt.",
    ]
    if light_desc:
        parts.append(f"MANDATORY Lighting condition: {light_desc}")
    if cam_desc:
        parts.append(f"MANDATORY Camera/Lens perspective: {cam_desc}")
    if comp_desc:
        parts.append(f"MANDATORY Composition framing: {comp_desc}")

    parts.append(
        "MANDATORY UNIVERSAL EXCLUSIONS: Strictly NO female characters, NO women, NO visible facial features; "
        "all living beings must be completely faceless. Prioritize inanimate objects, architecture, food, nature, tools, or faceless subjects."
    )
    parts.append(
        f"Generate 1 high-quality commercial prompt blending all the above parameters naturally, ending with [Aspect Ratio: {aspect_ratio}]."
    )
    return "\n".join(parts)


def enhance_prompt(
    client: genai.Client,
    base_idea: str,
    style_name: str,
    aspect_ratio: str,
    lighting: str = "",
    camera: str = "",
    composition: str = "",
    on_retry: Optional[Callable[[str], None]] = None,
) -> str:
    """Call the Gemini text model to produce 1 commercial image prompt matching all selected parameters."""
    if not base_idea or not base_idea.strip():
        raise ValueError("Please enter a base idea first.")

    def _call() -> str:
        prompt_input = build_enhancer_input(base_idea, style_name, aspect_ratio, lighting, camera, composition)
        last_err = None
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        temperature=0.75,
                        max_output_tokens=600,
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_input,
                        config=config_obj,
                    )
                    text = (response.text or "").strip()
                    if text:
                        return parse_enhancer_response(text, aspect_ratio)
                elif hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        input=prompt_input,
                        store=False,
                    )
                    text = (interaction.output_text or "").strip()
                    if text:
                        return parse_enhancer_response(text, aspect_ratio)
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(term in err_str for term in ("503", "unavailable", "high demand", "404", "400", "invalid_argument", "invalid argument")):
                    continue
                raise

        if last_err:
            raise last_err
        raise TransientError("Empty response from prompt enhancer")

    return retry_sync(_call, label="Prompt enhancement", on_retry=on_retry)
