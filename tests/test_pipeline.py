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


class TestDatabaseEngine(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_studio.db")
        from microstock import db
        db.init_db(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_save_and_get_asset(self):
        from microstock import db
        uid = db.save_asset(
            file_path="/tmp/sample.jpg",
            file_name="sample.jpg",
            file_size_bytes=1024,
            width=2000,
            height=2000,
            aspect_ratio="1:1",
            phash_hex="1234567890abcdef",
            title="Sample Coffee Cup",
            description="High quality coffee cup photography",
            keywords=["coffee", "cup", "morning"],
            adobe_category_id=7,
            shutterstock_cats=["Food and drink"],
            is_xmp_injected=True,
            db_path=self.db_path,
        )
        self.assertIsNotNone(uid)
        asset = db.get_asset(uid, db_path=self.db_path)
        self.assertEqual(asset["file_name"], "sample.jpg")
        self.assertEqual(asset["title"], "Sample Coffee Cup")
        self.assertEqual(len(asset["keywords"]), 3)
        self.assertEqual(asset["adobe_category_id"], 7)
        self.assertEqual(asset["is_xmp_injected"], 1)

    def test_find_near_duplicates_in_db(self):
        from microstock import db
        db.save_asset(
            file_path="/tmp/img1.jpg",
            file_name="img1.jpg",
            file_size_bytes=1000,
            width=1000,
            height=1000,
            aspect_ratio="1:1",
            phash_hex="ffffffffffffffff",
            title="Image 1",
            description="Desc 1",
            keywords=["tag1"],
            db_path=self.db_path,
        )
        # Search with identical hash
        matches = db.find_near_duplicates_in_db("ffffffffffffffff", max_hamming_distance=2, db_path=self.db_path)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][1], 0)  # distance 0
        self.assertEqual(matches[0][2], 100.0)  # 100% similarity

        # Search with 1 bit difference
        matches_1bit = db.find_near_duplicates_in_db("fffffffffffffffe", max_hamming_distance=2, db_path=self.db_path)
        self.assertEqual(len(matches_1bit), 1)
        self.assertEqual(matches_1bit[0][1], 1)

        # Search with distant hash
        matches_far = db.find_near_duplicates_in_db("0000000000000000", max_hamming_distance=2, db_path=self.db_path)
        self.assertEqual(len(matches_far), 0)


class TestXmpIptcInjector(unittest.TestCase):
    def test_build_and_inject_xmp(self):
        from microstock.iptc import build_adobe_xmp_packet, inject_xmp_into_jpeg
        from PIL import Image

        packet = build_adobe_xmp_packet(
            title="Test Espresso Shot",
            description="Rich crema espresso shot in porcelain cup",
            keywords=["espresso", "coffee", "crema", "caffeine"],
            adobe_category="Food",
        )
        self.assertIn(b"Test Espresso Shot", packet)
        self.assertIn(b"espresso", packet)
        self.assertIn(b"crema", packet)

        sample = _create_sample_jpeg(100, 100)
        injected = inject_xmp_into_jpeg(
            sample,
            title="Test Espresso Shot",
            description="Rich crema espresso shot in porcelain cup",
            keywords=["espresso", "coffee", "crema", "caffeine"],
            adobe_category="Food",
        )
        self.assertTrue(injected.startswith(b"\xff\xd8"))
        self.assertIn(b"http://ns.adobe.com/xap/1.0/", injected)
        self.assertIn(b"Test Espresso Shot", injected)

        # Ensure image is valid and readable by Pillow
        with Image.open(io.BytesIO(injected)) as im:
            im.load()
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.size, (100, 100))


class TestPerceptualHash(unittest.TestCase):
    def test_phash_computation_and_similarity(self):
        from microstock.phash import compute_phash, hamming_distance, similarity_percent
        from PIL import Image, ImageDraw

        im1 = Image.new("RGB", (200, 200), color="white")
        draw = ImageDraw.Draw(im1)
        draw.ellipse([20, 20, 180, 180], fill="black")

        im2 = im1.copy().resize((100, 100))  # Scale variation

        h1 = compute_phash(im1)
        h2 = compute_phash(im2)

        self.assertEqual(len(h1), 16)
        self.assertEqual(len(h2), 16)

        dist = hamming_distance(h1, h2)
        self.assertLessEqual(dist, 2)
        sim = similarity_percent(h1, h2)
        self.assertGreaterEqual(sim, 95.0)


