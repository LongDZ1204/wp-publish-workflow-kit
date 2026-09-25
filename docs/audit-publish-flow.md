# AUDIT publishing: MINIMAL_DIFF and REBUILD

This document covers **publishing an editorially approved change to an existing WordPress item**.
The editorial audit decides what to change and selects the mode. This kit prepares, approves,
writes and verifies that decision. No AUDIT route creates a new post or changes its permalink.

## 1. Select the mode before preparation

The v2 job must declare `task_type: "AUDIT"`, the exact `post_id` or `target_url`, and one of:

| Mode | Use when | HTML preparation |
|---|---|---|
| `MINIMAL_DIFF` | The approved change is a bounded set of passages in the existing body | Apply unique `{old,new}` replacements to fresh `content.raw` with `wp_apply_edits.py`. |
| `REBUILD` | The approved editorial plan replaces the article body or its structure | Build the full replacement HTML from the approved source; inventory every removed image/link and expected structure change. |

Do not derive the mode from ranking, slug, source format or word count. The Sheet's visible columns
may omit it: merge the approved editorial decision into the normalized job **before** running
`wp_job_contract.py`. The final job stops if `update_mode` is missing.

## 2. Fetch and lock the WordPress baseline

```bash
python3 skills/wp-rest-publish/scripts/wp_fetch.py \
  --site '<site-key>' --id '<post-id>' \
  --out '<item>/runs/<run-id>/snapshot' --backup '<item>/backups'
```

The fetch writes `content.raw` and a metadata JSON file. Every backup has a UTC timestamp and
cannot overwrite an earlier backup. The metadata includes post ID, status, `modified`, URL,
raw SHA-256, backup path and backup SHA-256. Keep those files private to the project.

Prepare a v2 request containing the approved `update_mode`, intended title/meta, site/client,
run/job IDs, source and exact target. The lock command copies the WordPress baseline fields from
the fetch metadata into `publish-request.json` and binds the editorial source:

```bash
python3 skills/wp-publish-new/scripts/wp_bundle.py lock \
  --request '<request.json>' --source '<approved-source.html>' \
  --source-type local_html --source-ref '<approved-source.html>' \
  --snapshot-meta '<snapshot>/<post-id>.meta.json' --bundle '<item>/bundle'
```

The source can also be a locked Markdown or Google Doc export. For a Google Doc, export it first,
then lock the local snapshot. A later source change invalidates approval.

## 3. Prepare and gate the body

For `MINIMAL_DIFF`, dry-run exact replacements and create the candidate body:

```bash
python3 skills/wp-rest-publish/scripts/wp_apply_edits.py \
  --html '<snapshot>/<post-id>.raw.html' --edits edits.json --dry-run
python3 skills/wp-rest-publish/scripts/wp_apply_edits.py \
  --html '<snapshot>/<post-id>.raw.html' --edits edits.json --out candidate.html
```

For `REBUILD`, `candidate.html` is the full HTML created from the approved editorial source.
Prepare images through `image-onpage`, retaining live URLs by default and uploading only new or
approved replacement assets. Then run the shared strong-to-b transform on the candidate to
produce `bundle/content.prepared.html` and `bundle/transform-report.json`.

Create `bundle/audit-plan.json` before approval. Example for a rebuild:

```json
{
  "update_mode": "REBUILD",
  "rebuild_reason": "Approved editorial diagnosis and replacement outline",
  "expected_structure_delta": {
    "h1": 0, "h2": 2, "h3": 3, "table": 1, "img": 1, "iframe": 0
  },
  "keep_passages": ["An approved passage that must remain verbatim"],
  "approved_removed_image_urls": [],
  "approved_removed_links": []
}
```

For `MINIMAL_DIFF`, use the same inventory fields and replace `rebuild_reason` with a nonempty
`edits` array of exact `{old,new}` objects. Structure deltas may be nonzero only when the
approved edits explain them. Every URL that disappears from the old image/link inventory must
appear in the appropriate approved-removal list; link entries include both `href` and `anchor`,
for example `{"href":"https://example.com/old/","anchor":"Old anchor"}`. The lists must match
exactly. The gate resolves
`asset://` tokens for reused images through the manifest's `existing_url` before comparing.

Run both gates:

```bash
python3 skills/wp-publish-new/scripts/wp_gate.py \
  --bundle '<item>/bundle' --profile 'projects/<client>/publish-context.json' \
  --content-type '<blog|service-page|product>' --phase prepared
python3 skills/wp-rest-publish/scripts/wp_audit_gate.py --bundle '<item>/bundle'
```

The audit gate checks the backup hash, mode, H1/H2/H3/table/image/iframe deltas, frozen passages,
and removed image URLs and link/anchor pairs. For minimal edits it also checks each `old` appears exactly once in
the backup and each nonempty `new` appears in the prepared body. Human review still decides
whether the rewrite answers the right queries, retains useful passages and keeps schema accurate.

## 4. Approve, execute and verify

Show the operator the candidate diff, audit gate report, image table, meta changes and hash.
Only after explicit approval of those bytes:

```bash
python3 skills/wp-publish-new/scripts/wp_bundle.py approve \
  --bundle '<item>/bundle' --approved-by '<operator>'
python3 skills/wp-rest-publish/scripts/wp_push_audit.py \
  --bundle '<item>/bundle' --site-key '<site-key>' \
  --profile 'projects/<client>/publish-context.json'
python3 skills/wp-rest-publish/scripts/wp_push_audit.py \
  --bundle '<item>/bundle' --site-key '<site-key>' \
  --profile 'projects/<client>/publish-context.json' \
  --execute --approval-hash '<approved-hash>'
```

The executor is a dry-run by default. A write requires a current six-file AUDIT approval,
an `APPROVED` run state and an unchanged WordPress baseline. It uploads approved media,
rechecks the post after uploads, then updates the existing ID without sending a new status or
permalink. It GETs `context=edit` afterward and compares exact body HTML, status, title and
submitted meta fields. A timeout has uncertain outcome and must be reconciled before any retry.

Inspect the rendered page on desktop/mobile, confirm public content, images, links and SEO meta,
and verify schema when the article change affects it. Record the WordPress revision/rollback
reference. Only then write and read back an optional Sheet tracker and mark the run complete.
The REST success message is not proof that the public page or its cache is current.
