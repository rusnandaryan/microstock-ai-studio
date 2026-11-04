"""Smoke and regression tests for Microstock AI Studio core pipeline.

Tests image padding, resolution enforcement, vision preparation, and upscaler logic.
Uses standard Python unittest (no external test runner dependencies needed).
"""
import io
import json
import unittest
from PIL import Image

from microstock import config, folder_watcher
from microstock.export import (
    build_metadata_dataframe,
    build_zip,
    to_adobe_stock_df,
    to_shutterstock_df,
)
from microstock.image_generator import BatchItem, _pad_jpeg_to_min_size, finalize_image
from microstock.metadata import ImageMetadata, _prepare_vision_bytes, normalize_keywords
from microstock.reverse_prompt import _detect_ratio
from microstock.trend_analyzer import _parse_trends_json
from microstock.upscaler import is_upscale_needed


def _create_sample_jpeg(width: int = 200, height: int = 200, color: str = "red") -> bytes:
    """Helper to generate a valid in-memory JPEG byte string."""
    im = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class TestJpegPadding(unittest.TestCase):
    def test_pad_jpeg_increases_file_size_without_corrupting(self):
        original_jpeg = _create_sample_jpeg(100, 100)
        orig_len = len(original_jpeg)
        target_size = orig_len + 50_000

        padded = _pad_jpeg_to_min_size(original_jpeg, target_size)

        self.assertGreaterEqual(len(padded), target_size)
        self.assertTrue(padded.startswith(b"\xff\xd8"), "JPEG must start with SOI marker")
        self.assertTrue(padded.endswith(b"\xff\xd9"), "JPEG must end with EOI marker")

        # Verify that PIL can open and verify the padded JPEG without error
        with Image.open(io.BytesIO(padded)) as im:
            im.verify()

    def test_pad_jpeg_noop_when_already_large_enough(self):
        original_jpeg = _create_sample_jpeg(100, 100)
        padded = _pad_jpeg_to_min_size(original_jpeg, 100)
        self.assertEqual(original_jpeg, padded)


class TestFinalizeImage(unittest.TestCase):
    def test_enforce_microstock_min_resolution(self):
        # 400x400 = 0.16 MP (far below 4.0 MP microstock requirement)
        small_jpeg = _create_sample_jpeg(400, 400)
        exp_bytes, prev_bytes, mime, w, h = finalize_image(
            small_jpeg,
            export_format="JPEG",
            enforce_microstock_res=True,
        )

        total_pixels = w * h
        self.assertGreaterEqual(total_pixels, config.TARGET_MIN_PIXELS)
        self.assertEqual(mime, "image/jpeg")

    def test_smart_microstock_max_target_pixels(self):
        # 4000x3000 = 12.0 MP (exceeds Smart Microstock target ~8.3 MP)
        large_jpeg = _create_sample_jpeg(4000, 3000)
        exp_bytes, prev_bytes, mime, w, h = finalize_image(
            large_jpeg,
            export_format="JPEG",
            enforce_microstock_res=False,
            max_target_pixels=config.SMART_MICROSTOCK_TARGET_PIXELS,
        )

        total_pixels = w * h
        self.assertLessEqual(total_pixels, config.SMART_MICROSTOCK_TARGET_PIXELS + 1000)

    def test_enforce_min_filesize_padding(self):
        sample = _create_sample_jpeg(200, 200)
        exp_bytes, prev_bytes, mime, w, h = finalize_image(
            sample,
            export_format="JPEG",
            enforce_min_filesize=True,
        )
        self.assertGreaterEqual(len(exp_bytes), config.MIN_FILE_SIZE_BYTES)


class TestVisionPreparation(unittest.TestCase):
    def test_downscales_large_image_and_converts_to_rgb(self):
        # Create 3000x1500 RGBA image
        im = Image.new("RGBA", (3000, 1500), color=(255, 0, 0, 128))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        raw_rgba = buf.getvalue()

        safe_bytes, safe_mime = _prepare_vision_bytes(raw_rgba, "image/png")

        self.assertEqual(safe_mime, "image/jpeg")
        with Image.open(io.BytesIO(safe_bytes)) as out_im:
            self.assertEqual(out_im.mode, "RGB")
            self.assertLessEqual(max(out_im.size), 2048)


