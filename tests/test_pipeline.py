"""Smoke and regression tests for Microstock AI Studio core pipeline.

Tests image padding, resolution enforcement, vision preparation, and upscaler logic.
Uses standard Python unittest (no external test runner dependencies needed).
"""
import io
import json
import unittest
from PIL import Image

from microstock import config
from microstock.image_generator import BatchItem, _pad_jpeg_to_min_size, detect_aspect_ratio, finalize_image
from microstock.metadata import ImageMetadata, _prepare_vision_bytes, normalize_keywords
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


class TestReversePromptHelpers(unittest.TestCase):
    def testdetect_aspect_ratio(self):
        self.assertEqual(detect_aspect_ratio(1920, 1080), "16:9")
        self.assertEqual(detect_aspect_ratio(1080, 1920), "9:16")
        self.assertEqual(detect_aspect_ratio(1000, 1000), "1:1")
        self.assertEqual(detect_aspect_ratio(1600, 1200), "4:3")
        self.assertEqual(detect_aspect_ratio(1200, 1600), "3:4")


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

    def test_visual_styles_32_count_and_content(self):
        from microstock import config
        self.assertEqual(len(config.VISUAL_STYLES_32), 32)
        style_names = {s.name for s in config.VISUAL_STYLES_32}
        self.assertIn("Lukisan Cat Minyak", style_names)
        self.assertIn("Cat Air", style_names)
        self.assertIn("Batik", style_names)
        self.assertIn("Wayang", style_names)
        self.assertIn("Foto Studio", style_names)
        self.assertIn("Cyberpunk", style_names)

    def test_format_photo_restyle_prompt(self):
        from microstock import config
        p = config.format_photo_restyle_prompt("Lukisan Cat Minyak")
        self.assertIn("lukisan cat minyak", p)
        self.assertIn("tekstur kuas tebal, klasik", p)
        self.assertIn("Pertahankan wajah, pose", p)

    def test_thematic_series_fallback_and_parse(self):
        from microstock.prompt_enhancer import _build_fallback_series, parse_series_response
        series = _build_fallback_series("Kopi espresso", "Foto Studio")
        self.assertEqual(len(series), 5)
        shot_ids = [s["id"] for s in series]
        self.assertEqual(shot_ids, ["hero", "detail", "copy_space", "flatlay", "atmospheric"])

        mock_json = '{"shots": [{"id": "hero", "title": "Hero Shot", "prompt": "Wide hero shot of espresso"}, {"id": "detail", "title": "Detail Shot", "prompt": "Macro shot of crema"}, {"id": "copy_space", "title": "Copy Space", "prompt": "Espresso with negative space"}]}'
        parsed = parse_series_response(mock_json, "Kopi espresso", "Foto Studio")
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["id"], "hero")


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


