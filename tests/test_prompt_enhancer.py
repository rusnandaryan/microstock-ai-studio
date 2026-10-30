"""Unit tests for single prompt enhancer parsing and input generation."""
import unittest

from microstock.prompt_enhancer import (
    build_enhancer_input,
    parse_enhancer_response,
    _format_with_aspect_ratio,
)


class TestPromptEnhancerParsing(unittest.TestCase):
    def test_format_with_aspect_ratio_appends_tag(self):
        text = "A clean minimalist espresso cup on oak wood table."
        formatted = _format_with_aspect_ratio(text, "16:9")
        self.assertTrue(formatted.endswith("[Aspect Ratio: 16:9]"))
        self.assertIn("espresso cup", formatted)

    def test_format_with_aspect_ratio_replaces_existing_tag(self):
        text = "A clean minimalist espresso cup [Aspect Ratio: 1:1]"
        formatted = _format_with_aspect_ratio(text, "9:16")
        self.assertTrue(formatted.endswith("[Aspect Ratio: 9:16]"))
        self.assertNotIn("1:1", formatted)

    def test_parse_plain_text(self):
        text = "Commercial stock photo of an artisanal ceramic cup on dark granite surface."
        result = parse_enhancer_response(text, "1:1")
        self.assertTrue(result.endswith("[Aspect Ratio: 1:1]"))
        self.assertIn("ceramic cup", result)

    def test_parse_markdown_wrapped_response(self):
        markdown_text = """```
        Commercial advertising photo of a modern eco cup with negative space.
        ```"""
        result = parse_enhancer_response(markdown_text, "16:9")
        self.assertTrue(result.endswith("[Aspect Ratio: 16:9]"))
        self.assertIn("negative space", result)

    def test_parse_json_fallback(self):
        json_str = """
        [
            "A modern ceramic cup in natural window sunlight."
        ]
        """
        result = parse_enhancer_response(json_str, "4:3")
        self.assertTrue(result.endswith("[Aspect Ratio: 4:3]"))
        self.assertIn("ceramic cup", result)

    def test_build_enhancer_input_preserves_all_parameters(self):
        user_input = build_enhancer_input(
            base_idea="artisanal ceramic cup",
            style_name="📷 Foto Komersial Bersih (Commercial Advertising)",
            aspect_ratio="16:9",
            lighting="Golden Hour / Warm Sunset",
            camera="100mm Macro (Extreme Detail)",
            composition="Negative Space for Copy / Headline",
        )
        self.assertIn("MANDATORY Lighting condition: Warm golden hour sunlight", user_input)
        self.assertIn("MANDATORY Camera/Lens perspective: 100mm macro lens", user_input)
        self.assertIn("MANDATORY Composition framing: Clean composition with generous empty negative space", user_input)
        self.assertIn("Target Aspect Ratio: 16:9", user_input)
        self.assertIn("MANDATORY UNIVERSAL EXCLUSIONS", user_input)
        self.assertIn("Generate 1 high-quality commercial prompt", user_input)


if __name__ == "__main__":
    unittest.main()
