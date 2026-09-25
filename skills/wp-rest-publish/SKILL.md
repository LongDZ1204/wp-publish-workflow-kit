---
name: wp-rest-publish
description: Execute an approved AUDIT update to one existing WordPress post from a fresh backup. Use through wp-publish for either MINIMAL_DIFF or REBUILD; never create a post or diagnose what the editorial change should be.
---

# WordPress AUDIT update

This is the AUDIT executor called by `wp-publish`. The editorial audit decides and approves
`update_mode=MINIMAL_DIFF|REBUILD` before this skill starts. Never infer the mode from the slug,
rank, or size of the draft. Read `../../workflows/wp-publish/CLAUDE.md` and the selected project's
`context.md` and `publish-context.json` first.

## Two preparation modes

- `MINIMAL_DIFF`: fetch fresh `content.raw`, list exact `{old,new}` edits, and use
  `wp_apply_edits.py` so every `old` matches once. Keep unrelated HTML, blocks, shortcodes,
  links and media. Put the edits in `audit-plan.json` too.
- `REBUILD`: prepare the approved replacement body from the editorial source. The plan needs a
  `rebuild_reason`, exact expected changes in H1/H2/H3/table/image/iframe counts, passages to
  preserve, and exact image URLs and link/anchor pairs approved for removal. Reusing an image through an `asset://` token
  must retain its `existing_url` in the image manifest. A full body rewrite is allowed only
  under this mode.

Both modes use `wp_audit_gate.py`; [audit-publish-flow.md](../../docs/audit-publish-flow.md)
defines `audit-plan.json` and the step-by-step commands. Semantic quality and the decision to
remove a passage remain editorial review, not an HTML counter's decision.

## Required execution gates

1. `wp_fetch.py` reads the exact post with `context=edit` and creates a dated backup that cannot
   overwrite an earlier backup. Lock its metadata with the source in `wp_bundle.py lock
   --snapshot-meta`.
2. Prepare the final HTML, image manifest and strong-to-b transform report. Run the shared HTML
   gate, then `wp_audit_gate.py`. Its report and the plan are included in the approval hash.
3. Present the source diff, inventory changes, meta fields and current hash. Create
   `approval.json` only after the operator approves those exact bytes.
4. Run `wp_push_audit.py` without `--execute` to show the plan. Execute only with the same
   `--approval-hash`. The script rechecks the approval, backup, post ID, permalink, status,
   `modified` value and raw HTML hash before any post update. It uploads/reuses approved media,
   rechecks WordPress after the uploads, then writes the approved body and reads it back.
5. Inspect the rendered post on desktop and mobile, check the public content, images, links,
   title/meta and any page-specific schema. Complete optional tracker writeback only after the
   WordPress and render checks pass. A REST readback alone is not public QA.

`wp_push_verify.py` is a read-only legacy probe (`--verify-only`); it refuses writes. An uncertain
POST or a changed WordPress revision is a STOP requiring reconciliation, never a blind retry.
