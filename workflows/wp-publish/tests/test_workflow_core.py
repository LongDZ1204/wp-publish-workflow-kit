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
item_scaffold_mod = load("wp_scaffold_item")
credential_setup = load("wp_setup_credentials")
job_contract = load("wp_job_contract")
intake_mod = load("wp_intake")
site_scan = load("wp_site_scan")
batch_approval = load("wp_batch_approval")
profile_status = load("wp_profile_status")


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
            "Update mode": "REBUILD",
        })
        self.assertEqual(row["target_url"], "https://example.com/a/")
        self.assertEqual(row["source_type"], "google_doc")
        self.assertEqual(row["job_id"], "sheet:r2")
        self.assertEqual(row["tracker"]["type"], "google_sheet")
        self.assertEqual(row["update_mode"], "REBUILD")

    def test_sheet_audit_may_wait_for_an_upstream_mode_decision(self):
        row = sheet.validate({
            "Row ID": "r2", "Loại bài": "AUDIT", "Nguồn content": "a.html",
            "Slug / URL WP": "https://example.com/a/", "Bài / Title": "A",
        })
        self.assertNotIn("update_mode", row)

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
    def test_audit_rebuild_mode_is_retained(self):
        job = job_contract.validate({
            "job_id": "a1", "run_id": "r1", "client": "demo", "site_key": "demo",
            "task_type": "AUDIT", "content_type": "blog", "title": "New title",
            "post_id": 42, "update_mode": "rebuild",
            "source": {"adapter": "local_html", "ref": "new.html"},
        })
        self.assertEqual(job["update_mode"], "REBUILD")

    def test_audit_job_without_mode_stops(self):
        with self.assertRaisesRegex(job_contract.ContractError, "update_mode"):
            job_contract.validate({
                "job_id": "a1", "run_id": "r1", "client": "demo", "site_key": "demo",
                "task_type": "AUDIT", "title": "New title", "post_id": 42,
                "source": {"adapter": "local_html", "ref": "new.html"},
            })

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
    def test_scan_rejects_invalid_wordpress_key(self):
        def requester(method, url, user, app_pass):
            if "users/me" in url:
                return 401, {"code": "rest_not_logged_in"}
            return 200, {}

        with self.assertRaisesRegex(ValueError, "WordPress credential check failed"):
            site_scan.build_scan("https://example.com", "editor", "wrong", requester)

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
        self.assertEqual(result["profiles"]["blog"]["status"], "unconfirmed")
        self.assertFalse(result["profiles"]["blog"]["batch_ready"])
        self.assertIn("edit_products", result["profiles"]["product"]["missing_capabilities"])


class BatchApprovalTests(unittest.TestCase):
    def make_context(self, root: Path, batch_ready: bool = True) -> Path:
        path = root / "publish-context.json"
        status = "batch-ready" if batch_ready else "pilot-ready"
        path.write_text(json.dumps({
            "version": 2,
            "content_profiles": {
                "blog": {
                    "status": status,
                    "ready": batch_ready,
                    "batch_ready": batch_ready,
                    "endpoint": "posts",
                    "schema_hash": "schema-1",
                }
            },
        }), encoding="utf-8")
        return path

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
            context = self.make_context(root)
            manifest = batch_approval.build_manifest("batch-1", [second, first], context)
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

    def test_batch_rejects_profile_that_has_not_passed_pilot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self.make_bundle(root, "job-a")
            context = self.make_context(root, batch_ready=False)
            with self.assertRaisesRegex(ValueError, "not batch-ready"):
                batch_approval.build_manifest("batch-1", [bundle], context)

    def test_batch_manifest_stops_when_certified_profile_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self.make_bundle(root, "job-a")
            context_path = self.make_context(root)
            manifest = batch_approval.build_manifest("batch-1", [bundle], context_path)
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["content_profiles"]["blog"]["endpoint"] = "changed-posts"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "content profile changed"):
                batch_approval.verify_manifest(manifest)

    def test_audit_batch_approval_binds_plan_and_audit_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self.make_bundle(root, "audit-job")
            request_path = bundle / "publish-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.update(task_type="AUDIT", update_mode="REBUILD", post_id=42)
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (bundle / "audit-plan.json").write_text('{"update_mode":"REBUILD"}', encoding="utf-8")
            (bundle / "audit-gate-report.json").write_text('{"ok":true}', encoding="utf-8")
            context = self.make_context(root)
            with mock.patch.object(batch_approval.BUNDLE, "verify_audit_gate") as audit_gate:
                manifest = batch_approval.build_manifest("batch-audit", [bundle], context)
                manifest_path = root / "batch-manifest.json"
                batch_approval.BUNDLE.atomic_json(manifest_path, manifest)
                batch_approval.approve_manifest(
                    manifest_path, batch_approval.file_sha256(manifest_path), "operator",
                )
                self.assertGreaterEqual(audit_gate.call_count, 2)
            approval = json.loads((bundle / "approval.json").read_text(encoding="utf-8"))
            self.assertEqual(approval["files"], list(batch_approval.BUNDLE.approval_files(bundle)))
            self.assertIn("audit-plan.json", approval["files"])
            self.assertIn("audit-gate-report.json", approval["files"])

    def test_audit_batch_rejects_stale_audit_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self.make_bundle(root, "audit-job")
            request_path = bundle / "publish-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.update(task_type="AUDIT", update_mode="REBUILD", post_id=42)
            request_path.write_text(json.dumps(request), encoding="utf-8")
            context = self.make_context(root)
            with mock.patch.object(batch_approval.BUNDLE, "verify_audit_gate", side_effect=ValueError("SOURCE-STALE")):
                with self.assertRaisesRegex(ValueError, "SOURCE-STALE"):
                    batch_approval.build_manifest("batch-audit", [bundle], context)


