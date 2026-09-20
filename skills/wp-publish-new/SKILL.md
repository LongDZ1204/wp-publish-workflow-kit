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
4. `projects/<client>/knowledge/publish-context.md`

Do not run a write command unless the site publish context has `ready=true`. The only exception is a
one-time, operator-approved draft pilot when the profile has `pilot_allowed=true`; pass `--pilot` to
both the gate and executor. A pilot can never publish the post.

## Source and draft storage

- Google Doc remains the editorial source. Pull it once with the Google Docs/Drive connector, export
  the current text to a temporary/local Markdown file, then run `wp_bundle.py lock`. The bundle keeps
  one `source.snapshot.md` plus its checksum; it does not keep successive draft versions.
- A local Markdown source is not copied. Its absolute path and checksum are stored in
  `source-lock.json`.
- Images live in `projects/<client>/content/06-assets/`; the bundle only stores mappings.
- The publish-ready artifact lives in
  `projects/<client>/content/07-publish-ready/<slug>/`.

## Prepare and approve

Với Google Doc, export `application/zip` (HTML + ảnh) rồi chuẩn hóa trước khi khóa bundle:

```bash
python3 skills/wp-publish-new/scripts/wp_doc_export.py \
  --zip doc-export.zip --mapping doc-image-map.json \
  --html-out content.rendered.html --image-request-out image-request.json
```

Mapping phải cấp alt/caption/filename rõ ràng; Google Doc không phải nguồn alt. Source phải có đúng một
H1 (Google Doc dùng Heading 1). Script loại style rác của Docs, chỉ bỏ paragraph mang style `title` của
Docs nếu có, giữ H1 cùng heading/list/link/table và thay ảnh bằng `asset://<asset_id>`.

```bash
python3 skills/wp-publish-new/scripts/wp_bundle.py lock \
  --request row.normalized.json --source article.md --source-type google_doc \
  --source-ref '<google-doc-url>' --source-revision '<Docs revision/modifiedTime>' \
  --bundle '<bundle-dir>'

python3 workflows/wp-publish/scripts/wp_strong.py \
  --input content.rendered.html --output '<bundle-dir>/content.prepared.html' \
  --report '<bundle-dir>/transform-report.json'

python3 skills/wp-publish-new/scripts/wp_gate.py \
  --bundle '<bundle-dir>' --profile 'projects/<client>/knowledge/publish-context.json' \
  --phase prepared
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
  --profile 'projects/<client>/knowledge/publish-context.json'
```

Then, only for the same approved hash:

```bash
python3 skills/wp-publish-new/scripts/wp_push_draft.py \
  --bundle '<bundle-dir>' --site-key '<site>' \
  --profile 'projects/<client>/knowledge/publish-context.json' --execute \
  --approval-hash '<sha256>'
```

Append `--pilot` only for the explicitly enabled one-time pilot described above.

The executor uploads only `prepare-upload` assets, replaces `asset://<asset_id>` tokens, creates one
draft, and immediately stores the returned post/media IDs. It refuses a blind retry after an
uncertain POST; reconcile WordPress first and resume only the same `run_id`.

## Completion gate

- Approval hash is current.
- Final HTML matches the profile's `body_h1_count` (0 when the theme's post title is the page H1).
- Final HTML has no local path, Markdown image marker, or unresolved asset token.
- WordPress GET `context=edit` matches title, slug, content and status `draft`.
- The workflow has written and read back the same Sheet row.
