"""AI Prompt Enhancer: expands a short base idea into a pro image prompt."""
from __future__ import annotations

from typing import Callable, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync

ENHANCER_SYSTEM_INSTRUCTION = """\
You are an elite art director and prompt engineer specializing in top-selling commercial microstock imagery compliant with official Adobe Stock Generative AI Content Guidelines.

Rewrite the user's short idea into ONE highly detailed, production-ready image generation prompt.

CRITICAL ADOBE STOCK GENERATIVE AI GUIDELINES & COMPLIANCE RULES:
1. THIRD-PARTY RIGHTS & INTELLECTUAL PROPERTY (ZERO TOLERANCE):
   - NO real people or celebrities: Never name real people, public figures, celebrities, or recognizable individuals.
   - NO artist names: Never reference other artists, illustrators, or photographers.
   - NO brands, logos, or trademarks: Never describe branded clothing or tech gadgets. All props must be generic.
   - NO private landmarks or copyrighted architectural structures.

2. MANDATORY FACELESS RULE (ZERO TOLERANCE):
   - If the prompt features ANY living creatures (humans, animals, insects) or humanoid robots, their faces MUST NOT be fully visible.
   - You MUST use techniques to hide the face: "shot from behind", "face hidden in shadows", "wearing an opaque mask/helmet", "cropped at the neck", "silhouette", or "facing away from the camera".

3. ANATOMICAL & TECHNICAL QUALITY STANDARDS:
   - Flawless human and animal anatomy: Exactly five fingers per hand, accurate limb attachments.
   - Professional photographic lighting and clean commercial composition with generous negative space.
   - Pristine visual clarity: NO blurry AI artifacts, NO readable text, NO signatures.

4. COMMERCIAL MICROSTOCK RELEVANCE:
   - Depict authentic human interactions (faceless), rich physical textures, and cohesive color palettes.
   - Strictly honor and reinforce the user's chosen aesthetic style.

5. MANDATORY ASPECT RATIO & ORIENTATION:
   - Explicitly mention the scene framing corresponding to the target aspect ratio within the prompt.
   - You MUST end each prompt with the text "[Aspect Ratio: {aspect_ratio}]".

Output a valid JSON array containing exactly 5 alternative prompt strings. Each string must be a highly detailed paragraph of 80-160 words in English ending with the Aspect Ratio tag. Provide completely different concepts/angles for each alternative. Do not output anything other than the JSON array.
"""


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
        f"Aesthetic/Style: {style.name} — {style.directive}",
        f"Target Aspect Ratio: {aspect_ratio} ({ratio_desc}) — MANDATORY: explicitly include '{aspect_ratio}' in the composition description and append '[Aspect Ratio: {aspect_ratio}]' at the end of the prompt",
    ]
    if light_desc:
        parts.append(f"Lighting condition: {light_desc}")
    if cam_desc:
        parts.append(f"Camera/Lens perspective: {cam_desc}")
    if comp_desc:
        parts.append(f"Composition framing: {comp_desc}")

    parts.append(
        "Write 5 alternative detailed, coherent, photography/art-grade prompts in English that blend all these directives naturally, in the requested JSON format."
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
    """Call the Gemini text model to produce detailed image prompts."""
    if not base_idea or not base_idea.strip():
        raise ValueError("Please enter a base idea first.")

    import re
    import json

    def _format_with_aspect_ratio(raw_text: str) -> str:
        clean = (raw_text or "").strip().strip('"').strip()
        if not clean:
            return ""
        # Check if an existing [Aspect Ratio: ...] tag exists
        if re.search(r"\[Aspect Ratio:\s+\d+:\d+\]", clean, re.IGNORECASE):
            clean = re.sub(r"\[Aspect Ratio:\s+\d+:\d+\]", f"[Aspect Ratio: {aspect_ratio}]", clean, flags=re.IGNORECASE)
        else:
            clean = f"{clean} [Aspect Ratio: {aspect_ratio}]"
        return clean

    def _parse_and_format(text: str) -> List[str]:
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        try:
            arr = json.loads(text.strip())
            return [_format_with_aspect_ratio(str(item)) for item in arr if str(item).strip()]
        except Exception as e:
            raise TransientError(f"Failed to parse JSON: {e}")

    def _call() -> List[str]:
        prompt_input = build_enhancer_input(base_idea, style_name, aspect_ratio, lighting, camera, composition)
        last_err = None
        # Try primary model then fallbacks if 503 UNAVAILABLE or 404 NOT_FOUND
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        temperature=0.8,
                        max_output_tokens=1500,
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_input,
                        config=config_obj,
                    )
                    text = (response.text or "").strip()
                    if text:
                        return _parse_and_format(text)
                elif hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        input=prompt_input,
                        store=False,
                    )
                    text = (interaction.output_text or "").strip()
                    if text:
                        return _parse_and_format(text)
            except Exception as e:
                last_err = e
                # If high demand (503) or not found (404), try next fallback model
                err_str = str(e).lower()
                if "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "404" in err_str:
                    continue
                raise

        if last_err:
            raise last_err
        raise TransientError("Empty response from prompt enhancer")

    return retry_sync(_call, label="Prompt enhancement", on_retry=on_retry)