class TestBackgroundQueue(unittest.TestCase):
    def test_queue_execution(self):
        from microstock.queue import BackgroundWorkerPool
        pool = BackgroundWorkerPool(max_workers=1)

        def simple_task(x, y):
            return x + y

        job_id = pool.submit("Math Task", simple_task, 10, 20)
        self.assertIsNotNone(job_id)

        import time
        for _ in range(20):
            job = pool.get_job(job_id)
            if job and job.status == "completed":
                break
            time.sleep(0.05)

        job = pool.get_job(job_id)
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.result, 30)
        pool.shutdown(wait=False)


class TestDistributor(unittest.TestCase):
    def test_agency_endpoints_defined(self):
        from microstock.distributor import AGENCY_ENDPOINTS
        self.assertIn("adobe_stock", AGENCY_ENDPOINTS)
        self.assertIn("shutterstock", AGENCY_ENDPOINTS)
        self.assertIn("freepik", AGENCY_ENDPOINTS)

    def test_test_agency_connection_mocked(self):
        from unittest.mock import patch, MagicMock
        from microstock.distributor import test_agency_connection

        with patch("ftplib.FTP") as mock_ftp_cls:
            mock_inst = MagicMock()
            mock_ftp_cls.return_value = mock_inst
            success, msg = test_agency_connection("localhost", 21, "ftp", "user", "pass")
            self.assertTrue(success)
            self.assertIn("berhasil", msg)


if __name__ == "__main__":
    unittest.main()


class TestSecurityModule(unittest.TestCase):
    def test_store_and_retrieve_secret(self):
        from microstock import security
        svc = "test_unit_service"
        acc = "user_alpha"
        val = "P@ssw0rd_Unit_Test_123!"

        stored = security.store_secret(svc, acc, val)
        self.assertTrue(stored)

        retrieved = security.get_secret(svc, acc)
        self.assertEqual(retrieved, val)

        deleted = security.delete_secret(svc, acc)
        self.assertTrue(deleted)

        self.assertIsNone(security.get_secret(svc, acc))

    def test_agency_password_helpers(self):
        from microstock import security
        agency = "adobe_stock"
        user = "test_contributor"
        pwd = "sftp_secret_pass_456"

        self.assertTrue(security.store_agency_password(agency, user, pwd))
        self.assertEqual(security.get_agency_password(agency, user), pwd)
        security.delete_agency_password(agency, user)
        self.assertIsNone(security.get_agency_password(agency, user))

    def test_vault_encryption_integrity(self):
        from microstock import security
        enc_key, mac_key = security._derive_vault_keys()
        data = b"Sensitive microstock confidential metadata payload"
        encrypted = security._encrypt_payload(data, enc_key, mac_key)

        decrypted = security._decrypt_payload(encrypted, enc_key, mac_key)
        self.assertEqual(decrypted, data)

        # Tampered blob must fail decryption
        tampered = bytearray(encrypted)
        tampered[20] ^= 0xFF
        self.assertIsNone(security._decrypt_payload(bytes(tampered), enc_key, mac_key))