class TestUpscalerLogic(unittest.TestCase):
    def test_is_upscale_needed(self):
        # 1000x1000 = 1 MP -> Needed (< 4.2 MP)
        self.assertTrue(is_upscale_needed(1000, 1000))
        # 3000x2000 = 6 MP -> Not needed (>= 4.2 MP)
        self.assertFalse(is_upscale_needed(3000, 2000))

    def test_run_upscale_missing_binary(self):
        from unittest.mock import patch
        from microstock.upscaler import run_upscale
        with patch("microstock.upscaler.get_upscaler_binary_path", return_value=None):
            success, err = run_upscale("dummy_in.jpg", "dummy_out.jpg")
            self.assertFalse(success)
            self.assertIn("tidak ditemukan", err)

    def test_run_upscale_timeout_handled(self):
        import subprocess
        from unittest.mock import patch
        from microstock.upscaler import run_upscale
        with patch("microstock.upscaler.get_upscaler_binary_path", return_value="/bin/dummy"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="realesrgan", timeout=1)):
                success, err = run_upscale("dummy_in.jpg", "dummy_out.jpg", timeout=1)
                self.assertFalse(success)
                self.assertIn("melebihi batas waktu", err)


class TestFallbackMetadata(unittest.TestCase):
    def test_create_fallback_metadata_cleans_filename(self):
        from microstock.metadata import create_fallback_metadata
        md = create_fallback_metadata("vintage_coffee_cup-01.jpg")
        self.assertEqual(md.title, "Vintage Coffee Cup 01")
        self.assertIn("coffee", md.keywords)
        self.assertEqual(md.adobe_category, 12)


class TestKeywordSanitization(unittest.TestCase):
    def test_normalize_keywords_removes_duplicates_and_strips(self):
        raw = [" Nature", "nature", "LANDSCAPE", "outdoor", "nature", "tree "]
        cleaned = normalize_keywords(raw)
        self.assertEqual(cleaned, ["nature", "landscape", "outdoor", "tree"])

    def test_normalize_keywords_preserves_ss_and_handles_plurals(self):
        raw = ["glass", "glasses", "business", "trees", "tree", "boxes", "box"]
        cleaned = normalize_keywords(raw)
        self.assertIn("glass", cleaned)
        self.assertNotIn("glasses", cleaned)
        self.assertIn("business", cleaned)
        self.assertIn("trees", cleaned)
        self.assertNotIn("tree", cleaned)
        self.assertIn("boxes", cleaned)
        self.assertNotIn("box", cleaned)


class TestMetadataHelpers(unittest.TestCase):
    def test_clamp_title(self):
        from microstock.metadata import clamp_title
        self.assertEqual(clamp_title("  Clean Office Desk.  "), "Clean Office Desk")
        long_title = "A " * 60  # 120 chars
        clamped = clamp_title(long_title, limit=100)
        self.assertLessEqual(len(clamped), 100)
        self.assertFalse(clamped.endswith(" "))

    def test_clamp_description(self):
        from microstock.metadata import clamp_description
        self.assertEqual(clamp_description("A serene landscape."), "A serene landscape.")
        long_desc = "Word " * 50
        clamped = clamp_description(long_desc, limit=200)
        self.assertLessEqual(len(clamped), 200)
        self.assertTrue(clamped.endswith("."))

    def test_parse_json(self):
        from microstock.metadata import _parse_json
        from microstock.rate_limit import TransientError
        self.assertEqual(_parse_json('{"key": "value"}'), {"key": "value"})
        self.assertEqual(_parse_json('```json\n{"key": "value"}\n```'), {"key": "value"})
        self.assertEqual(_parse_json('Analysis result:\n```json\n{"key": "value"}\n```\nDone.'), {"key": "value"})
        with self.assertRaises(TransientError):
            _parse_json("not json")

    def test_metadata_schema_valid_for_genai(self):
        from google.genai import types
        from microstock.metadata import METADATA_SCHEMA, SUPPLEMENT_SCHEMA
        s_main = types.Schema.model_validate(METADATA_SCHEMA)
        self.assertIsNotNone(s_main)
        s_sup = types.Schema.model_validate(SUPPLEMENT_SCHEMA)
        self.assertIsNotNone(s_sup)

    def test_generate_metadata_from_vision_async_mocked(self):
        import asyncio
        from unittest.mock import MagicMock
        from microstock.metadata import generate_metadata_from_vision_async

        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "title": "Fresh Organic Apples in Wooden Box",
            "description": "High quality commercial shot of fresh organic apples in a wooden crate.",
            "keywords": [f"keyword{i}" for i in range(50)],
            "adobe_category": "Food",
            "shutterstock_categories": ["Food and drink"],
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp

        # Create 100x100 dummy JPEG bytes
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), color="red").save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        md = asyncio.run(generate_metadata_from_vision_async(
            client=mock_client,
            image_bytes=raw_bytes,
            mime_type="image/jpeg",
        ))

        self.assertEqual(md.adobe_category, 7)  # "Food" maps to 7
        self.assertIn("Food and drink", md.shutterstock_categories)
        self.assertEqual(len(md.keywords), 50)
        self.assertTrue(len(md.title) > 0)


