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
mkdir -p projects/example-client
cp templates/context.example.md projects/example-client/context.md
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client example-client
```

The scaffold creates `publish-context.json`, `scans/` and separate content folders for `blog`,
`service-page` and `product`. It is idempotent and never overwrites existing context. Shared skills
and tools remain at repository level.

## 3. Configure WordPress credentials

Use a dedicated account. The exact required capabilities are checked later per content type; do not
grant Administrator merely to make setup pass.

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py \
  --site-key example-site --url https://example.com --user wp-publish \
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
  --client example-client --site-key example-site
```

The scanner uses only `GET` and `OPTIONS`. It inventories the authenticated identity, capabilities,
REST post types, taxonomies and endpoint schemas. It writes `site-scan.json` and
`publish-context.proposed.json` under a timestamped `projects/example-client/scans/` folder; it does
not overwrite the active profile.

Review and confirm the profile for the first content type you will use: endpoint/post type, fields,
taxonomies, H1 ownership, HTML policy, SEO meta, image policy and exact missing capabilities. Copy
only confirmed values into `projects/example-client/publish-context.json` and set that profile's
`ready=true`. Other content types remain disabled until separately confirmed.

## 5. Prepare a tracker-free job

Create a v2 job using [the job contract](../workflows/wp-publish/references/job-contract.md). Its
`source.adapter` can be `local_markdown`, `local_html` or `google_doc`; set
`tracker.type` to `none`.

```bash
python3 workflows/wp-publish/scripts/wp_intake.py \
  --adapter local_html --source article.html --source-ref article.html \
  --assets-json assets.json --out projects/example-client/content/blog/article/intake
```

The source may originate anywhere. Intake requires a readable content snapshot and a valid asset
inventory; downstream gates enforce the confirmed site profile.

## 6. Enable Google Sheets later (optional)

Follow [google-sheet-template.md](google-sheet-template.md), then change the project tracker to
`google_sheet`. The Sheet adapter validates a row and emits the same job contract. A tracker-enabled
run is complete only after Sheet writeback and readback; a tracker-free run completes after WordPress
readback.

## 7. Run checks

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 scripts/check_distribution.py
```

## Publishing boundary

- `NEW` remains draft-only.
- `AUDIT` requires a fresh WordPress snapshot and immutable backup.
- Every external write requires approval for the current bundle hash.
- A POST timeout requires GET/reconciliation; never retry blindly.
- HTML/image transforms and WordPress readback must pass the confirmed content profile.
