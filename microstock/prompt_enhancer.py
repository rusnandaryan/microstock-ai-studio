"""AI Prompt Enhancer: expands a short base idea into 5 diversified pro image prompts."""
from __future__ import annotations

import json
import re
from typing import Callable, List, Optional, Tuple

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync


SCENARIO_DESCRIPTIONS: List[Tuple[str, str]] = [
    ("Pristine Hero", "Fokus subjek murni & kesempurnaan material"),
    ("In-Action Moment", "Momen proses & interaksi dinamis (faceless)"),
    ("Raw Materials", "Bahan baku & komponen asal subjek"),
    ("Lifestyle Pairing", "Konteks cerita & benda pelengkap"),
    ("Colorway & Mood", "Variasi palet warna & tekstur aksen"),
]


ENHANCER_SYSTEM_INSTRUCTION = """\
You are an elite commercial art director and prompt engineer specializing in top-selling microstock imagery for Adobe Stock & Shutterstock.

Rewrite the user's base concept into 5 highly detailed, production-ready, ultra-clean image generation prompts.

CRITICAL PARAMETER FIDELITY (STRICT ENFORCEMENT):
Every single prompt must STRICTLY adhere to the user's selected camera perspective, composition framing, lighting condition, aesthetic style, and aspect ratio. Do NOT alter the chosen camera lens, framing, or lighting across the 5 prompts.

To strictly prevent microstock rejections for "Similar Content / Duplicate Submission" while respecting the user's camera and framing choices, you MUST vary the 5 prompts across 5 distinct commercial storytelling scenarios:
1. Scenario 1 (Pristine Hero): The main subject in its purest, isolated, iconic form, focusing deeply on its physical materials, fine finish, and standalone beauty within the chosen framing.
2. Scenario 2 (In-Action Dynamic Moment): The subject in an active moment of practical use, process, or motion (strictly faceless, hands/tools only, showing dynamic function).
3. Scenario 3 (Raw Materials & Origins): The subject naturally paired with its authentic raw ingredients, component parts, organic elements, or crafting tools.
4. Scenario 4 (Lifestyle Pairing Context): The subject contextualized alongside complementary everyday objects that tell a realistic lifestyle or professional story.
5. Scenario 5 (Alternative Colorway & Mood Accent): The subject explored with an alternative complementary color palette, distinct material texture, or subtle accent contrast while maintaining the overall atmosphere.

CRITICAL ADOBE STOCK COMPLIANCE & COMMERCIAL RULES (STRICT ENFORCEMENT ACROSS ALL 5 PROMPTS):

1. ZERO FEMALE CHARACTERS (STRICT UNIVERSAL PROHIBITION):
   - ABSOLUTELY ZERO female figures, women, girls, or feminine representations in ANY form (human, cartoon, cyborg, robot, mascot, or illustration).
   - When people are not explicitly requested by the user, focus strictly on inanimate objects, architecture, food, nature, tools, and scenery.
   - If people are requested, depict ONLY male figures that are completely faceless.
   - In EVERY prompt, you MUST explicitly include: "strictly no women, no female characters, no visible facial features, completely faceless and clean".

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
   - You MUST end each prompt with the text "[Aspect Ratio: {aspect_ratio}]".

OUTPUT FORMAT:
Output a valid JSON array containing exactly 5 prompt strings corresponding to the 5 scenarios:
[
  "Detailed prompt paragraph 1 (Pristine Hero) of 80-160 words ending with [Aspect Ratio: {aspect_ratio}]",
  "Detailed prompt paragraph 2 (In-Action Moment) of 80-160 words ending with [Aspect Ratio: {aspect_ratio}]",
  "Detailed prompt paragraph 3 (Raw Materials) of 80-160 words ending with [Aspect Ratio: {aspect_ratio}]",
  "Detailed prompt paragraph 4 (Lifestyle Pairing) of 80-160 words ending with [Aspect Ratio: {aspect_ratio}]",
  "Detailed prompt paragraph 5 (Colorway & Mood) of 80-160 words ending with [Aspect Ratio: {aspect_ratio}]"
]
Do not output anything other than the JSON array.
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


def parse_enhancer_response(text: str, aspect_ratio: str) -> List[str]:
    """Parse Gemini JSON response into a list of 5 prompt strings."""
    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
    except Exception as e:
        raise TransientError(f"Failed to parse JSON: {e}")

    if isinstance(data, dict):
        for k in ("prompts", "items", "results"):
            if k in data and isinstance(data[k], list):
                data = data[k]
                break

    if not isinstance(data, list):
        raise TransientError("Enhancer response JSON is not an array")

    prompts: List[str] = []
    for item in data:
        if isinstance(item, dict):
            p_str = item.get("prompt", "") or item.get("text", "") or ""
        else:
            p_str = str(item)

        formatted = _format_with_aspect_ratio(p_str, aspect_ratio)
        if formatted:
            prompts.append(formatted)

    if not prompts:
        raise TransientError("Empty list of prompts returned by enhancer")

    return prompts


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
        f"Target Aspect Ratio: {aspect_ratio} ({ratio_desc}), append '[Aspect Ratio: {aspect_ratio}]' at the end of each prompt.",
    ]
    if light_desc:
        parts.append(f"MANDATORY Lighting condition (Apply to ALL 5 prompts): {light_desc}")
    if cam_desc:
        parts.append(f"MANDATORY Camera/Lens perspective (Apply to ALL 5 prompts): {cam_desc}")
    if comp_desc:
        parts.append(f"MANDATORY Composition framing (Apply to ALL 5 prompts): {comp_desc}")

    parts.append(
        "MANDATORY 5-SCENARIO DIVERSIFICATION (Generate 1 distinct prompt for each scenario while strictly preserving the above camera, lighting, and composition):\n"
        "  - Scenario 1 (Pristine Hero): Pure standalone subject, immaculate material perfection.\n"
        "  - Scenario 2 (In-Action Dynamic Moment): Active process or dynamic use interaction (faceless, hands/tools only).\n"
        "  - Scenario 3 (Raw Materials & Origins): Paired authentically with raw ingredients, components, or crafting tools.\n"
        "  - Scenario 4 (Lifestyle Pairing Context): Paired with complementary everyday objects telling a rich narrative.\n"
        "  - Scenario 5 (Colorway & Mood Accent): Explored with an alternative complementary color palette or accent contrast."
    )
    parts.append(
        "MANDATORY UNIVERSAL EXCLUSIONS: Strictly NO female characters, NO women, NO visible facial features; "
        "all living beings must be completely faceless. Prioritize inanimate objects, architecture, food, nature, tools, or faceless subjects."
    )
    parts.append(
        f"Generate 5 distinct high-quality commercial prompts in JSON format ending with [Aspect Ratio: {aspect_ratio}]."
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
) -> List[str]:
    """Call the Gemini text model to produce 5 alternative commercial image prompts."""
    if not base_idea or not base_idea.strip():
        raise ValueError("Please enter a base idea first.")

    def _call() -> List[str]:
        prompt_input = build_enhancer_input(base_idea, style_name, aspect_ratio, lighting, camera, composition)
        last_err = None
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        temperature=0.85,
                        max_output_tokens=2200,
                        response_mime_type="application/json",
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
