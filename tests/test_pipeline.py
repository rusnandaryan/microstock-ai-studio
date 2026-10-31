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


class TestKeywordSanitization(unittest.TestCase):
    def test_normalize_keywords_removes_duplicates_and_strips(self):
        raw = [" Nature", "nature", "LANDSCAPE", "outdoor", "nature", "tree "]
        cleaned = normalize_keywords(raw)
        self.assertEqual(cleaned, ["nature", "landscape", "outdoor", "tree"])


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
                "market_status": "🔥 Viral",
                "reason": "Liputan media tinggi",
                "ideas": [f"Visual A {i}", f"Visual B {i}", f"Visual C {i}"],
                "recommended_cat": "Fotografi (Photorealism)",
                "recommended_style": "📷 Foto Komersial Bersih",
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


if __name__ == "__main__":
    unittest.main()