class TestFolderWatcher(unittest.TestCase):
    def test_get_cutoff_timestamp(self):
        cutoff_15m = folder_watcher.get_cutoff_timestamp("15 Menit Terakhir (Sesi Sekarang)")
        self.assertIsNotNone(cutoff_15m)
        cutoff_all = folder_watcher.get_cutoff_timestamp("Semua File Gambar Terbaru")
        self.assertIsNone(cutoff_all)

    def test_check_pending_downloads_nonexistent_dir(self):
        count = folder_watcher.check_pending_downloads("/nonexistent_folder_path_xyz")
        self.assertEqual(count, 0)


class TestReversePromptHelpers(unittest.TestCase):
    def test_detect_ratio(self):
        self.assertEqual(_detect_ratio(1920, 1080), "16:9")
        self.assertEqual(_detect_ratio(1080, 1920), "9:16")
        self.assertEqual(_detect_ratio(1000, 1000), "1:1")
        self.assertEqual(_detect_ratio(1600, 1200), "4:3")
        self.assertEqual(_detect_ratio(1200, 1600), "3:4")


class TestTrendAnalyzerParser(unittest.TestCase):
    def test_parse_trends_json_markdown_wrapped(self):
        sample_items = [
            {
                "event_name": f"Event {i}",
                "target_date": f"{i} Mei",
                "market_status": "Viral",
                "reason": "Liputan media tinggi",
                "ideas": [f"Visual A {i}", f"Visual B {i}", f"Visual C {i}"],
                "recommended_cat": "Fotografi (Photorealism)",
                "recommended_style": "Foto Komersial Bersih",
                "recommended_ratio": "16:9",
            }
            for i in range(1, 11)
        ]
        markdown_str = f"```json\n{json.dumps(sample_items)}\n```"
        parsed = _parse_trends_json(markdown_str, "31 October 2026")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["period"], "31 October 2026")
        self.assertEqual(len(parsed["trends"]), 10)
        self.assertEqual(parsed["trends"][0]["category"], "Event 1")
        self.assertEqual(parsed["trends"][0]["target_date"], "1 Mei")
        self.assertEqual(len(parsed["trends"][0]["ideas"]), 3)
        self.assertEqual(parsed["trends"][0]["base_idea"], "Visual A 1")

    def test_parse_trends_json_dict_format(self):
        dict_str = json.dumps({
            "trends": [
                {"category": "Earth Day", "target_date": "22 April", "reason": "Awareness", "base_idea": "Tree planting"}
            ]
        })
        parsed = _parse_trends_json(dict_str, "31 October 2026")
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed["trends"]), 1)
        self.assertEqual(parsed["trends"][0]["event_name"], "Earth Day")
        # Synthesizes at least 3-4 commercial angles automatically when input has only 1 base_idea
        self.assertGreaterEqual(len(parsed["trends"][0]["ideas"]), 3)
        self.assertTrue(parsed["trends"][0]["base_idea"].startswith("Tree planting"))

    def test_ensure_trend_variations_synthesizes_multiple_angles(self):
        from microstock.trend_analyzer import ensure_trend_variations
        raw_trend = {"event_name": "World Water Day", "base_idea": "Clean drop of water"}
        variations = ensure_trend_variations(raw_trend)
        self.assertGreaterEqual(len(variations), 4)
        self.assertTrue(any("close-up" in v.lower() for v in variations))
        self.assertTrue(any("flat lay" in v.lower() for v in variations))


