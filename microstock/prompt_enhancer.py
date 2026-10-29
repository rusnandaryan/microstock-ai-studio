"""AI Prompt Enhancer: expands a short base idea into 5 diversified pro image prompts."""
from __future__ import annotations

import json
import re
from typing import Callable, Dict, List, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync


PROMPT_ARCHETYPES = [
    {
        "id": "wide_context",
        "title": "Shot 1: Wide Context & Environment",
        "badge": "🌐 Wide Context",
        "badge_class": "ms-badge-blue",
        "guidance": "Establishing/wide environmental composition showing the subject naturally integrated into its realistic wider architectural, landscape, or workspace ecosystem.",
    },
    {
        "id": "macro_detail",
        "title": "Shot 2: Macro & Material Craftsmanship",
        "badge": "🔍 Macro Detail",
        "badge_class": "ms-badge-amber",
        "guidance": "Extreme close-up/macro detail highlighting physical micro-textures, material grain, surface reflections, tactile craftsmanship, and a shallow depth of field (f/1.8 to f/2.8).",
    },
    {
        "id": "in_use_action",
        "title": "Shot 3: Dynamic Interaction / In-Use Action",
        "badge": "⚡ In-Use Action",
        "badge_class": "ms-badge-green",
        "guidance": "Dynamic action, process, or practical functional use (strictly faceless; hands, tools, or physical motion only).",
    },
    {
        "id": "copy_space",
        "title": "Shot 4: Clean Copy Space / Ad Layout",
        "badge": "📐 Copy Space Ready",
        "badge_class": "ms-badge-accent",
        "guidance": "Clean commercial advertising framing with 40% to 50% uncluttered negative space (clean wall, soft studio gradient, or creamy bokeh) on one side reserved for headline copy.",
    },
    {
        "id": "alternative_angle",
        "title": "Shot 5: Flat Lay Knolling / Alternative Angle",
        "badge": "🧩 Flat Lay / Knolling",
        "badge_class": "ms-badge-purple",
        "guidance": "Overhead 90-degree flat lay (knolling arrangement neatly organized with balanced complementary props) OR dramatic high/low geometric perspective completely contrasting the other 4 shots.",
    },
]


