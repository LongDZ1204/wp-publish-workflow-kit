---
name: wp-publish-new
description: Prepare an approved publish bundle, upload/reuse media safely, and create or resume exactly one WordPress draft for a NEW article. Use only through the wp-publish workflow when Sheet intent is NEW.
---

# WordPress publish new

Create a WordPress **draft**, never a published post. The Sheet declares `NEW`; WordPress state only
verifies that this is safe. If a slug already belongs to an unrelated post, stop with
`ROUTE-CONFLICT`.

## Required upstream context

Read, in order:

1. `workflows/wp-publish/CLAUDE.md`
2. `workflows/wp-publish/references/bundle-contract.md`
3. `projects/<client>/context.md`
4. `projects/<client>/publish-context.json` (select the job's confirmed `content_type` profile)

Do not run a normal write unless the requested content-type profile has `status=batch-ready` and
`ready=true`. The only exception is a one-time, operator-approved draft pilot when that profile has
`status=pilot-ready` and `pilot_allowed=true`; pass `--pilot` to both the gate and executor. A pilot
can never publish the post or enable another content type.

## Source and draft storage

- Google Doc remains the editorial source. Export it to `runs/<run-id>/work/`, snapshot the converted
  content to `runs/<run-id>/intake/`, then lock that file. The bundle keeps a Google Doc
  `source.snapshot.html|md` and its checksum; it does not keep successive draft versions.
- A local Markdown/HTML source is copied by `wp_intake.py` to the run's `intake/`. Lock that copy;
  `source-lock.json` stores its path and checksum. Changing it invalidates approval.
- Supplied/ZIP images go in `assets/original/<run-id>/`; prepared images go in
  `assets/prepared/<run-id>/`. The bundle stores only mappings and evidence.
- The publish-ready artifact lives in
  `projects/<client>/content/<content-type>/<slug>/runs/<run-id>/bundle/`.

## Prepare and approve

Với Google Doc, export `application/zip` (HTML + ảnh) rồi chuẩn hóa trước khi khóa bundle:

```bash
python3 skills/wp-publish-new/scripts/wp_doc_export.py \
  --zip '<run-dir>/work/doc-export.zip' --mapping '<run-dir>/work/doc-image-map.json' \
  --html-out '<run-dir>/work/content.rendered.html' \
  --image-request-out '<run-dir>/work/image-request.json'
```

Mapping phải cấp alt/caption/filename rõ ràng; Google Doc không phải nguồn alt. Source phải có đúng một
H1 (Google Doc dùng Heading 1). Script loại style rác của Docs, chỉ bỏ paragraph mang style `title` của
Docs nếu có, giữ H1 cùng heading/list/link/table và thay ảnh bằng `asset://<asset_id>`.
Mỗi `source_output` trong mapping trỏ tới `<item>/assets/original/<run-id>/<filename>`. Chạy
`wp_intake.py` trên `content.rendered.html` vào `<run-dir>/intake/` trước khi khóa bundle.

```bash
python3 skills/wp-publish-new/scripts/wp_bundle.py lock \
  --request '<run-dir>/work/row.normalized.json' \
  --source '<run-dir>/intake/content.snapshot.html' --source-type google_doc \
  --source-ref '<google-doc-url>' --source-revision '<Docs revision/modifiedTime>' \
  --bundle '<bundle-dir>'

python3 workflows/wp-publish/scripts/wp_strong.py \
  --input '<run-dir>/work/content.rendered.html' --output '<bundle-dir>/content.prepared.html' \
  --report '<bundle-dir>/transform-report.json'

python3 skills/wp-publish-new/scripts/wp_gate.py \
  --bundle '<bundle-dir>' --profile 'projects/<client>/publish-context.json' \
  --content-type '<blog|service-page|product>' --phase prepared
```

Only after operator explicitly approves the displayed bundle:

```bash
python3 skills/wp-publish-new/scripts/wp_bundle.py hash --bundle '<bundle-dir>'

python3 skills/wp-publish-new/scripts/wp_bundle.py approve \
  --bundle '<bundle-dir>' --approved-by 'operator'
```

Any change to the four approval inputs invalidates the approval.

## Draft write

Always run the dry plan first:

```bash
python3 skills/wp-publish-new/scripts/wp_push_draft.py \
  --bundle '<bundle-dir>' --site-key '<site>' \
  --profile 'projects/<client>/publish-context.json'
```

Then, only for the same approved hash:

```bash
python3 skills/wp-publish-new/scripts/wp_push_draft.py \
  --bundle '<bundle-dir>' --site-key '<site>' \
  --profile 'projects/<client>/publish-context.json' --execute \
  --approval-hash '<sha256>'
```

Append `--pilot` only for the explicitly enabled one-time pilot described above.

After a pilot, inspect the authenticated draft render and write `<bundle-dir>/render-report.json`
with `ok=true`,
the exact `post_id`, and true checks for `content`, `images`, `heading`, `links` and `seo_meta`. Then
run `workflows/wp-publish/scripts/wp_profile_status.py certify`; only this transition enables batch.

The executor uploads only `prepare-upload` assets, replaces `asset://<asset_id>` tokens, creates one
draft, and immediately stores the returned post/media IDs. It refuses a blind retry after an
uncertain POST; reconcile WordPress first and resume only the same `run_id`.

## Completion gate

- Approval hash is current.
- Final HTML matches the profile's `body_h1_count` (0 when the theme's post title is the page H1).
- Final HTML has no local path, Markdown image marker, or unresolved asset token.
- WordPress GET `context=edit` matches title, slug, content and status `draft`.
- The configured tracker, if any, has been written and read back.
