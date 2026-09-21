import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sheet = load("wp_sheet_contract")
router = load("wp_route")
state_mod = load("wp_state")
learn = load("wp_learn")
sheet_io = load("wp_sheet_io")
scaffold_mod = load("wp_scaffold_project")
credential_setup = load("wp_setup_credentials")
job_contract = load("wp_job_contract")
intake_mod = load("wp_intake")
site_scan = load("wp_site_scan")
batch_approval = load("wp_batch_approval")


class SheetContractTests(unittest.TestCase):
    def test_new_requires_slug(self):
        with self.assertRaises(sheet.ContractError):
            sheet.validate({
                "Row ID": "r1", "Loại bài": "NEW",
                "Nguồn content": "x.md", "Bài / Title": "X",
            })

    def test_audit_normalizes(self):
        row = sheet.validate({
            "Row ID": "r2", "Loại bài": "AUDIT",
            "Nguồn content": "https://docs.google.com/document/d/1/edit",
            "Slug / URL WP": "https://example.com/a/", "Bài / Title": "A",
        })
        self.assertEqual(row["target_url"], "https://example.com/a/")
        self.assertEqual(row["source_type"], "google_doc")
        self.assertEqual(row["job_id"], "sheet:r2")
        self.assertEqual(row["tracker"]["type"], "google_sheet")

    def test_new_combined_locator_becomes_slug(self):
        row = sheet.validate({
            "Row ID": "r3", "Loại bài": "NEW", "Nguồn content": "x.md",
            "Slug / URL WP": "new-post", "Bài / Title": "New post",
        })
        self.assertEqual(row["slug"], "new-post")

    def test_html_source_is_detected(self):
        row = sheet.validate({
            "Row ID": "r4", "Loại bài": "NEW", "Nguồn content": "article.html",
            "Slug / URL WP": "article", "Bài / Title": "Article",
        })
        self.assertEqual(row["source_type"], "local_html")


class JobContractTests(unittest.TestCase):
    def test_tracker_free_html_job(self):
        job = job_contract.validate({
            "job_id": "job-1", "run_id": "run-1", "client": "demo", "site_key": "demo",
            "task_type": "NEW", "content_type": "service-page", "title": "Demo", "slug": "demo",
            "source": {"adapter": "local_html", "ref": "demo.html"},
        })
        self.assertEqual(job["tracker"], {"type": "none"})
        self.assertEqual(job["source"]["adapter"], "local_html")

    def test_legacy_sheet_job_is_normalized(self):
        job = job_contract.validate({
            "row_id": "R1", "run_id": "run-1", "client": "demo", "site_key": "demo",
            "task_type": "NEW", "title": "Demo", "slug": "demo",
            "source_ref": "demo.md", "source_type": "local_markdown",
        })
        self.assertEqual(job["job_id"], "sheet:R1")
        self.assertEqual(job["tracker"]["type"], "google_sheet")


