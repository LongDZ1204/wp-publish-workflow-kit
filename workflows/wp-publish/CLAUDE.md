# Workflow `wp-publish` — prepare, approve and verify WordPress changes

## 1. Boundary

This is the single entrypoint for NEW and AUDIT publishing jobs. The v2 job contract owns route,
source and optional tracker configuration; WordPress only verifies current state.

Components remain shared across projects:

- `skills/wp-publish-new/` — creates or resumes one draft.
- `skills/wp-rest-publish/` — updates one existing item with backup and readback.
- `skills/image-onpage/` — prepares and validates existing images.
- `skills/strong-to-b/` — deterministic HTML normalization.
- `workflows/wp-publish/scripts/wp_intake.py` — immutable input snapshot.
- `workflows/wp-publish/scripts/wp_site_scan.py` — read-only site discovery.
- `workflows/wp-publish/scripts/wp_profile_status.py` — JIT confirmation and pilot certification.
- `workflows/wp-publish/scripts/wp_setup_credentials.py` — optional masked credential setup.
- `workflows/wp-publish/scripts/wp_learn.py` — records compact STOP/verify evidence for review.
- `workflows/wp-publish/scripts/wp_batch_approval.py` — one approval for an exact gated batch.

Never change route from WordPress state, write without approval for the current hash, publish a NEW
item automatically, retry an uncertain POST blindly, request Administrator just to unblock setup, or
overwrite a project context/profile during discovery.
AUDIT also requires an explicit, editorially approved `update_mode`: `MINIMAL_DIFF` or `REBUILD`.

## 2. Sources of truth

| Data | Source |
|---|---|
| NEW/AUDIT, source, content type, tracker | v2 job contract |
| Current post/media/schema | WordPress REST `context=edit` / `OPTIONS` |
| Brand, voice, language, market | `projects/<client>/context.md` |
| Site-specific publishing rules | `projects/<client>/publish-context.json` |
| Approved content | content-addressed bundle under the project content folder |
| Run state | `run-state.json` |
| Optional tracking state | configured tracker adapter |

Before a run, read [job-contract.md](references/job-contract.md),
[intake-contract.md](references/intake-contract.md), [bundle-contract.md](references/bundle-contract.md),
[state-machine.md](references/state-machine.md) and the two project context files.

## 3. First connection and just-in-time content profiles

1. Scaffold the project from `templates/project-skeleton/` with `scripts/wp_scaffold_project.py`.
2. Store all site credential variables in the root gitignored `.env.wp-publish` with mode `0600`.
   The parser reads this file directly; never source it into the shell or put secrets in AI context.
3. Run `scripts/wp_site_scan.py`; it may use only GET and OPTIONS.
4. Confirm only project-wide context during setup. Keep every content profile `unconfirmed`.
5. When the user first requests a content type, present only that proposed profile and its exact
   missing capabilities. Confirm endpoint, fields, H1 ownership, HTML policy, SEO meta and image
   policy, then run `scripts/wp_profile_status.py confirm` to make it `pilot-ready`.
6. Run one explicitly approved draft pilot for that type. After REST readback and rendered QA both
   pass, run `scripts/wp_profile_status.py certify` to make only that type `batch-ready`.

Do not ask the user to confirm unused content types. Detection is evidence, not confirmation, and a
blog pilot never enables service pages or products.

## 4. Per-job pipeline

### P0 — Normalize and lock input

- Validate with `scripts/wp_job_contract.py`.
- If the source is a Sheet row, first use `scripts/wp_sheet_contract.py`; merge the approved
  editorial AUDIT mode into that normalized row, then validate the complete job with
  `scripts/wp_job_contract.py`. The visible Sheet does not need an Update mode column.
- Lock Markdown, HTML or a Google Doc export with `scripts/wp_intake.py`.
- Load the matching profile. An `unconfirmed` type stops for JIT confirmation; a `pilot-ready` type
  permits only an explicit `--pilot`; normal jobs require `status=batch-ready` and `ready=true`.
- Initialize the atomic journal with `scripts/wp_state.py`.
- For AUDIT, preserve the selected `update_mode` in the request and run state; a missing mode stops
  before any WordPress write. It is not inferred from the source format or post history.

