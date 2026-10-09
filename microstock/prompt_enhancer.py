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
   - NO real people or celebrities: Never name real people, public figures, celebrities, or recognizable individuals. All people must be purely fictional.
   - NO artist names: Never reference other artists, illustrators, or photographers (e.g. NEVER write "in the style of [Artist]", "art by [Artist]").
   - NO brands, logos, or trademarks: Never describe branded clothing, tech gadgets (e.g. no Apple/iPhone logos, no Nike swoosh, no Starbucks cups), copyrighted characters (e.g. Marvel, Disney, anime characters), or proprietary product designs. All props and wardrobe must be completely unbranded, generic, and commercial-safe.
   - NO private landmarks or copyrighted architectural structures requiring property releases.

2. ANATOMICAL & TECHNICAL QUALITY STANDARDS:
   - Flawless human and animal anatomy: Exactly five fingers per hand, natural eye symmetry, accurate limb attachments, clean proportions, no extra or melted fingers/limbs.
   - Professional photographic lighting: True-to-life exposure, balanced highlights and shadows, physically accurate reflections.
   - Clean commercial composition: Include generous negative space (clean copy space) for commercial advertising headlines/copy where appropriate.
   - Pristine visual clarity: NO blurry AI artifacts, NO warped backgrounds, NO readable text, NO signatures, and NO watermarks.

3. COMMERCIAL MICROSTOCK RELEVANCE:
   - Depict authentic, candid, natural human interactions, relatable expressions, and diverse modern lifestyles.
   - Specify rich physical textures (fabrics, skin, wood, glass, metals) and cohesive color palettes.
   - Strictly honor and reinforce the user's chosen aesthetic style.

4. MANDATORY ASPECT RATIO & ORIENTATION:
   - Explicitly mention the scene framing corresponding to the target aspect ratio within the prompt (e.g. "16:9 widescreen composition", "9:16 vertical framing", "1:1 square composition", "4:3 landscape framing", or "3:4 portrait framing").
   - You MUST end the prompt with the text "[Aspect Ratio: {aspect_ratio}]" (e.g., "[Aspect Ratio: 16:9]", "[Aspect Ratio: 9:16]").

Output ONLY the final prompt as a single paragraph of 80-160 words in English ending with the Aspect Ratio tag.
No preamble, no quotes, no markdown, no bullet points.
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
        "Write ONE detailed, coherent, photography/art-grade prompt in English that blends all these directives naturally."
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
    """Call the Gemini text model to produce a detailed image prompt."""
    if not base_idea or not base_idea.strip():
        raise ValueError("Please enter a base idea first.")

    import re

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

    def _call() -> str:
        prompt_input = build_enhancer_input(base_idea, style_name, aspect_ratio, lighting, camera, composition)
        last_err = None
        # Try primary model then fallbacks if 503 UNAVAILABLE or 404 NOT_FOUND
        for model_name in config.TEXT_MODEL_FALLBACKS:
            try:
                if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    from google.genai import types
                    config_obj = types.GenerateContentConfig(
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=300,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_input,
                        config=config_obj,
                    )
                    text = (response.text or "").strip()
                    if text:
                        return _format_with_aspect_ratio(text)
                elif hasattr(client, "interactions"):
                    interaction = client.interactions.create(
                        model=model_name,
                        system_instruction=ENHANCER_SYSTEM_INSTRUCTION,
                        input=prompt_input,
                        store=False,
                    )
                    text = (interaction.output_text or "").strip()
                    if text:
                        return _format_with_aspect_ratio(text)
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
