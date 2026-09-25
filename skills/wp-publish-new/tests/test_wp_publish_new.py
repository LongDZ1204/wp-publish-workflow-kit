from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUNDLE = load("test_wp_bundle", ROOT / "skills/wp-publish-new/scripts/wp_bundle.py")
GATE = load("test_wp_gate", ROOT / "skills/wp-publish-new/scripts/wp_gate.py")
PUSH = load("test_wp_push", ROOT / "skills/wp-publish-new/scripts/wp_push_draft.py")
DOC_EXPORT = load("test_wp_doc_export", ROOT / "skills/wp-publish-new/scripts/wp_doc_export.py")


class Args:
    pass


class BundleTests(unittest.TestCase):
    def test_google_doc_html_snapshot_keeps_html_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "content.snapshot.html"
            source.write_text("<h1>Draft</h1>", encoding="utf-8")
            request = root / "request.json"
            request.write_text(json.dumps({
                "job_id": "job-one", "run_id": "run-one", "client": "demo", "site_key": "demo",
                "task_type": "NEW", "title": "Title", "slug": "title",
            }), encoding="utf-8")
            bundle = root / "bundle"
            args = Args()
            args.bundle, args.request, args.source = str(bundle), str(request), str(source)
            args.source_type, args.source_ref, args.source_revision = "google_doc", "doc-id", None
            args.snapshot_meta = None
            self.assertEqual(BUNDLE.lock(args), 0)
            self.assertTrue((bundle / "source.snapshot.html").is_file())
            self.assertFalse((bundle / "source.snapshot.md").exists())
            BUNDLE.verify_source(bundle)

    def test_local_source_lock_approve_and_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "article.md"
            source.write_text("# Draft\n", encoding="utf-8")
            request = root / "request.json"
            request.write_text(json.dumps({
                "row_id": "R1", "run_id": "RUN1", "client": "demo", "site_key": "demo",
                "task_type": "NEW", "title": "Title", "slug": "title",
            }), encoding="utf-8")
            bundle = root / "bundle"
            args = Args()
            args.bundle, args.request, args.source = str(bundle), str(request), str(source)
            args.source_type, args.source_ref = "local_markdown", str(source)
            args.source_revision = None
            self.assertEqual(BUNDLE.lock(args), 0)
            self.assertFalse((bundle / "source.snapshot.md").exists())
            (bundle / "content.prepared.html").write_text("<p>Ready</p>", encoding="utf-8")
            (bundle / "image-manifest.json").write_text('{"images": []}\n', encoding="utf-8")
            (bundle / "transform-report.json").write_text('{"total": 0, "converted": 0, "protected": 0}\n', encoding="utf-8")
            approve = Args()
            approve.bundle, approve.approved_by = str(bundle), "operator"
            self.assertEqual(BUNDLE.approve(approve), 0)
            verify = Args()
            verify.bundle = str(bundle)
            self.assertEqual(BUNDLE.verify(verify), 0)
            (bundle / "content.prepared.html").write_text("<p>Changed</p>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SOURCE-STALE"):
                BUNDLE.verify(verify)