ENHANCER_SYSTEM_INSTRUCTION = """\
You are an elite commercial art director and prompt engineer specializing in top-selling microstock imagery for Adobe Stock & Shutterstock.

To strictly prevent microstock rejections for "Similar Content / Spam Submission", you MUST transform the user's base idea into 5 completely visually distinct, non-repetitive image generation prompts representing 5 distinct commercial photography archetypes:

1. Shot 1: Wide Context & Environment
   - Establishing/wide environmental shot showing the subject in its realistic, wider setting or architectural ecosystem.
   - Purpose: Editorial, hero website banners, contextual realism.

2. Shot 2: Macro & Material Craftsmanship
   - Extreme close-up/macro detail highlighting physical micro-textures, material grain, surface reflections, tactile craftsmanship, and a shallow depth of field (f/1.8 to f/2.8).
   - Purpose: Tactile product features, packaging, material authenticity.

3. Shot 3: Dynamic Interaction / In-Use Action
   - Dynamic motion, functional interaction, practical use, process, or assembly (strictly faceless; hands, tools, or physical motion only).
   - Purpose: How-to guides, social media marketing, functional demonstration.

4. Shot 4: Clean Copy Space / Ad Layout
   - Commercial advertising framing with 40% to 50% clean, uncluttered negative space (clean background, smooth wall, or soft bokeh) on one side reserved for headline copy.
   - Purpose: #1 commercial stock asset for graphic designers and agencies.

5. Shot 5: Flat Lay Knolling / Alternative Angle
   - Overhead 90-degree flat lay (knolling arrangement neatly organized with balanced complementary props) OR dramatic high/low geometric perspective completely contrasting the other 4 shots.
   - Purpose: E-commerce, catalogs, modern minimalist branding.

CRITICAL ADOBE STOCK COMPLIANCE & COMMERCIAL RULES (STRICT ENFORCEMENT ACROSS ALL 5 SHOTS):

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
   - FOR GENERAL SCENES: Adhere strictly to the requested archetype framing for each shot.

6. AUTHENTIC LIGHTING & ANTI-PLASTIC GLOW:
   - Use strictly real photographic lighting: "natural directional window sunlight", "diffused studio softbox", or "warm golden hour ambient illumination".
   - Avoid artificial neon glows, oversaturated plastic sheen, or waxy textures.

7. PHYSICAL MICRO-TEXTURES:
   - Specify rich real-world physical textures (linen fabric weave, authentic wood grain, brushed aluminum, crisp glass reflections).

8. MANDATORY ASPECT RATIO & ORIENTATION:
   - Explicitly describe framing matching the target aspect ratio.
   - You MUST end each prompt with the text "[Aspect Ratio: {aspect_ratio}]".

OUTPUT FORMAT:
Output a valid JSON array containing exactly 5 objects:
[
  {
    "archetype": "Shot 1: Wide Context & Environment",
    "prompt": "Detailed paragraph of 80-160 words in English ending with [Aspect Ratio: {aspect_ratio}]"
  },
  ...
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


def parse_enhancer_response(text: str, aspect_ratio: str) -> List[Dict[str, str]]:
    """Parse Gemini JSON response into a list of archetype prompt dictionaries."""
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

    parsed_items: List[Dict[str, str]] = []
    for idx, item in enumerate(data):
        arch_meta = PROMPT_ARCHETYPES[idx % len(PROMPT_ARCHETYPES)]
        if isinstance(item, dict):
            prompt_str = item.get("prompt", "") or item.get("text", "") or ""
            arch_title = item.get("archetype") or arch_meta["title"]
            badge = item.get("badge") or arch_meta["badge"]
            badge_class = item.get("badge_class") or arch_meta["badge_class"]
        else:
            prompt_str = str(item)
            arch_title = arch_meta["title"]
            badge = arch_meta["badge"]
            badge_class = arch_meta["badge_class"]

        formatted_prompt = _format_with_aspect_ratio(prompt_str, aspect_ratio)
        if formatted_prompt:
            parsed_items.append({
                "archetype": arch_title,
                "badge": badge,
                "badge_class": badge_class,
                "prompt": formatted_prompt,
            })

    if not parsed_items:
        raise TransientError("Empty list of prompts returned by enhancer")

    return parsed_items


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

    archetypes_spec = "\n".join(
        f"  - {a['title']}: {a['guidance']}" for a in PROMPT_ARCHETYPES
    )

    parts = [
        f"Base concept/subject: {base_idea.strip()}",
        f"Aesthetic/Style: {style.name}: {style.directive}",
        f"Target Aspect Ratio: {aspect_ratio} ({ratio_desc}), append '[Aspect Ratio: {aspect_ratio}]' at the end of each prompt.",
    ]
    if light_desc:
        parts.append(f"Primary lighting base: {light_desc}")
    if cam_desc:
        parts.append(f"Camera aesthetic base: {cam_desc}")
    if comp_desc:
        parts.append(f"User composition preference: {comp_desc}")

    parts.append(
        "MANDATORY 5-SHOT DIVERSIFICATION MATRIX (You MUST produce 1 distinct prompt for each of these 5 shots to prevent microstock duplicate submission rejection):\n"
        f"{archetypes_spec}"
    )
    parts.append(
        "MANDATORY UNIVERSAL EXCLUSIONS: Strictly NO female characters, NO women, NO visible facial features; "
        "all living beings must be completely faceless. Prioritize inanimate objects, architecture, food, nature, tools, or faceless subjects."
    )
    parts.append(
        f"Output exactly 5 distinct prompts in JSON format ending with [Aspect Ratio: {aspect_ratio}]."
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
) -> List[Dict[str, str]]:
    """Call the Gemini text model to produce 5 visually diversified commercial image prompts."""
    if not base_idea or not base_idea.strip():
        raise ValueError("Please enter a base idea first.")

    def _call() -> List[Dict[str, str]]:
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
