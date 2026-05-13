"""
DB 레이어 단위 테스트 (임시 파일 DB 사용).
"""
import sys
import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# conftest.py가 먼저 실행되어 streamlit/playwright가 mock됩니다
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

with patch("subprocess.run"):
    import app as _app


def _make_asset(uid="test-id-1", keyword="에어컨", url=None):
    return {
        "id": uid,
        "keyword": keyword,
        "country": "KR",
        "asset_type": "image",
        "image_url": url or f"https://example.com/{uid}.jpg",
        "source_url": "https://facebook.com/ads",
        "caption": "테스트 광고",
        "width": 400,
        "height": 400,
        "created_at": "2025-01-01T00:00:00",
        "starred": 0,
        "capture_source": "card",
        "img_b64": "",
        "ai_json": "",
    }


class TestDbLayer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        _app.DB_PATH = self.tmp.name
        _app.db_init()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_upsert_and_load(self):
        _app.db_upsert_assets([_make_asset()])
        loaded = _app.db_load_assets()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["id"], "test-id-1")

    def test_upsert_idempotent(self):
        asset = _make_asset()
        _app.db_upsert_assets([asset])
        _app.db_upsert_assets([asset])
        self.assertEqual(len(_app.db_load_assets()), 1)

    def test_set_field_starred(self):
        _app.db_upsert_assets([_make_asset()])
        _app.db_set_field("test-id-1", starred=1)
        self.assertEqual(_app.db_load_assets()[0]["starred"], 1)

    def test_set_field_ai_json(self):
        _app.db_upsert_assets([_make_asset()])
        _app.db_set_field("test-id-1", ai_json=json.dumps({"hook": "가격", "appeal": "할인"}))
        loaded = _app.db_load_assets()
        self.assertEqual(loaded[0]["ai"]["hook"], "가격")

    def test_hidden(self):
        _app.db_add_hidden("test-id-1")
        self.assertIn("test-id-1", _app.db_load_hidden())

    def test_history(self):
        _app.db_add_history("에어컨")
        self.assertIn("에어컨", _app.db_load_history())

    def test_summary_store(self):
        _app.db_save_summary({"dominant_appeal": "가격", "tags": ["할인"]})
        loaded = _app.db_load_summary()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["dominant_appeal"], "가격")

    def test_trend_snapshot(self):
        ai = json.dumps({"appeal": "가격", "hook": "할인", "scores": {"overall_conversion_power": 4}})
        assets = [
            {**_make_asset("id1"), "ai_json": ai},
            {**_make_asset("id2"), "ai_json": ""},
        ]
        _app.db_upsert_assets(assets)
        loaded = _app.db_load_assets()
        _app.db_save_trend_snapshot("에어컨", loaded)
        snapshots = _app.db_load_trend_snapshots("에어컨")
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["keyword"], "에어컨")
        self.assertEqual(snapshots[0]["asset_count"], 2)

    def test_trend_snapshot_overwrite_same_day(self):
        _app.db_upsert_assets([_make_asset("id1")])
        loaded = _app.db_load_assets()
        _app.db_save_trend_snapshot("에어컨", loaded)
        _app.db_save_trend_snapshot("에어컨", loaded)
        self.assertEqual(len(_app.db_load_trend_snapshots("에어컨")), 1)

    def test_load_all_trend_snapshots(self):
        assets = [_make_asset("id1", "에어컨"), _make_asset("id2", "공기청정기")]
        _app.db_upsert_assets(assets)
        loaded = _app.db_load_assets()
        _app.db_save_trend_snapshot("에어컨", loaded)
        _app.db_save_trend_snapshot("공기청정기", loaded)
        self.assertEqual(len(_app.db_load_trend_snapshots()), 2)


class TestMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        _app.DB_PATH = self.tmp.name
        _app.db_init()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_merge_new_items(self):
        existing = [_make_asset("id1", url="https://example.com/1.jpg")]
        new_items = [_make_asset("id2", url="https://example.com/2.jpg")]
        merged, added, skipped = _app.merge(existing, new_items)
        self.assertEqual(added, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(merged), 2)

    def test_merge_duplicate_skipped(self):
        asset = _make_asset("id1")
        _, added, skipped = _app.merge([asset], [asset])
        self.assertEqual(added, 0)
        self.assertEqual(skipped, 1)


class TestApiRetry(unittest.TestCase):
    def test_retry_on_429(self):
        mock_429 = MagicMock(status_code=429)
        mock_ok = MagicMock(status_code=200)
        calls = {"n": 0}

        def fake_post(*args, **kwargs):
            calls["n"] += 1
            return mock_ok if calls["n"] >= 3 else mock_429

        with patch("app.requests.post", side_effect=fake_post), patch("app.time.sleep"):
            resp = _app._anthropic_post({"model": "x", "max_tokens": 1, "messages": []}, max_retries=4)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calls["n"], 3)

    def test_no_retry_on_200(self):
        mock_ok = MagicMock(status_code=200)
        with patch("app.requests.post", return_value=mock_ok) as mock_req:
            resp = _app._anthropic_post({"model": "x", "max_tokens": 1, "messages": []})
        self.assertEqual(mock_req.call_count, 1)
        self.assertEqual(resp.status_code, 200)

    def test_gives_up_after_max_retries(self):
        mock_429 = MagicMock(status_code=429)
        with patch("app.requests.post", return_value=mock_429), patch("app.time.sleep"):
            resp = _app._anthropic_post({"model": "x", "max_tokens": 1, "messages": []}, max_retries=2)
        self.assertEqual(resp.status_code, 429)


if __name__ == "__main__":
    unittest.main()
