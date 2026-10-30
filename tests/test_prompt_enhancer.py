"""Unit tests for prompt enhancer parsing."""
import unittest

from microstock.prompt_enhancer import (
    SCENARIO_DESCRIPTIONS,
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

    def test_parse_string_array(self):
        json_str = """
        [
            "Prompt one for scene.",
            "Prompt two for scene.",
            "Prompt three for scene.",
            "Prompt four for scene.",
            "Prompt five for scene."
        ]
        """
        results = parse_enhancer_response(json_str, "1:1")
        self.assertEqual(len(results), 5)
        for idx in range(5):
            self.assertTrue(results[idx].endswith("[Aspect Ratio: 1:1]"))

    def test_parse_object_array_fallback(self):
        json_str = """
        [
            {"prompt": "A modern eco cup with negative space on right."},
            {"prompt": "A ceramic cup in natural window sunlight."}
        ]
        """
        results = parse_enhancer_response(json_str, "16:9")
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].endswith("[Aspect Ratio: 16:9]"))
        self.assertIn("negative space", results[0])

    def test_parse_markdown_wrapped_json(self):
        json_str = """```json
        [
            "Modern office desk in natural sunlight."
        ]
        ```"""
        results = parse_enhancer_response(json_str, "4:3")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].endswith("[Aspect Ratio: 4:3]"))

    def test_scenario_descriptions_length_and_structure(self):
        self.assertEqual(len(SCENARIO_DESCRIPTIONS), 5)
        for label, desc in SCENARIO_DESCRIPTIONS:
            self.assertTrue(bool(label))
            self.assertTrue(bool(desc))

    def test_build_enhancer_input_preserves_parameters_and_injects_scenarios(self):
        user_input = build_enhancer_input(
            base_idea="artisanal ceramic cup",
            style_name="📷 Foto Komersial Bersih (Commercial Advertising)",
            aspect_ratio="16:9",
            lighting="Golden Hour / Warm Sunset",
            camera="100mm Macro (Extreme Detail)",
            composition="Negative Space for Copy / Headline",
        )
        # Check parameter preservation
        self.assertIn("MANDATORY Lighting condition", user_input)
        self.assertIn("MANDATORY Camera/Lens perspective", user_input)
        self.assertIn("MANDATORY Composition framing", user_input)
        self.assertIn("Target Aspect Ratio: 16:9", user_input)
        # Check scenario directives
        self.assertIn("MANDATORY 5-SCENARIO DIVERSIFICATION", user_input)
        self.assertIn("Scenario 1 (Pristine Hero)", user_input)
        self.assertIn("Scenario 2 (In-Action Dynamic Moment)", user_input)
        self.assertIn("Scenario 3 (Raw Materials & Origins)", user_input)
        self.assertIn("Scenario 4 (Lifestyle Pairing Context)", user_input)
        self.assertIn("Scenario 5 (Colorway & Mood Accent)", user_input)


if __name__ == "__main__":
    unittest.main()