class ProfileStatusTests(unittest.TestCase):
    def make_context(self, root: Path) -> Path:
        path = root / "publish-context.json"
        path.write_text(json.dumps({
            "version": 2,
            "content_profiles": {
                "blog": {
                    "endpoint": "posts", "post_type": "post", "status": "unconfirmed",
                    "ready": False, "pilot_allowed": False, "batch_ready": False,
                    "body_h1_count": 0, "html_policy": "clean_article",
                    "required_fields": ["title", "content", "slug"],
                    "required_capabilities": ["edit_posts", "upload_files"],
                    "missing_capabilities": [], "schema_hash": "schema-1",
                    "image_policy": {"format_policy": "preserve", "max_kb": 150, "max_width": 1200},
                    "seo_meta_adapter": "yoast",
                }
            },
        }), encoding="utf-8")
        return path

    def test_confirm_then_certify_enables_only_tested_profile_for_batch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            context_path = self.make_context(root)
            confirmed = profile_status.confirm(context_path, "blog", "operator", "schema-1")
            self.assertEqual(confirmed["status"], "pilot-ready")
            context = profile_status.load_context(context_path)
            profile = profile_status.get_profile(context, "blog")
            self.assertTrue(profile["pilot_allowed"])
            self.assertFalse(profile["batch_ready"])

            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "publish-request.json").write_text(json.dumps({
                "job_id": "pilot-blog", "run_id": "run-1", "content_type": "blog",
            }), encoding="utf-8")
            (bundle / "run-state.json").write_text(json.dumps({
                "job_id": "pilot-blog", "run_id": "run-1", "pilot": True,
                "verified": True, "wp_status": "draft", "content_type": "blog",
                "post_id": 42, "profile_hash": profile_status.profile_hash(profile),
            }), encoding="utf-8")
            render = root / "render-report.json"
            render.write_text(json.dumps({
                "ok": True, "post_id": 42,
                "checks": {name: True for name in profile_status.RENDER_CHECKS},
            }), encoding="utf-8")
            certified = profile_status.certify(
                context_path, "blog", bundle, render, "operator",
            )
            self.assertEqual(certified["status"], "batch-ready")
            profile = profile_status.get_profile(profile_status.load_context(context_path), "blog")
            self.assertTrue(profile["ready"])
            self.assertTrue(profile["batch_ready"])
            self.assertFalse(profile["pilot_allowed"])

    def test_render_qa_must_be_complete_before_batch_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            context_path = self.make_context(root)
            profile_status.confirm(context_path, "blog", "operator")
            profile = profile_status.get_profile(profile_status.load_context(context_path), "blog")
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "publish-request.json").write_text(
                '{"job_id":"pilot-blog","run_id":"run-1","content_type":"blog"}',
                encoding="utf-8",
            )
            (bundle / "run-state.json").write_text(json.dumps({
                "job_id": "pilot-blog", "run_id": "run-1", "pilot": True,
                "verified": True, "wp_status": "draft", "content_type": "blog",
                "post_id": 42, "profile_hash": profile_status.profile_hash(profile),
            }), encoding="utf-8")
            render = root / "render-report.json"
            render.write_text('{"ok":false,"post_id":42,"checks":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rendered QA incomplete"):
                profile_status.certify(context_path, "blog", bundle, render, "operator")


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
            self.assertEqual(generated["content_profiles"]["blog"]["status"], "unconfirmed")
            self.assertFalse(generated["content_profiles"]["blog"]["pilot_allowed"])
            self.assertFalse(generated["content_profiles"]["blog"]["batch_ready"])
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

    def test_item_runs_are_isolated_and_non_destructive(self):
        with tempfile.TemporaryDirectory() as td:
            projects = Path(td) / "projects"
            scaffold_mod.scaffold("demo-client", projects)
            first = item_scaffold_mod.scaffold_item("demo-client", "blog", "article", "run-one", projects)
            item = projects / "demo-client/content/blog/article"
            self.assertTrue((item / "runs/run-one/intake").is_dir())
            self.assertTrue((item / "runs/run-one/snapshot").is_dir())
            self.assertTrue((item / "runs/run-one/bundle").is_dir())
            self.assertTrue((item / "assets/original/run-one").is_dir())
            self.assertTrue((item / "assets/prepared/run-one").is_dir())
            self.assertTrue((item / "backups").is_dir())
            marker = item / "runs/run-one/bundle/approval.json"
            marker.write_text("approved", encoding="utf-8")
            second = item_scaffold_mod.scaffold_item("demo-client", "blog", "article", "run-one", projects)
            third = item_scaffold_mod.scaffold_item("demo-client", "blog", "article", "run-two", projects)
            self.assertEqual(second["created"], [])
            self.assertTrue(first["created"])
            self.assertTrue(third["created"])
            self.assertEqual(marker.read_text(encoding="utf-8"), "approved")
            self.assertTrue((item / "runs/run-two/bundle").is_dir())

    def test_item_scaffold_requires_project_and_valid_route(self):
        with tempfile.TemporaryDirectory() as td:
            projects = Path(td) / "projects"
            with self.assertRaisesRegex(ValueError, "scaffold the project"):
                item_scaffold_mod.scaffold_item("demo", "blog", "article", "run-one", projects)
            scaffold_mod.scaffold("demo", projects)
            with self.assertRaisesRegex(ValueError, "content_type"):
                item_scaffold_mod.scaffold_item("demo", "page", "article", "run-one", projects)
            with self.assertRaisesRegex(ValueError, "run_id"):
                item_scaffold_mod.scaffold_item("demo", "blog", "article", "../escape", projects)


class CredentialSetupTests(unittest.TestCase):
    def test_shared_root_file_selects_site_and_overrides_legacy_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shared = root / "wp-credentials.env"
            shared.write_text(
                credential_setup.credential_block("first-site", "https://first.example", "one", "secret-one")
                + credential_setup.credential_block("second-site", "https://second.example", "two", "secret-two"),
                encoding="utf-8",
            )
            shared.chmod(0o600)
            old = root / "projects" / "first-site" / "wp-credentials.env"
            old.parent.mkdir(parents=True)
            old.write_text('WP_URL="https://old.example"\nWP_USER="old"\nWP_APP_PASS="old"\n', encoding="utf-8")
            old.chmod(0o600)
            with mock.patch.object(credential_setup.WP_LIB, "KIT_ROOT", root), mock.patch.object(
                credential_setup.WP_LIB, "PROJECTS_ROOT", root / "projects"
            ):
                self.assertEqual(credential_setup.WP_LIB.load_credential("first-site"), ("https://first.example", "one", "secret-one"))
                self.assertEqual(credential_setup.WP_LIB.load_credential("second-site"), ("https://second.example", "two", "secret-two"))

    def test_optional_google_service_account_multiline_json(self):
        account = {"type": "service_account", "client_email": "bot@example.com", "private_key": "private\\nkey", "token_uri": "https://oauth.example/token"}
        value = json.dumps(account)
        text = 'GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON="""\n' + value + '\n"""\n'
        self.assertEqual(credential_setup.WP_LIB.google_service_account_from_env_text(text), account)
        self.assertIsNone(credential_setup.WP_LIB.google_service_account_from_env_text('GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON="""\n"""\n'))
        with self.assertRaisesRegex(ValueError, "service-account JSON"):
            credential_setup.WP_LIB.google_service_account_from_env_text('GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON="""\ninvalid\n"""\n')

    def test_project_file_uses_fixed_names_and_isolated_site_lookup(self):
        with tempfile.TemporaryDirectory() as td:
            projects = Path(td) / "projects"
            for site, url in (("first-site", "https://first.example"), ("second-site", "https://second.example")):
                folder = projects / site
                folder.mkdir(parents=True)
                path = folder / "wp-credentials.env"
                path.write_text(
                    f'WP_URL="{url}"\nWP_USER="editor"\nWP_APP_PASS="secret"\n',
                    encoding="utf-8",
                )
                path.chmod(0o600)
            with mock.patch.object(credential_setup.WP_LIB, "PROJECTS_ROOT", projects):
                self.assertEqual(
                    credential_setup.WP_LIB.load_credential("first-site"),
                    ("https://first.example", "editor", "secret"),
                )
                self.assertEqual(
                    credential_setup.WP_LIB.load_credential("second-site"),
                    ("https://second.example", "editor", "secret"),
                )

    def test_project_file_requires_all_three_values(self):
        with self.assertRaisesRegex(ValueError, "incomplete project credential"):
            credential_setup.WP_LIB.credential_from_project_text(
                'WP_URL="https://example.com"\nWP_USER="editor"\n'
            )

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