class TestUiThemeSupport(unittest.TestCase):
    def test_get_modern_css_dark_and_light(self):
        import os
        css_path = os.path.join(os.path.dirname(__file__), "..", "microstock", "web", "assets", "bundle.css")
        self.assertTrue(os.path.isfile(css_path))
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        self.assertIn("--p-bg:", css_content)
        self.assertIn("--p-inv-bg:", css_content)


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

    def test_delete_clear_and_prune_assets(self):
        import os
        from microstock import db
        real_file = os.path.join(self.tmp_dir.name, "real.jpg")
        with open(real_file, "wb") as f:
            f.write(b"fake image content")
        fake_file = os.path.join(self.tmp_dir.name, "nonexistent.jpg")

        id1 = db.save_asset(
            file_path=real_file,
            file_name="real.jpg",
            file_size_bytes=100,
            width=100,
            height=100,
            aspect_ratio="1:1",
            phash_hex="1111111111111111",
            title="Real File",
            description="Real Desc",
            keywords=["real"],
            db_path=self.db_path,
        )
        id2 = db.save_asset(
            file_path=fake_file,
            file_name="nonexistent.jpg",
            file_size_bytes=100,
            width=100,
            height=100,
            aspect_ratio="1:1",
            phash_hex="2222222222222222",
            title="Fake File",
            description="Fake Desc",
            keywords=["fake"],
            db_path=self.db_path,
        )
        self.assertEqual(len(db.list_recent_assets(db_path=self.db_path)), 2)

        # Test prune missing files
        pruned = db.prune_missing_assets(db_path=self.db_path)
        self.assertEqual(pruned, 1)
        remaining = db.list_recent_assets(db_path=self.db_path)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], id1)

        # Test delete specific
        deleted = db.delete_asset(id1, db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertEqual(len(db.list_recent_assets(db_path=self.db_path)), 0)

        # Test clear all
        db.save_asset(
            file_path=real_file,
            file_name="real2.jpg",
            file_size_bytes=100,
            width=100,
            height=100,
            aspect_ratio="1:1",
            phash_hex="3333333333333333",
            title="Real 2",
            description="Desc 2",
            keywords=["real2"],
            db_path=self.db_path,
        )
        cleared = db.clear_all_assets(db_path=self.db_path)
        self.assertEqual(cleared, 1)
        self.assertEqual(len(db.list_recent_assets(db_path=self.db_path)), 0)


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


class TestKeywordRanker(unittest.TestCase):
    def test_buyer_intent_ordering(self):
        from microstock.keyword_ranker import rank_keywords_by_buyer_intent
        raw = ["indoor", "brown", "coffee", "cup", "beverage", "wood", "copy space", "table", "aromatic"]
        ranked = rank_keywords_by_buyer_intent(raw, title="Minimalist Coffee Cup with Copy Space")
        # Primary title words and high buyer intent terms must be boosted to the top
        top_slice = ranked[:4]
        self.assertTrue(any(w in top_slice for w in ("coffee", "cup", "copy space", "minimalist")))


class TestNetworkResilienceAndFallback(unittest.TestCase):
    def test_thematic_series_network_error_fallback(self):
        from unittest.mock import MagicMock
        from microstock.prompt_enhancer import generate_thematic_series

        mock_client = MagicMock()
        # Simulate ConnectError [Errno 8] nodename nor servname provided, or not known
        mock_client.models.generate_content.side_effect = RuntimeError("ConnectError: [Errno 8] nodename nor servname provided, or not known")

        results = generate_thematic_series(
            client=mock_client,
            base_idea="Minimalist Coffee",
            style_name="Foto Studio",
        )
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["id"], "hero")
        self.assertIn("Minimalist Coffee", results[0]["prompt"])

    def test_enhance_prompt_network_error_fallback(self):
        from unittest.mock import MagicMock
        from microstock.prompt_enhancer import enhance_prompt

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("ConnectError: [Errno 8] nodename nor servname provided, or not known")

        res = enhance_prompt(
            client=mock_client,
            base_idea="Baking Bread",
            style_name="Foto Studio",
        )
        self.assertIn("Baking Bread", res)
        self.assertTrue(len(res) > 20)


class TestGemini4HydrogenConfig(unittest.TestCase):
    def test_primary_model_is_gemini_4_hydrogen(self):
        self.assertEqual(config.PRIMARY_GEMINI_MODEL, "gemini-4-hydrogen")
        self.assertEqual(config.TEXT_MODEL_FALLBACKS[0], "gemini-4-hydrogen")
        self.assertIn("gemini-3.8-flash", config.TEXT_MODEL_FALLBACKS)
        self.assertIn("gemini-3.5-flash", config.TEXT_MODEL_FALLBACKS)

    def test_build_generation_config_defaults(self):
        cfg = config.build_generation_config(
            system_instruction="Test instruction",
            temperature=0.5,
            max_output_tokens=2048,
        )
        self.assertEqual(cfg.temperature, 0.5)
        self.assertEqual(cfg.max_output_tokens, 2048)
        self.assertIsNotNone(cfg.thinking_config)
        self.assertEqual(str(cfg.thinking_config.thinking_level).split(".")[-1], "LOW")


class TestStarletteServer(unittest.TestCase):
    def test_status_and_prompt_restyle_endpoints(self):
        from starlette.testclient import TestClient
        import server

        client = TestClient(server.app)
        resp = client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["active_model"], "gemini-4-hydrogen")

        restyle = client.post("/api/prompt/generate", json={"mode": "restyle", "style": "Foto Studio"})
        self.assertEqual(restyle.status_code, 200)
        self.assertTrue(len(restyle.json()["result"]["prompts"]) >= 1)
