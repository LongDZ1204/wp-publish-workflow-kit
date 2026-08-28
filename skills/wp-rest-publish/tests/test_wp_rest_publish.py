from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


APPLY = load("wp_apply_edits")
PUSH = load("wp_push_verify")


class HtmlPolicyTests(unittest.TestCase):
    def test_h1_count_is_case_insensitive(self):
        self.assertEqual(APPLY.h1_count("<H1>Title</H1><p>Body</p>"), 1)
        self.assertEqual(PUSH.h1_count("<h1 class='entry'>Title</h1>"), 1)


class SeoMetaTests(unittest.TestCase):
    def test_yoast_mapping(self):
        self.assertEqual(PUSH.build_seo_meta("yoast", "SEO title", "Description"), {
            "_yoast_wpseo_title": "SEO title",
            "_yoast_wpseo_metadesc": "Description",
        })

    def test_rankmath_mapping(self):
        self.assertEqual(PUSH.build_seo_meta("rankmath", "SEO title", "Description"), {
            "rank_math_title": "SEO title",
            "rank_math_description": "Description",
        })

    def test_adapter_is_required_when_meta_is_supplied(self):
        with self.assertRaisesRegex(ValueError, "yoast or rankmath"):
            PUSH.build_seo_meta(None, "SEO title", None)


if __name__ == "__main__":
    unittest.main()
