from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
FETCH = load("wp_fetch")
AUDIT_GATE = load("wp_audit_gate")
AUDIT_EXEC = load("wp_push_audit")
BUNDLE = AUDIT_EXEC.BUNDLE


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


class AuditWorkflowTests(unittest.TestCase):
    def make_bundle(self, root: Path, with_image: bool = False) -> tuple[Path, Path, str, str]:
        original = "<p>Old</p>"
        prepared = "<h2>New</h2><p>Text</p>"
        images = []
        if with_image:
            prepared += '<img src="asset://new" alt="New">'
            image_file = root / "new.jpg"
            image_file.write_bytes(b"image-placeholder")
            images = [{"asset_id": "new", "action": "prepare-upload", "alt": "New",
                       "filename": "new.jpg", "output": str(image_file),
                       "output_sha256": hashlib.sha256(image_file.read_bytes()).hexdigest()}]
        backup = root / "post.20260925.wp-raw-backup.html"
        backup.write_text(original, encoding="utf-8")
        source = root / "new.html"
        source.write_text(prepared, encoding="utf-8")
        request = root / "request.json"
        request.write_text(json.dumps({
            "job_id": "job1", "run_id": "run1", "client": "demo", "site_key": "demo",
            "task_type": "AUDIT", "update_mode": "REBUILD", "content_type": "blog",
            "post_id": 42, "target_url": "https://example.com/a/", "title": "New title",
        }), encoding="utf-8")
        snapshot = root / "snapshot.meta.json"
        snapshot.write_text(json.dumps({
            "id": 42, "modified": "2026-09-25T12:00:00", "status": "publish",
            "link": "https://example.com/a/", "backup_path": str(backup),
            "raw_sha256": hashlib.sha256(original.encode()).hexdigest(),
        }), encoding="utf-8")
        bundle = root / "bundle"
        BUNDLE.lock(argparse.Namespace(
            request=str(request), source=str(source), source_type="local_html",
            source_ref=str(source), source_revision=None, snapshot_meta=str(snapshot),
            bundle=str(bundle),
        ))
        (bundle / "content.prepared.html").write_text(prepared, encoding="utf-8")
        (bundle / "image-manifest.json").write_text(json.dumps({"images": images}), encoding="utf-8")
        (bundle / "transform-report.json").write_text(
            '{"total":0,"converted":0,"protected":0}', encoding="utf-8")
        (bundle / "audit-plan.json").write_text(json.dumps({
            "update_mode": "REBUILD", "rebuild_reason": "Approved new section",
            "expected_structure_delta": {"h1": 0, "h2": 1, "h3": 0, "table": 0,
                                         "img": 1 if with_image else 0, "iframe": 0},
            "approved_removed_image_urls": [], "approved_removed_links": [],
            "keep_passages": [],
        }), encoding="utf-8")
        report = AUDIT_GATE.check(bundle)
        (bundle / "audit-gate-report.json").write_text(json.dumps(report), encoding="utf-8")
        BUNDLE.approve(argparse.Namespace(bundle=str(bundle), approved_by="operator"))
        (bundle / "run-state.json").write_text(json.dumps({
            "state": "APPROVED", "run_id": "run1", "job_id": "job1", "media": {},
        }), encoding="utf-8")
        profile = root / "publish-context.json"
        profile.write_text(json.dumps({
            "version": 2, "content_profiles": {"blog": {
                "endpoint": "posts", "status": "batch-ready", "ready": True,
                "batch_ready": True, "body_h1_count": 0, "seo_meta_adapter": "none",
            }},
        }), encoding="utf-8")
        return bundle, profile, original, prepared

    def test_rebuild_requires_an_exact_approved_structure_delta(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, _, _, _ = self.make_bundle(Path(td))
            plan = json.loads((bundle / "audit-plan.json").read_text())
            plan["expected_structure_delta"]["h2"] = 0
            (bundle / "audit-plan.json").write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "structure delta"):
                AUDIT_GATE.check(bundle)
            with self.assertRaisesRegex(ValueError, "structure delta"):
                AUDIT_EXEC.load_approved_bundle(bundle, None)

    def test_rebuild_requires_approval_for_removed_link(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, _, _, _ = self.make_bundle(Path(td))
            old = '<a href="https://example.com/old">Old</a>'
            backup = Path(json.loads((bundle / "publish-request.json").read_text())["backup_path"])
            backup.write_text(old, encoding="utf-8")
            request = json.loads((bundle / "publish-request.json").read_text())
            request["wp_raw_sha256_at_fetch"] = hashlib.sha256(old.encode()).hexdigest()
            (bundle / "publish-request.json").write_text(json.dumps(request), encoding="utf-8")
            plan = json.loads((bundle / "audit-plan.json").read_text())
            plan["expected_structure_delta"]["h2"] = 1
            (bundle / "audit-plan.json").write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "removed links"):
                AUDIT_GATE.check(bundle)

    def test_rebuild_detects_changed_anchor_at_the_same_url(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, _, _, _ = self.make_bundle(Path(td))
            old = '<p><a href="https://example.com/a/">Old anchor</a></p>'
            new = '<h2>New</h2><p><a href="https://example.com/a/">New anchor</a></p>'
            request = json.loads((bundle / "publish-request.json").read_text())
            Path(request["backup_path"]).write_text(old, encoding="utf-8")
            request["wp_raw_sha256_at_fetch"] = hashlib.sha256(old.encode()).hexdigest()
            (bundle / "publish-request.json").write_text(json.dumps(request), encoding="utf-8")
            (bundle / "content.prepared.html").write_text(new, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "removed links/anchors"):
                AUDIT_GATE.check(bundle)

    def test_minimal_diff_requires_exact_unique_edit(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, _, original, prepared = self.make_bundle(Path(td))
            request = json.loads((bundle / "publish-request.json").read_text())
            request["update_mode"] = "MINIMAL_DIFF"
            (bundle / "publish-request.json").write_text(json.dumps(request), encoding="utf-8")
            plan = json.loads((bundle / "audit-plan.json").read_text())
            plan["update_mode"] = "MINIMAL_DIFF"
            plan.pop("rebuild_reason")
            plan["edits"] = [{"old": original, "new": prepared}]
            (bundle / "audit-plan.json").write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(AUDIT_GATE.check(bundle)["update_mode"], "MINIMAL_DIFF")
            plan["edits"] = [{"old": "missing", "new": prepared}]
            (bundle / "audit-plan.json").write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "edit does not match"):
                AUDIT_GATE.check(bundle)

    def test_rebuild_write_stops_when_post_changed_since_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, profile, original, _ = self.make_bundle(Path(td))
            approval = json.loads((bundle / "approval.json").read_text())
            current = {"id": 42, "modified": "2026-09-25T13:00:00", "status": "publish",
                       "link": "https://example.com/a/", "content": {"raw": original}}
            args = argparse.Namespace(bundle=str(bundle), site_key="demo", profile=str(profile),
                                      execute=True, approval_hash=approval["approval_hash"])
            with mock.patch.object(AUDIT_EXEC.WP, "load_credential", return_value=("https://example.com", "u", "p")), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_get", return_value=(200, current)), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_post") as post:
                with self.assertRaisesRegex(ValueError, "SOURCE-STALE"):
                    AUDIT_EXEC.run(args)
                post.assert_not_called()

    def test_approved_rebuild_updates_existing_post_and_reads_back(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, profile, original, prepared = self.make_bundle(Path(td))
            approval = json.loads((bundle / "approval.json").read_text())
            current = {"id": 42, "modified": "2026-09-25T12:00:00", "status": "publish",
                       "link": "https://example.com/a/", "content": {"raw": original}}
            readback = {"id": 42, "modified": "2026-09-25T12:01:00", "status": "publish",
                        "link": "https://example.com/a/", "content": {"raw": prepared},
                        "title": {"raw": "New title"}, "meta": {}}
            args = argparse.Namespace(bundle=str(bundle), site_key="demo", profile=str(profile),
                                      execute=True, approval_hash=approval["approval_hash"])
            with mock.patch.object(AUDIT_EXEC.WP, "load_credential", return_value=("https://example.com", "u", "p")), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_get", side_effect=[(200, current), (200, current), (200, readback)]), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_post", return_value=(200, {"id": 42})) as post:
                self.assertEqual(AUDIT_EXEC.run(args), 0)
                payload = post.call_args.args[4]
                self.assertEqual(payload["content"], prepared)
                self.assertNotIn("status", payload)

    def test_rebuild_uploads_one_approved_image_and_uses_its_url(self):
        with tempfile.TemporaryDirectory() as td:
            bundle, profile, original, _ = self.make_bundle(Path(td), with_image=True)
            approval = json.loads((bundle / "approval.json").read_text())
            final = '<h2>New</h2><p>Text</p><img src="https://example.com/new.jpg" alt="New">'
            current = {"id": 42, "modified": "2026-09-25T12:00:00", "status": "publish",
                       "link": "https://example.com/a/", "content": {"raw": original}}
            readback = {"id": 42, "status": "publish", "content": {"raw": final},
                        "title": {"raw": "New title"}, "meta": {}}
            args = argparse.Namespace(bundle=str(bundle), site_key="demo", profile=str(profile),
                                      execute=True, approval_hash=approval["approval_hash"])
            with mock.patch.object(AUDIT_EXEC.WP, "load_credential", return_value=("https://example.com", "u", "p")), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_get", side_effect=[(200, current), (200, current), (200, readback)]), \
                 mock.patch.object(AUDIT_EXEC.WP, "wp_post", return_value=(200, {"id": 42})) as post, \
                 mock.patch.object(AUDIT_EXEC.NEW, "upload_media", return_value={
                     "media_id": 55, "source_url": "https://example.com/new.jpg",
                 }) as upload:
                self.assertEqual(AUDIT_EXEC.run(args), 0)
                upload.assert_called_once()
                self.assertEqual(post.call_args.args[4]["content"], final)

    def test_legacy_verify_command_refuses_unguarded_write(self):
        with mock.patch.object(sys, "argv", ["wp_push_verify.py", "--site", "demo", "--id", "42", "--html", "x.html"]):
            with self.assertRaisesRegex(SystemExit, "wp_push_audit.py"):
                PUSH.main()

    def test_fetch_creates_distinct_backup_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            response = {"id": 42, "slug": "a", "link": "https://example.com/a/",
                        "modified": "2026-09-25T12:00:00", "status": "publish",
                        "title": {"raw": "A"}, "content": {"raw": "<p>Old</p>"}}
            argv = ["wp_fetch.py", "--site", "demo", "--id", "42", "--out", str(root / "out"),
                    "--backup", str(root / "backups")]
            with mock.patch.object(sys, "argv", argv), \
                 mock.patch.object(FETCH, "load_credential", return_value=("https://example.com", "u", "p")), \
                 mock.patch.object(FETCH, "wp_get", return_value=(200, response)):
                FETCH.main()
                first = json.loads((root / "out" / "42.meta.json").read_text())["backup_path"]
                FETCH.main()
                second = json.loads((root / "out" / "42.meta.json").read_text())["backup_path"]
            self.assertNotEqual(first, second)
            self.assertEqual(len(list((root / "backups").glob("*.html"))), 2)


if __name__ == "__main__":
    unittest.main()