class TestExportHub(unittest.TestCase):
    def setUp(self):
        self.meta = ImageMetadata(
            title="Modern Office Desk",
            description="Minimalist workstation with laptop and coffee cup.",
            keywords=["office", "desk", "laptop", "coffee", "minimalist"],
            adobe_category=3,
            shutterstock_categories=["Business/Finance", "Technology"],
        )
        self.sample_bytes = _create_sample_jpeg(400, 300)
        self.item = BatchItem(
            index=0,
            variation="desk",
            final_prompt="A clean desk",
            filename="desk.jpg",
            image_bytes=self.sample_bytes,
            preview_bytes=self.sample_bytes,
            mime_type="image/jpeg",
            width=400,
            height=300,
            metadata=self.meta,
        )

    def test_build_metadata_dataframe(self):
        df = build_metadata_dataframe([self.item])
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["Filename"], "desk.jpg")
        self.assertEqual(df.iloc[0]["Title"], "Modern Office Desk")
        self.assertEqual(df.iloc[0]["Adobe Category"], 3)

    def test_to_adobe_stock_df(self):
        master_df = build_metadata_dataframe([self.item])
        adobe_df = to_adobe_stock_df(master_df)
        expected_cols = ["Filename", "Title", "Keywords", "Category", "Releases"]
        self.assertEqual(list(adobe_df.columns), expected_cols)
        self.assertEqual(adobe_df.iloc[0]["Filename"], "desk.jpg")

    def test_to_shutterstock_df(self):
        master_df = build_metadata_dataframe([self.item])
        ss_df = to_shutterstock_df(master_df, [self.item])
        expected_cols = ["Filename", "Description", "Keywords", "Categories", "Editorial", "Mature content", "illustration"]
        self.assertEqual(list(ss_df.columns), expected_cols)
        self.assertEqual(ss_df.iloc[0]["Filename"], "desk.jpg")
        self.assertEqual(ss_df.iloc[0]["illustration"], "no")

    def test_to_shutterstock_df_infers_illustration_from_keywords_or_category(self):
        meta_illu = ImageMetadata(
            title="Abstract 3D Vector Icon",
            description="Minimalist 3D vector illustration.",
            keywords=["vector", "illustration", "3d render", "icon"],
            adobe_category=8,
            shutterstock_categories=["Arts", "Abstract"],
        )
        item_illu = BatchItem(
            index=0,
            variation="vector",
            final_prompt="3d vector",
            filename="vector.jpg",
            image_bytes=self.sample_bytes,
            metadata=meta_illu,
        )
        master_df = build_metadata_dataframe([item_illu])
        ss_df = to_shutterstock_df(master_df, [item_illu])
        self.assertEqual(ss_df.iloc[0]["illustration"], "yes")


    def test_build_zip_packages_files(self):
        import zipfile
        zip_bytes = build_zip([self.item], None)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            namelist = zf.namelist()
            self.assertIn("desk.jpg", namelist)
            self.assertIn("metadata.csv", namelist)
            self.assertIn("adobe_stock.csv", namelist)
            self.assertIn("shutterstock.csv", namelist)
            self.assertIn("README.txt", namelist)


class TestConfigKeyStore(unittest.TestCase):
    def test_save_load_delete_api_key(self):
        import tempfile
        import os
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_env = os.path.join(tmp_dir, ".env")
            with patch("microstock.config.get_env_file_path", return_value=fake_env):
                config.save_api_key("test_api_key_12345")
                loaded = config.load_saved_api_key()
                self.assertEqual(loaded, "test_api_key_12345")

                config.delete_saved_api_key()
                loaded_after = config.load_saved_api_key()
                self.assertIsNone(loaded_after)

    def test_read_env_flexible_formatting(self):
        import tempfile
        import os
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_env = os.path.join(tmp_dir, ".env")
            with open(fake_env, "w") as f:
                f.write('export GOOGLE_API_KEY = "flex_key_999"\n')
            with patch("microstock.config.get_env_file_path", return_value=fake_env):
                self.assertEqual(config.load_saved_api_key(), "flex_key_999")

    def test_resolve_api_key_precedence(self):
        from unittest.mock import patch
        # 1. User supplied takes highest priority
        self.assertEqual(config.resolve_api_key("direct_key"), "direct_key")

        # 2. Saved .env file takes precedence over env vars
        with patch("microstock.config._read_env_file", return_value="env_file_key"):
            with patch.dict("os.environ", {"GEMINI_API_KEY": "ambient_os_key"}):
                self.assertEqual(config.resolve_api_key(), "env_file_key")


