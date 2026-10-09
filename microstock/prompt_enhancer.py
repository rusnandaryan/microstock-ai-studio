"""AI Prompt Enhancer: expands a short base idea into a pro image prompt."""
from __future__ import annotations

from typing import Callable, Optional

from google import genai

from . import config
from .rate_limit import TransientError, retry_sync

ENHANCER_SYSTEM_INSTRUCTION = """\
You are an elite art director and prompt engineer specializing in top-selling commercial microstock imagery compliant with official Adobe Stock & Shutterstock Generative AI Content Guidelines.

Rewrite the user's short idea into 5 highly detailed, production-ready, ultra-clean image generation prompts.

CRITICAL ADOBE STOCK COMPLIANCE & COMMERCIAL RULES (STRICT ENFORCEMENT):

1. ZERO FEMALE CHARACTERS (STRICT RULE):
   - NO female characters, women, girls, or feminine figures in ANY form (human, silhouette, cyborg, humanoid robot, or illustration).
   - Depict ONLY male figures (faceless), gender-neutral hands/silhouettes, or purely focus on inanimate objects, architecture, food, nature, tools, or concepts.

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
   - Explicitly describe framing matching the target aspect ratio.
   - You MUST end each prompt with the text "[Aspect Ratio: {aspect_ratio}]".

Output a valid JSON array containing exactly 5 alternative prompt strings. Each string must be a highly detailed paragraph of 80-160 words in English ending with the Aspect Ratio tag. Provide completely distinct concepts/perspectives for each alternative. Do not output anything other than the JSON array.
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
