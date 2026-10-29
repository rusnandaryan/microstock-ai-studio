"""Unit tests for prompt enhancer parsing and archetype diversification."""
import unittest

from microstock.prompt_enhancer import (
    PROMPT_ARCHETYPES,
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

    def test_parse_structured_json_with_archetypes(self):
        json_str = """
        [
            {"archetype": "Shot 1: Wide Context & Environment", "prompt": "Wide view of modern cafe."},
            {"archetype": "Shot 2: Macro & Material Craftsmanship", "prompt": "Close-up macro of ceramic cup grain."},
            {"archetype": "Shot 3: Dynamic Interaction / In-Use Action", "prompt": "Barista pouring latte art into cup."},
            {"archetype": "Shot 4: Clean Copy Space / Ad Layout", "prompt": "Espresso cup with clean negative space on right."},
            {"archetype": "Shot 5: Flat Lay Knolling / Geometric Angle", "prompt": "Overhead flat lay knolling of coffee beans and cup."}
        ]
        """
        results = parse_enhancer_response(json_str, "16:9")
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["archetype"], "Shot 1: Wide Context & Environment")
        self.assertTrue(results[0]["prompt"].endswith("[Aspect Ratio: 16:9]"))
        self.assertEqual(results[1]["badge"], "🔍 Macro Detail")
        self.assertEqual(results[4]["badge"], "🧩 Flat Lay / Knolling")

    def test_parse_fallback_string_array(self):
        # When Gemini returns a simple array of 5 strings, archetypes should be assigned automatically
        json_str = """
        [
            "Prompt one for wide scene.",
            "Prompt two for macro details.",
            "Prompt three for action.",
            "Prompt four for copy space.",
            "Prompt five for top down."
        ]
        """
        results = parse_enhancer_response(json_str, "1:1")
        self.assertEqual(len(results), 5)
        # Should map 0..4 to the 5 archetypes
        for idx in range(5):
            self.assertEqual(results[idx]["archetype"], PROMPT_ARCHETYPES[idx]["title"])
            self.assertEqual(results[idx]["badge"], PROMPT_ARCHETYPES[idx]["badge"])
            self.assertTrue(results[idx]["prompt"].endswith("[Aspect Ratio: 1:1]"))

    def test_parse_markdown_wrapped_json(self):
        json_str = """```json
        [
            {"archetype": "Shot 1: Wide Context & Environment", "prompt": "Modern office desk in natural sunlight."}
        ]
        ```"""
        results = parse_enhancer_response(json_str, "4:3")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["archetype"], "Shot 1: Wide Context & Environment")
        self.assertTrue(results[0]["prompt"].endswith("[Aspect Ratio: 4:3]"))


if __name__ == "__main__":
    unittest.main()