class GateTests(unittest.TestCase):
    def make_bundle(self, root: Path) -> Path:
        bundle = root / "bundle"
        bundle.mkdir()
        (bundle / "publish-request.json").write_text("{}", encoding="utf-8")
        (bundle / "content.prepared.html").write_text(
            '<h1>Article title</h1><p>Text</p><img src="asset://hero" alt="Useful image">', encoding="utf-8"
        )
        (bundle / "image-manifest.json").write_text(json.dumps({"images": [{
            "asset_id": "hero", "alt": "Useful image", "decorative": False,
            "action": "prepare-upload",
        }]}), encoding="utf-8")
        (bundle / "transform-report.json").write_text(json.dumps({
            "total": 2, "converted": 1, "protected": 1,
        }), encoding="utf-8")
        return bundle

    def test_prepared_and_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            profile = {"ready": True, "body_h1_count": 1}
            self.assertTrue(GATE.validate(bundle, profile, "prepared")["ok"])
            (bundle / "content.final.html").write_text(
                '<h1>Article title</h1><p>Text</p><img src="https://example.com/hero.jpg" alt="Useful image">', encoding="utf-8"
            )
            self.assertTrue(GATE.validate(bundle, profile, "final")["ok"])

    def test_not_ready_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            with self.assertRaisesRegex(ValueError, "BRAND-MISSING"):
                GATE.validate(bundle, {"ready": False}, "prepared")

    def test_explicit_pilot_allows_not_ready_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            profile = {"ready": False, "pilot_allowed": True, "body_h1_count": 1}
            self.assertTrue(GATE.validate(bundle, profile, "prepared", allow_pilot=True)["ok"])

    def test_h1_count_must_match_declared_ownership(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            (bundle / "content.prepared.html").write_text(
                '<p>No heading</p><img src="asset://hero" alt="Useful image">', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "h1 expected=1 actual=0"):
                GATE.validate(bundle, {"ready": True, "body_h1_count": 1}, "prepared")

    def test_zero_h1_allowed_when_theme_owns_the_page_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            (bundle / "content.prepared.html").write_text(
                '<p>Body starts at H2 on themes that render the title as H1</p>'
                '<img src="asset://hero" alt="Useful image">', encoding="utf-8"
            )
            self.assertTrue(GATE.validate(bundle, {"ready": True, "body_h1_count": 0}, "prepared")["ok"])

    def test_missing_body_h1_count_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(Path(tmp))
            with self.assertRaisesRegex(ValueError, "BRAND-MISSING: body_h1_count"):
                GATE.validate(bundle, {"ready": True}, "prepared")


class DraftHelpersTests(unittest.TestCase):
    def test_v2_write_profile_requires_jit_pilot_then_batch_certification(self):
        context = {"version": 2, "content_profiles": {"blog": {
            "status": "unconfirmed", "ready": False,
            "pilot_allowed": False, "batch_ready": False,
        }}}
        with self.assertRaisesRegex(ValueError, "not pilot-ready"):
            PUSH.select_write_profile(context, "blog", pilot=True)
        context["content_profiles"]["blog"].update(
            status="pilot-ready", pilot_allowed=True,
        )
        self.assertEqual(
            PUSH.select_write_profile(context, "blog", pilot=True)["status"], "pilot-ready",
        )
        with self.assertRaisesRegex(ValueError, "not batch-ready"):
            PUSH.select_write_profile(context, "blog", pilot=False)
        context["content_profiles"]["blog"].update(
            status="batch-ready", ready=True, pilot_allowed=False, batch_ready=True,
        )
        self.assertEqual(
            PUSH.select_write_profile(context, "blog", pilot=False)["status"], "batch-ready",
        )

    def test_replace_asset_tokens(self):
        manifest = {"images": [
            {"asset_id": "new", "action": "prepare-upload"},
            {"asset_id": "old", "action": "preserve-existing", "existing_url": "https://x/old.jpg"},
        ]}
        html = '<img src="asset://new"><img src="asset://old">'
        result = PUSH.replace_asset_tokens(html, manifest, {"new": {"source_url": "https://x/new.jpg"}})
        self.assertNotIn("asset://", result)
        self.assertIn("https://x/new.jpg", result)

    def test_yoast_meta_is_bound_to_profile(self):
        request = {
            "title": "Post title", "slug": "post-title", "meta_description": "Meta text",
        }
        payload = PUSH.build_payload(request, "<p>Body</p>", {}, {"seo_meta_adapter": "yoast"})
        self.assertEqual(payload["meta"]["_yoast_wpseo_title"], "Post title")
        self.assertEqual(payload["meta"]["_yoast_wpseo_metadesc"], "Meta text")
        with self.assertRaisesRegex(ValueError, "BRAND-MISSING"):
            PUSH.build_payload(request, "<p>Body</p>", {}, {"seo_meta_adapter": None})

    def test_rankmath_meta_is_bound_to_profile(self):
        request = {
            "title": "Post title", "slug": "post-title", "meta_description": "Meta text",
        }
        payload = PUSH.build_payload(request, "<p>Body</p>", {}, {"seo_meta_adapter": "rankmath"})
        self.assertEqual(payload["meta"]["rank_math_title"], "Post title")
        self.assertEqual(payload["meta"]["rank_math_description"], "Meta text")

    def test_strong_wrapper_outputs_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output, report = root / "in.html", root / "out.html", root / "report.json"
            source.write_text("<p><strong>A</strong></p><h2><strong>B</strong></h2>", encoding="utf-8")
            command = [
                sys.executable, str(ROOT / "workflows/wp-publish/scripts/wp_strong.py"),
                "--input", str(source), "--output", str(output), "--report", str(report),
            ]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("<b>A</b>", output.read_text(encoding="utf-8"))
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["total"], data["converted"] + data["protected"])


class DocExportTests(unittest.TestCase):
    def test_clean_export_extracts_image_drops_doc_title_and_keeps_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "doc.zip"
            html = '''<html><body><p class="title"><span>Title</span></p>
            <h1><span>Content H1</span></h1><h2 style="x"><span>Section</span></h2>
            <p><span>A </span><span style="font-weight:700">bold</span></p>
            <p><span><img src="images/image1.jpg"></span></p>
            <ul><li><span>One</span></li></ul></body></html>'''
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("doc.html", html)
                archive.writestr("images/image1.jpg", b"fake-image")
            source_output = root / "assets/source.jpg"
            mapping = {"profile": {"max_kb": 150}, "images": [{
                "zip_path": "images/image1.jpg", "source_output": str(source_output),
                "asset_id": "hero", "filename": "hero.jpg", "alt": "Useful hero image",
            }]}
            clean_html, request = DOC_EXPORT.convert(archive_path, mapping)
            self.assertNotIn("Title", clean_html)
            self.assertIn("<h1>Content H1</h1>", clean_html)
            self.assertIn("<h2>Section</h2>", clean_html)
            self.assertIn("<strong>bold</strong>", clean_html)
            self.assertIn('src="asset://hero"', clean_html)
            self.assertTrue(source_output.is_file())
            self.assertEqual(request["images"][0]["source"], str(source_output.resolve()))

    def test_image_count_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "doc.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("doc.html", '<html><body><p><img src="images/a.jpg"></p></body></html>')
                archive.writestr("images/a.jpg", b"x")
            with self.assertRaisesRegex(ValueError, "IMG-COUNT"):
                DOC_EXPORT.convert(archive_path, {"images": []})


if __name__ == "__main__":
    unittest.main()