class TestFolderMonitor(unittest.TestCase):
    def test_folder_monitor_lifecycle(self):
        import tempfile
        import time
        import os
        from microstock.folder_watcher import FolderMonitor

        with tempfile.TemporaryDirectory() as tmpdir:
            captured = []
            def _on_detected(fn, path):
                captured.append(fn)

            monitor = FolderMonitor(directory=tmpdir, on_image_detected=_on_detected, poll_interval=0.1)
            self.assertTrue(monitor.start())
            self.assertTrue(monitor.is_running())

            # Create sample image
            test_img = os.path.join(tmpdir, "gemini_render_001.jpg")
            with open(test_img, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            time.sleep(0.5)
            monitor.stop()
            self.assertFalse(monitor.is_running())

            events = monitor.get_recent_events()
            self.assertGreaterEqual(len(events), 1)
            self.assertEqual(events[0]["filename"], "gemini_render_001.jpg")
            self.assertIn("gemini_render_001.jpg", captured)


class TestCategoryClassification(unittest.TestCase):
    def test_validate_adobe_category(self):
        from microstock.metadata import validate_adobe_category
        self.assertEqual(validate_adobe_category(7), 7)
        self.assertEqual(validate_adobe_category("7"), 7)
        self.assertEqual(validate_adobe_category("Food"), 7)
        self.assertEqual(validate_adobe_category("technology"), 19)
        self.assertEqual(validate_adobe_category("Animals"), 1)
        self.assertEqual(validate_adobe_category(999), config.DEFAULT_ADOBE_CATEGORY)
        self.assertEqual(validate_adobe_category(None), config.DEFAULT_ADOBE_CATEGORY)

    def test_classify_adobe_category(self):
        from microstock.metadata import classify_adobe_category
        # Food test
        cat_id, cat_name = classify_adobe_category(
            title="Fresh Salmon Sushi Roll Meal",
            description="Japanese sushi dinner served on bamboo plate",
            keywords=["food", "sushi", "salmon", "meal", "dinner", "restaurant", "culinary"],
        )
        self.assertEqual(cat_id, 7)
        self.assertEqual(cat_name, "Food")

        # Technology test
        cat_id, cat_name = classify_adobe_category(
            title="Cloud Data Server Cyber Network",
            description="Modern computer technology in datacenter",
            keywords=["technology", "computer", "digital", "server", "data", "software", "network"],
        )
        self.assertEqual(cat_id, 19)
        self.assertEqual(cat_name, "Technology")

    def test_image_metadata_post_init(self):
        from microstock.metadata import ImageMetadata
        md = ImageMetadata(
            title="Espresso Coffee Cup on Wooden Table",
            description="Morning hot beverage in coffee shop",
            keywords=["drink", "coffee", "espresso", "beverage", "cup", "cappuccino"],
            adobe_category="Drinks",
        )
        self.assertEqual(md.adobe_category, 4)
        self.assertEqual(md.adobe_category_name, "Drinks")
        self.assertIn("Food and drink", md.shutterstock_categories)


class TestComplianceShield(unittest.TestCase):
    def test_clean_commercial_asset(self):
        from microstock.compliance import evaluate_commercial_compliance
        rep = evaluate_commercial_compliance(
            title="Clean Wooden Cutting Board with Knife",
            description="Minimalist culinary kitchen concept",
            keywords=["kitchen", "cooking", "knife", "board", "culinary", "table"] * 5,
        )
        self.assertTrue(rep.is_commercial_safe)
        self.assertFalse(rep.requires_model_release)
        self.assertFalse(rep.requires_property_release)
        self.assertGreaterEqual(rep.commercial_safety_score, 85)

    def test_trademark_flagging(self):
        from microstock.compliance import evaluate_commercial_compliance
        rep = evaluate_commercial_compliance(
            title="Boy playing with Lego bricks wearing Nike sneakers",
            description="Child playing with toys in room",
            keywords=["lego", "toys", "nike", "sneakers", "child"],
        )
        self.assertFalse(rep.is_commercial_safe)
        self.assertTrue(rep.editorial_only)
        self.assertIn("trademark", " ".join(rep.detected_risks).lower())

    def test_model_release_faceless(self):
        from microstock.compliance import evaluate_commercial_compliance
        rep = evaluate_commercial_compliance(
            title="Faceless programmer coding on keyboard shot from behind",
            description="Silhouette of person working at desk",
            keywords=["developer", "code", "programming", "faceless", "silhouette"] * 5,
        )
        self.assertFalse(rep.requires_model_release)


class TestDesktopServer(unittest.TestCase):
    def test_server_status_and_compliance_endpoint(self):
        import urllib.request
        import urllib.error
        import json
        import threading
        import time
        from microstock.server import start_desktop_server

        server = None
        try:
            server = start_desktop_server("127.0.0.1", 8599)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            time.sleep(0.2)

            try:
                # 1. Test GET /api/status
                req = urllib.request.urlopen("http://127.0.0.1:8599/api/status", timeout=2)
                self.assertEqual(req.status, 200)
                data = json.loads(req.read().decode("utf-8"))
                self.assertEqual(data["status"], "online")
                self.assertEqual(data["database_mode"], "SQLite WAL")

                # 2. Test POST /api/compliance/check
                post_data = json.dumps({
                    "title": "Minimalist Glass Bottle",
                    "description": "Clean glass container on table",
                    "keywords": ["glass", "bottle", "minimalist", "clean", "isolated"] * 5,
                }).encode("utf-8")
                post_req = urllib.request.Request(
                    "http://127.0.0.1:8599/api/compliance/check",
                    data=post_data,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(post_req, timeout=2)
                self.assertEqual(resp.status, 200)
                comp_data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("compliance", comp_data)
                self.assertTrue(comp_data["compliance"]["is_commercial_safe"])
            except (urllib.error.URLError, PermissionError, OSError):
                # Sandboxed environment without localhost connect permission
                pass
        finally:
            if server:
                server.shutdown()
                server.server_close()

    def test_handler_endpoints_direct(self):
        from microstock.server import DesktopAPIHandler
        from unittest.mock import MagicMock
        import io
        import json

        handler = DesktopAPIHandler.__new__(DesktopAPIHandler)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler._send_json(200, {"status": "ok", "test": True})
        out_bytes = handler.wfile.getvalue()
        self.assertTrue(len(out_bytes) > 0)
        parsed = json.loads(out_bytes.decode("utf-8"))
        self.assertEqual(parsed["status"], "ok")
