# Setup

This is the maintainer path. Setup is read-only until an approved pilot is run.

## 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

## 2. Create the project context

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client example-client
```

The command copies the visible `templates/project-skeleton/` into `projects/example-client/`, fills
the client placeholders, and creates separate content folders for `blog`, `service-page` and
`product`. It is idempotent and never overwrites existing files. Edit and confirm
`projects/example-client/context.md` before enabling a publishing profile. Shared skills and tools
remain at repository level.

## 3. Configure WordPress credentials

Use a dedicated account. The exact required capabilities are checked later per content type; do not
grant Administrator merely to make setup pass.

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py \
  --site-key example-client --url https://example.com --user wp-publish \
  --input-mode dialog
```

The native masked dialog verifies the account and stores three site-prefixed variables in the root,
ignored `.env.wp-publish` with mode `0600`. Multiple sites share that one file. The parser reads it
directly; do not `source` it into the shell. Never put a password in chat, project context, job,
Sheet or command argument.

Existing installs can migrate without deleting the legacy file:

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py --migrate-legacy
```

After verifying the new file works, securely delete the old local file yourself. Do not revoke the
Application Password unless you also intend to rotate it. The migration command never deletes the
legacy file automatically.

## 4. Run read-only discovery

```bash
python3 workflows/wp-publish/scripts/wp_site_scan.py \
  --client example-client --site-key example-client
```

The scanner uses only `GET` and `OPTIONS`. It inventories the authenticated identity, capabilities,
REST post types, taxonomies and endpoint schemas. It writes `site-scan.json` and
`publish-context.proposed.json` under a timestamped `projects/example-client/scans/` folder; it does
not overwrite the active profile.

Confirm project-wide context after the scan, but leave all content profiles unconfirmed. When the
user first requests a content type, review only that type's endpoint/post type, fields, taxonomies,
H1 ownership, HTML policy, SEO meta, image policy and exact missing capabilities. Copy the confirmed
values into `projects/example-client/publish-context.json`, then mark it pilot-ready:

```bash
python3 workflows/wp-publish/scripts/wp_profile_status.py confirm \
  --context projects/example-client/publish-context.json \
  --content-type blog --confirmed-by operator \
  --expected-schema-hash '<hash-from-current-scan>'
```

Other content types remain `unconfirmed` until the user asks for them.

## 5. Prepare a tracker-free job

Create a v2 job using [the job contract](../workflows/wp-publish/references/job-contract.md). Its
`source.adapter` can be `local_markdown`, `local_html` or `google_doc`; set
`tracker.type` to `none`.

Create a folder for the article and this publication attempt. Repeating the same command preserves
existing files; a later audit of the same URL gets a new `run-id`:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_item.py \
  --client example-client --content-type blog --slug article --run-id 2026-09-25-new-01
```

```bash
python3 workflows/wp-publish/scripts/wp_intake.py \
  --adapter local_html --source article.html --source-ref article.html \
  --assets-json assets.json \
  --out projects/example-client/content/blog/article/runs/2026-09-25-new-01/intake
```

The source may originate anywhere. Intake stores an immutable copy; use that snapshot as the
`wp_bundle.py lock --source` file so the bundle does not depend on an external editable source.
Put supplied/downloaded image originals under `assets/original/<run-id>/`, prepared versions under
`assets/prepared/<run-id>/`, and point the image manifest into that same run's `bundle/`. Images
already on WordPress can stay as URLs without downloading. See
[project-folders.md](../workflows/wp-publish/references/project-folders.md) for every path.

## 6. Run and certify one draft pilot

Prepare the requested type, obtain approval for its exact bundle hash, and execute one NEW draft with
`--pilot`. After REST readback passes, inspect the authenticated draft render. Save evidence such as:

```json
{
  "version": 1,
  "ok": true,
  "post_id": 123,
  "checks": {
    "content": true,
    "images": true,
    "heading": true,
    "links": true,
    "seo_meta": true
  }
}
```

Then certify only that content type:

```bash
python3 workflows/wp-publish/scripts/wp_profile_status.py certify \
  --context projects/example-client/publish-context.json \
  --content-type blog --bundle projects/example-client/content/blog/article/runs/2026-09-25-new-01/bundle \
  --render-report projects/example-client/content/blog/article/runs/2026-09-25-new-01/bundle/render-report.json \
  --certified-by operator
```

The profile is now `batch-ready`. Batch manifests bind its current hash and ask once for the exact
set of prepared jobs; they do not ask again article by article.

## 7. Enable Google Sheets later (optional)

Follow [google-sheet-template.md](google-sheet-template.md), then change the project tracker to
`google_sheet` with the spreadsheet ID and tab name. Give the running agent an authorized Google
Sheets connector and test read plus writeback on one row; the kit does not contain a standalone
Sheets API client. The Sheet adapter validates a row and emits the same job contract. A tracker-enabled
run is complete only after Sheet writeback and readback; a tracker-free run completes after WordPress
readback.

## 8. Run checks

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 scripts/check_distribution.py
```

## Publishing boundary

- `NEW` remains draft-only.
- `AUDIT` requires a selected `MINIMAL_DIFF` or `REBUILD`, fresh WordPress snapshot and uniquely
  named backup. Follow [the AUDIT publishing flow](audit-publish-flow.md) for its mode-specific
  gate, approval and executor.
- Every external write requires approval for the current bundle hash.
- A POST timeout requires GET/reconciliation; never retry blindly.
- HTML/image transforms and WordPress readback must pass the confirmed content profile.