### P1 — Route reconciliation (read-only)

Fetch the exact WordPress target and run `scripts/wp_route.py`. NEW may create/resume only its own
draft; AUDIT must resolve exactly one existing target. Any mismatch is `ROUTE-CONFLICT`.

### P2 — Prepare bundle without external writes

- NEW calls `wp-publish-new`. AUDIT records a fresh raw snapshot and uniquely named backup,
  then locks snapshot metadata and source through `wp_bundle.py lock --snapshot-meta`.
- AUDIT `MINIMAL_DIFF` applies exact replacements to the current raw HTML. `REBUILD` prepares the
  approved replacement body. Both require `audit-plan.json` and `wp_audit_gate.py`; the plan must
  account for structure changes, frozen passages, and every removed image/link URL.
- Run `image-onpage` for every referenced image. Alt text is required except for explicitly
decorative images. Caption is optional and must not be invented merely to fill a field.
- Run `scripts/wp_strong.py`; the shared engine converts eligible `<strong>` to `<b>` while
preserving protected heading/link cases.
- Apply the confirmed `html_policy`: article cleanup may remove safe editor residue; builder markup is
preserved unless the profile explicitly allows a transform.
- Gate final H1 ownership, content, assets, unresolved tokens and transform report.
- For AUDIT, run `skills/wp-rest-publish/scripts/wp_audit_gate.py --bundle <bundle>` and present
  its inventory/diff with the prepared content. A rebuild may change structure only by the exact
  delta recorded in its plan; it does not inherit the minimal-diff structural freeze.

### P3 — Approval

Approval binds `publish-request.json`, prepared HTML, image manifest and transform report. Any change
invalidates approval and returns the run to preparation.
AUDIT additionally binds `audit-plan.json` and `audit-gate-report.json`. Re-run the audit gate before
approval; the executor verifies that both still describe the current backup and prepared body.

For multiple jobs, read [batch-approval.md](references/batch-approval.md). Gate all bundles, present
one complete manifest/hash, and request one confirmation for the batch. Each job still receives its
own approval/state and WordPress readback. The manifest must load the project publish context and
reject every content type not marked `batch-ready`; never approve future or changed jobs implicitly.

### P4 — WordPress write and readback

- NEW writes draft only to the profile endpoint.
- AUDIT compares the fresh revision before writing.
- AUDIT dry-runs `wp_push_audit.py`, then executes it with `--approval-hash`. That executor checks
  approval and WordPress post ID/permalink/status/modified/raw hash before the write, again after
  any media uploads, and verifies the complete REST body and required meta after the write.
- Replace asset tokens only with verified WordPress media URLs.
- GET the item with `context=edit` and compare ID, status, title, content and required meta.
- For AUDIT, inspect the rendered public page on desktop and mobile, including images and links;
  inspect schema when the content change affects it. REST readback does not prove public rendering.
- A pilot records its content type and profile hash in `run-state.json`. Inspect the authenticated
  draft render and record `content`, `images`, `heading`, `links` and `seo_meta` in
  `render-report.json`; only then may `wp_profile_status.py certify` enable batch use.

### P5 — Optional tracker readback

- `tracker.type=none`: complete after WordPress readback.
- `tracker.type=google_sheet`: update by immutable Row ID with `scripts/wp_sheet_io.py`, read the row
  back, then transition through `TRACKER_VERIFIED`.

## 5. Completion gate

A run is complete only when its bundle and approval are current, final HTML/image gates pass,
WordPress readback matches, NEW remains draft, AUDIT has a backup, and any configured tracker is read
back successfully. A local dry-run is not external completion.
An AUDIT also needs its approved mode, audit gate report and rendered-page QA before completion.

Pilot completion and production readiness are separate: a successful pilot becomes `batch-ready`
only after certification. A later profile/schema change invalidates the batch manifest and requires
reconfirmation or another pilot as appropriate.

## 6. Self-test

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 -m unittest discover -s workflows/wp-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-publish-new/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-rest-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-rest-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
python3 -m pytest tools/strong-to-b/test_strong_to_b.py -q
```
