import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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

    def test_new_combined_locator_becomes_slug(self):
        row = sheet.validate({
            "Row ID": "r3", "Loại bài": "NEW", "Nguồn content": "x.md",
            "Slug / URL WP": "new-post", "Bài / Title": "New post",
        })
        self.assertEqual(row["slug"], "new-post")


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
            project.mkdir(parents=True)
            (project / "context.md").write_text("# approved context\n", encoding="utf-8")
            first = scaffold_mod.scaffold("demo-client", projects)
            self.assertTrue(first["created"])
            profile = project / "knowledge/publish-context.json"
            generated = json.loads(profile.read_text(encoding="utf-8"))
            self.assertFalse(generated["ready"])
            self.assertFalse(generated["pilot_allowed"])
            self.assertIsNone(generated["spreadsheet_id"])
            self.assertEqual(generated["timezone"], "UTC")
            profile.write_text('{"ready": true}\n', encoding="utf-8")
            second = scaffold_mod.scaffold("demo-client", projects)
            self.assertEqual(profile.read_text(encoding="utf-8"), '{"ready": true}\n')
            self.assertEqual(second["created"], [])

    def test_scaffold_requires_existing_context(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "BRAND-MISSING"):
                scaffold_mod.scaffold("missing-client", Path(td))


if __name__ == "__main__":
    unittest.main()