class TestCliInterface(unittest.TestCase):
    def test_cli_help_runs_cleanly(self):
        import subprocess
        import sys
        res = subprocess.run([sys.executable, "cli.py", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("prompt", res.stdout)
        self.assertIn("process", res.stdout)
        self.assertIn("reverse", res.stdout)
        self.assertIn("trends", res.stdout)
        self.assertIn("gui", res.stdout)


class TestPromptEnhancer(unittest.TestCase):
    def test_format_with_aspect_ratio(self):
        from microstock.prompt_enhancer import _format_with_aspect_ratio
        res = _format_with_aspect_ratio("A clean coffee cup", "16:9")
        self.assertEqual(res, "A clean coffee cup [Aspect Ratio: 16:9]")

        res2 = _format_with_aspect_ratio("A clean coffee cup [Aspect Ratio: 1:1]", "16:9")
        self.assertEqual(res2, "A clean coffee cup [Aspect Ratio: 16:9]")

    def test_parse_enhancer_response(self):
        from microstock.prompt_enhancer import parse_enhancer_response
        res = parse_enhancer_response("A minimal ceramic vase", "4:3")
        self.assertEqual(res, "A minimal ceramic vase [Aspect Ratio: 4:3]")

        json_payload = '```json\n{"prompt": "A modern glass teapot"}\n```'
        res2 = parse_enhancer_response(json_payload, "1:1")
        self.assertEqual(res2, "A modern glass teapot [Aspect Ratio: 1:1]")

    def test_build_enhancer_input(self):
        from microstock.prompt_enhancer import build_enhancer_input
        prompt_input = build_enhancer_input(
            base_idea="Minimalist wooden desk",
            style_name="Fotografi (Photorealism)",
            aspect_ratio="16:9",
        )
        self.assertIn("Minimalist wooden desk", prompt_input)
        self.assertIn("16:9", prompt_input)


class TestUpscalerBytes(unittest.TestCase):
    def test_upscale_bytes_fallback_when_binary_missing(self):
        from unittest.mock import patch
        from microstock.upscaler import upscale_bytes
        sample = _create_sample_jpeg(100, 100)
        with patch("microstock.upscaler.get_upscaler_binary_path", return_value=None):
            result, success, err = upscale_bytes(sample)
            self.assertFalse(success)
            self.assertEqual(result, sample)
            self.assertIn("tidak ditemukan", err)


class TestReversePromptSave(unittest.TestCase):
    def test_save_prompt_avoids_overwriting(self):
        import tempfile
        import os
        from unittest.mock import patch
        from microstock.reverse_prompt import save_prompt_to_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("microstock.reverse_prompt.os.path.abspath", return_value=os.path.join(tmp_dir, "mock")):
                p1 = save_prompt_to_file("Prompt 1", "test.jpg")
                p2 = save_prompt_to_file("Prompt 2", "test.jpg")
                self.assertNotEqual(p1, p2)
                self.assertTrue(os.path.exists(p1))
                self.assertTrue(os.path.exists(p2))


class TestFolderWatcherLimit(unittest.TestCase):
    def test_read_image_bytes_skips_large_file(self):
        import tempfile
        from unittest.mock import patch, mock_open
        from microstock.folder_watcher import read_image_bytes

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            with patch("builtins.open", mock_open(read_data=b"x" * (51 * 1024 * 1024))):
                res = read_image_bytes(tmp.name)
                self.assertIsNone(res)


class TestCliArgParser(unittest.TestCase):
    def test_cli_subcommand_accepts_api_key_flag(self):
        import sys
        from unittest.mock import patch
        import cli
        test_argv = ["cli.py", "prompt", "test idea", "--api-key", "my_test_key"]
        with patch.object(sys, "argv", test_argv):
            # Capture parser created in main
            with patch("cli.cmd_prompt") as mock_func:
                cli.main()
                mock_func.assert_called_once()
                args = mock_func.call_args[0][0]
                self.assertEqual(args.api_key, "my_test_key")
                self.assertEqual(args.idea, "test idea")


class TestUiThemeSupport(unittest.TestCase):
    def test_get_modern_css_dark_and_light(self):
        from microstock.ui_components import get_modern_css
        dark_css = get_modern_css(is_dark=True)
        self.assertIn("color-scheme: dark", dark_css)
        self.assertIn("--bg-page: #06080D", dark_css)

        light_css = get_modern_css(is_dark=False)
        self.assertIn("color-scheme: light", light_css)
        self.assertIn("--bg-page: #F8FAFC", light_css)


if __name__ == "__main__":
    unittest.main()
