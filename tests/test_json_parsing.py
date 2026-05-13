"""
JSON 파싱 파이프라인 단위 테스트.
"""
import sys
import os
import json
import unittest
from unittest.mock import patch

# conftest.py가 먼저 실행되어 streamlit/playwright가 mock됩니다
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

with patch("subprocess.run"):
    import app as _app

_extract_json_block    = _app._extract_json_block
_fix_unescaped_newlines = _app._fix_unescaped_newlines
_fix_common_json_issues = _app._fix_common_json_issues
_parse_ai_json          = _app._parse_ai_json
_safe_join              = _app._safe_join
_url_path_key           = _app._url_path_key
make_fp                 = _app.make_fp


class TestExtractJsonBlock(unittest.TestCase):
    def test_clean_json(self):
        raw = '{"a": 1, "b": "hello"}'
        self.assertEqual(_extract_json_block(raw), raw)

    def test_markdown_fenced(self):
        result = _extract_json_block('```json\n{"x": 42}\n```')
        self.assertEqual(json.loads(result), {"x": 42})

    def test_truncated_json_auto_close(self):
        result = _extract_json_block('{"a": 1, "b": "val')
        self.assertIsNotNone(result)

    def test_no_json(self):
        self.assertIsNone(_extract_json_block("no json here"))

    def test_empty_string(self):
        self.assertIsNone(_extract_json_block(""))

    def test_json_with_surrounding_text(self):
        result = _extract_json_block('Here is the result: {"key": "value"} done.')
        self.assertEqual(json.loads(result), {"key": "value"})


class TestFixUnescapedNewlines(unittest.TestCase):
    def test_no_change_outside_string(self):
        raw = '{"a": 1}\n{"b": 2}'
        self.assertEqual(_fix_unescaped_newlines(raw), raw)

    def test_newline_inside_string(self):
        result = _fix_unescaped_newlines('{"a": "line1\nline2"}')
        self.assertEqual(json.loads(result), {"a": "line1 line2"})

    def test_escaped_newline_preserved(self):
        result = _fix_unescaped_newlines('{"a": "line1\\nline2"}')
        self.assertEqual(json.loads(result), {"a": "line1\nline2"})


class TestFixCommonJsonIssues(unittest.TestCase):
    def test_trailing_comma_object(self):
        self.assertEqual(json.loads(_fix_common_json_issues('{"a": 1,}')), {"a": 1})

    def test_trailing_comma_array(self):
        self.assertEqual(json.loads(_fix_common_json_issues('{"arr": [1, 2, 3,]}')), {"arr": [1, 2, 3]})

    def test_control_chars_removed(self):
        self.assertEqual(json.loads(_fix_common_json_issues('{"a": "val\x01ue"}')), {"a": "value"})


class TestParseAiJson(unittest.TestCase):
    def test_valid_json(self):
        result, err = _parse_ai_json('{"hook": "가격 소구", "appeal": "할인"}')
        self.assertIsNone(err)
        self.assertEqual(result["hook"], "가격 소구")

    def test_newline_in_string(self):
        result, err = _parse_ai_json('{"hook": "line1\nline2", "appeal": "test"}')
        self.assertIsNone(err)
        self.assertIn("line1", result["hook"])

    def test_trailing_comma(self):
        result, err = _parse_ai_json('{"hook": "test", "appeal": "감성",}')
        self.assertIsNone(err)
        self.assertEqual(result["appeal"], "감성")

    def test_no_json(self):
        result, err = _parse_ai_json("죄송합니다, 분석할 수 없습니다.")
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    def test_markdown_wrapped(self):
        result, err = _parse_ai_json('```json\n{"key": "value"}\n```')
        self.assertIsNone(err)
        self.assertEqual(result["key"], "value")


class TestSafeJoin(unittest.TestCase):
    def test_list(self):
        self.assertEqual(_safe_join(["a", "b", "c"]), "a, b, c")

    def test_empty_list(self):
        self.assertEqual(_safe_join([]), "")

    def test_string_input(self):
        self.assertEqual(_safe_join("hello"), "hello")

    def test_none(self):
        self.assertEqual(_safe_join(None), "")

    def test_custom_sep(self):
        self.assertEqual(_safe_join(["x", "y"], " / "), "x / y")


class TestMakeFp(unittest.TestCase):
    def test_same_url_same_fp(self):
        item = {"image_url": "https://example.com/img.jpg?w=100", "asset_type": "image"}
        self.assertEqual(make_fp(item), make_fp(item))

    def test_different_url_different_fp(self):
        i1 = {"image_url": "https://example.com/img1.jpg", "asset_type": "image"}
        i2 = {"image_url": "https://example.com/img2.jpg", "asset_type": "image"}
        self.assertNotEqual(make_fp(i1), make_fp(i2))

    def test_empty_url(self):
        self.assertIsNotNone(make_fp({"image_url": "", "asset_type": "image"}))


class TestUrlPathKey(unittest.TestCase):
    def test_strips_query(self):
        self.assertNotIn("?", _url_path_key("https://example.com/img.jpg?w=100"))

    def test_invalid_url(self):
        self.assertIsNotNone(_url_path_key("not-a-url"))


if __name__ == "__main__":
    unittest.main()