class IntakeTests(unittest.TestCase):
    def test_html_snapshot_and_assets_are_locked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.html"
            source.write_text("<p>Hello</p>", encoding="utf-8")
            assets = root / "assets-source.json"
            assets.write_text('{"version":1,"images":[{"asset_id":"hero"}]}', encoding="utf-8")
            intake = intake_mod.create_intake(
                "local_html", source, str(source), root / "intake", assets
            )
            self.assertEqual(intake["media_type"], "text/html")
            self.assertEqual(intake["asset_count"], 1)
            self.assertTrue((root / "intake/content.snapshot.html").is_file())

    def test_invalid_assets_do_not_copy_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.md"
            source.write_text("# Hello", encoding="utf-8")
            assets = root / "assets-source.json"
            assets.write_text('{"images":"wrong"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "assets.images"):
                intake_mod.create_intake(
                    "local_markdown", source, str(source), root / "intake", assets
                )
            self.assertFalse((root / "intake/content.snapshot.md").exists())


class SiteScanTests(unittest.TestCase):
    def test_scan_is_read_only_and_builds_profiles(self):
        calls = []

        def requester(method, url, user, app_pass):
            calls.append((method, url))
            if "users/me" in url:
                return 200, {"id": 7, "roles": ["editor"], "capabilities": {
                    "edit_posts": True, "edit_pages": True, "upload_files": True,
                }}
            if "types?" in url:
                return 200, {
                    "post": {"rest_base": "posts"}, "page": {"rest_base": "pages"},
                    "product": {"rest_base": "products"},
                }
            if "taxonomies?" in url:
                return 200, {"category": {}, "post_tag": {}}
            return 200, {"schema": {"properties": {"title": {}}}}

        result = site_scan.build_scan("https://example.com", "editor", "secret", requester)
        self.assertTrue(result["read_only"])
        self.assertTrue(all(method in {"GET", "OPTIONS"} for method, _ in calls))
        self.assertEqual(result["profiles"]["product"]["post_type"], "product")
        self.assertEqual(result["profiles"]["product"]["endpoint"], "products")
        self.assertIn("edit_products", result["profiles"]["product"]["missing_capabilities"])


class BatchApprovalTests(unittest.TestCase):
    def make_bundle(self, root: Path, job_id: str) -> Path:
        bundle = root / job_id
        bundle.mkdir()
        source = root / f"{job_id}.md"
        source.write_text("# Source", encoding="utf-8")
        request = {
            "job_id": job_id, "run_id": f"run-{job_id}", "task_type": "NEW",
            "content_type": "blog", "title": job_id,
        }
        (bundle / "publish-request.json").write_text(json.dumps(request), encoding="utf-8")
        (bundle / "content.prepared.html").write_text("<h1>Source</h1>", encoding="utf-8")
        (bundle / "image-manifest.json").write_text('{"images":[]}', encoding="utf-8")
        (bundle / "transform-report.json").write_text('{"ok":true}', encoding="utf-8")
        lock = {
            "source_type": "local_markdown", "source_path": str(source),
            "source_sha256": batch_approval.BUNDLE.sha256_file(source),
        }
        (bundle / "source-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        return bundle

    def test_one_batch_approval_creates_exact_per_job_approvals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.make_bundle(root, "job-a")
            second = self.make_bundle(root, "job-b")
            manifest = batch_approval.build_manifest("batch-1", [second, first])
            manifest_path = root / "batch-manifest.json"
            batch_approval.BUNDLE.atomic_json(manifest_path, manifest)
            digest = batch_approval.file_sha256(manifest_path)
            approval = batch_approval.approve_manifest(manifest_path, digest, "operator")
            self.assertEqual(approval["job_count"], 2)
            self.assertTrue((first / "approval.json").is_file())
            self.assertTrue((second / "approval.json").is_file())
            (second / "content.prepared.html").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SOURCE-STALE"):
                batch_approval.verify_manifest(manifest)


class RouteTests(unittest.TestCase):
    def test_new_absent(self):
        self.assertEqual(router.route({"task_type": "NEW"}, {"matches": []})["route"], "NEW_PREPARE")

    def test_new_existing_stops(self):
        with self.assertRaises(router.RouteConflict):
            router.route({"task_type": "NEW", "run_id": "x"}, {"matches": [{"id": 1, "status": "draft"}]})

    def test_new_resume_same_run(self):
        result = router.route(
            {"task_type": "NEW", "run_id": "run-1"},
            {"matches": [{"id": 4, "status": "draft"}]},
            {"post_id": 4, "run_id": "run-1"},
        )
        self.assertEqual(result["route"], "NEW_RESUME")

    def test_audit_exact_url(self):
        result = router.route(
            {"task_type": "AUDIT", "target_url": "https://example.com/a/"},
            {"matches": [{"id": 7, "link": "https://example.com/a", "status": "publish"}]},
        )
        self.assertEqual(result["post_id"], 7)


class StateTests(unittest.TestCase):
    def test_linear_and_stop_resume(self):
        data = {"state": "NEW", "history": []}
        state_mod.transition(data, "CONTEXT_LOCKED")
        state_mod.transition(data, "STOPPED", "INPUT-MISSING", "x")
        self.assertEqual(data["resume_state"], "CONTEXT_LOCKED")
        state_mod.transition(data, "CONTEXT_LOCKED")
        self.assertNotIn("error_code", data)

    def test_skipping_state_fails(self):
        with self.assertRaises(ValueError):
            state_mod.transition({"state": "NEW", "history": []}, "PREPARED")

    def test_tracker_free_run_can_complete_after_wp_readback(self):
        data = {"state": "WP_VERIFIED", "tracker": {"type": "none"}, "history": []}
        state_mod.transition(data, "COMPLETE")
        self.assertEqual(data["state"], "COMPLETE")

    def test_sheet_alias_migrates_to_tracker_verified(self):
        data = {"state": "WP_VERIFIED", "tracker": {"type": "google_sheet"}, "history": []}
        state_mod.transition(data, "SHEET_VERIFIED")
        self.assertEqual(data["state"], "TRACKER_VERIFIED")


class LearningTests(unittest.TestCase):
    def test_same_key_updates_in_place_and_caps_samples(self):
        index = {"version": 1, "items": {}}
        for n in range(7):
            learn.record(index, {
                "error_code": "IMG-DUP", "client": "example-site", "step": "media-upload", "run_id": f"run-{n}"
            })
        self.assertEqual(len(index["items"]), 1)
        item = next(iter(index["items"].values()))
        self.assertEqual(item["distinct_runs"], 7)
        self.assertEqual(len(item["sample_run_ids"]), 3)
        self.assertEqual(item["status"], "candidate")

    def test_index_hard_cap_write(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "index.json"
            learn.atomic_save(p, {"version": 1, "items": {}})
            self.assertTrue(json.loads(p.read_text())["items"] == {})


class SheetIOTests(unittest.TestCase):
    def test_prepare_and_verify_readback(self):
        patch = sheet_io.prepare(
            {"Row ID": "R-1", "Loại bài": "NEW"},
            {"Trạng thái": "Hoàn tất", "URL draft/live": "https://example.com/a/"},
        )
        sheet_io.verify(patch, {"Row ID": "R-1", "Trạng thái": "Hoàn tất", "URL draft/live": "https://example.com/a/"})

    def test_rejects_input_field_mutation(self):
        with self.assertRaisesRegex(ValueError, "SHEET-WRITE"):
            sheet_io.prepare({"Row ID": "R-1"}, {"Loại bài": "AUDIT"})

    def test_readback_mismatch_fails(self):
        patch = sheet_io.prepare({"Row ID": "R-1"}, {"Trạng thái": "Chờ xác nhận"})
        with self.assertRaisesRegex(ValueError, "SHEET-READBACK"):
            sheet_io.verify(patch, {"Row ID": "R-1", "Trạng thái": "Hoàn tất"})

    def test_rejects_unknown_status(self):
        with self.assertRaisesRegex(ValueError, "invalid Trạng thái"):
            sheet_io.prepare({"Row ID": "R-1"}, {"Trạng thái": "Đang chuẩn bị"})


class ProjectScaffoldTests(unittest.TestCase):
    def test_scaffold_is_non_destructive_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            projects = Path(td) / "projects"
            project = projects / "demo-client"
            first = scaffold_mod.scaffold("demo-client", projects)
            self.assertTrue(first["created"])
            self.assertEqual(first["context_status"], "created-needs-confirmation")
            self.assertIn("# Demo Client context", (project / "context.md").read_text(encoding="utf-8"))
            self.assertTrue((project / "content/README.md").is_file())
            self.assertTrue((project / "content/blog/.gitkeep").is_file())
            self.assertTrue((project / "content/service-page/.gitkeep").is_file())
            self.assertTrue((project / "content/product/.gitkeep").is_file())
            self.assertTrue((project / "scans/.gitkeep").is_file())
            profile = project / "publish-context.json"
            generated = json.loads(profile.read_text(encoding="utf-8"))
            self.assertEqual(generated["site_key"], "demo-client")
            self.assertFalse(generated["content_profiles"]["blog"]["ready"])
            self.assertFalse(generated["pilot_allowed"])
            self.assertEqual(generated["tracker"], {"type": "none"})
            self.assertEqual(generated["timezone"], "UTC")
            profile.write_text('{"ready": true}\n', encoding="utf-8")
            second = scaffold_mod.scaffold("demo-client", projects)
            self.assertEqual(profile.read_text(encoding="utf-8"), '{"ready": true}\n')
            self.assertEqual(second["created"], [])
            self.assertEqual(second["context_status"], "preserved")

    def test_scaffold_rejects_invalid_client_slug(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "kebab-case"):
                scaffold_mod.scaffold("Missing Client", Path(td))


class CredentialSetupTests(unittest.TestCase):
    def test_https_and_kebab_case_are_required(self):
        self.assertEqual(
            credential_setup.validate_inputs("demo-site", "https://example.com/", "wp-publish"),
            ("demo-site", "https://example.com", "wp-publish"),
        )
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            credential_setup.validate_inputs("demo-site", "http://example.com", "wp-publish")

    def test_editor_capabilities_pass_and_admin_is_detected(self):
        capabilities = {name: True for name in credential_setup.REQUIRED_CAPABILITIES}
        editor = credential_setup.assess_user({"roles": ["editor"], "capabilities": capabilities})
        self.assertFalse(editor["administrator"])
        self.assertEqual(editor["missing_capabilities"], [])
        admin = credential_setup.assess_user({"roles": ["administrator"], "capabilities": capabilities})
        self.assertTrue(admin["administrator"])

    def test_existing_credential_requires_explicit_replace(self):
        old = credential_setup.credential_block("demo", "https://old.example", "old", "old")
        new = credential_setup.credential_block("demo", "https://new.example", "new", "secret")
        with self.assertRaisesRegex(ValueError, "--replace"):
            credential_setup.update_text(old, "demo", new, replace=False)
        replaced = credential_setup.update_text(old, "demo", new, replace=True)
        self.assertIn("https://new.example", replaced)
        self.assertNotIn("https://old.example", replaced)

    def test_env_credential_round_trip_uses_site_prefix(self):
        text = credential_setup.credential_block(
            "demo-site", "https://example.com", "wp-publish", "abcd efgh"
        )
        self.assertEqual(
            credential_setup.WP_LIB.credential_from_env_text("demo-site", text),
            ("https://example.com", "wp-publish", "abcd efgh"),
        )
        self.assertIn("WP_DEMO_SITE_APP_PASS", text)

    def test_incomplete_env_entry_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "incomplete credential"):
            credential_setup.WP_LIB.credential_from_env_text(
                "demo", 'WP_DEMO_URL="https://example.com"\nWP_DEMO_USER="editor"\n'
            )

    def test_legacy_migration_keeps_multiple_sites(self):
        legacy = (
            "### demo WordPress (REST API)\n- URL: https://demo.example\n"
            "- User: editor\n- App Password: one two\n\n"
            "### second-site WordPress (REST API)\n- URL: https://second.example\n"
            "- User: editor2\n- App Password: three four\n"
        )
        migrated, count = credential_setup.migrate_legacy_text("", legacy)
        self.assertEqual(count, 2)
        self.assertIn("WP_DEMO_URL", migrated)
        self.assertIn("WP_SECOND_SITE_URL", migrated)
        self.assertEqual(
            credential_setup.WP_LIB.credential_from_env_text("second-site", migrated),
            ("https://second.example", "editor2", "three four"),
        )

    def test_private_write_uses_owner_only_mode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".env.wp-publish"
            credential_setup.atomic_private_write(path, "SECRET=value\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_loader_rejects_group_readable_env_file(self):
        if os.name == "nt":
            self.skipTest("POSIX permission bits are not enforced on Windows")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".env.wp-publish"
            path.write_text(
                credential_setup.credential_block(
                    "demo", "https://example.com", "editor", "secret"
                ),
                encoding="utf-8",
            )
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "chmod 600"):
                credential_setup.WP_LIB.load_credential("demo", credential_path=path)

    def test_macos_dialog_returns_secret_without_printing_it(self):
        completed = subprocess.CompletedProcess([], 0, stdout="abcd efgh\n", stderr="")
        with mock.patch.object(credential_setup.shutil, "which", return_value="/usr/bin/osascript"):
            password = credential_setup.macos_password_dialog("demo", runner=lambda *args, **kwargs: completed)
        self.assertEqual(password, "abcd efgh")

    def test_macos_dialog_cancel_stops_without_terminal_fallback(self):
        completed = subprocess.CompletedProcess([], 1, stdout="", stderr="User canceled")
        with mock.patch.object(credential_setup.shutil, "which", return_value="/usr/bin/osascript"):
            with self.assertRaisesRegex(credential_setup.InputCancelled, "cancelled"):
                credential_setup.macos_password_dialog("demo", runner=lambda *args, **kwargs: completed)

    def test_auto_mode_uses_native_dialog_without_tty(self):
        with mock.patch.object(credential_setup, "native_password_dialog", return_value="secret"):
            self.assertEqual(credential_setup.collect_password("demo", "auto"), "secret")


if __name__ == "__main__":
    unittest.main()
