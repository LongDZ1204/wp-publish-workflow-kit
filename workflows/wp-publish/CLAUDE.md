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
- `workflows/wp-publish/scripts/wp_setup_credentials.py` — optional masked credential setup.
- `workflows/wp-publish/scripts/wp_learn.py` — records compact STOP/verify evidence for review.
- `workflows/wp-publish/scripts/wp_batch_approval.py` — one approval for an exact gated batch.

Never change route from WordPress state, write without approval for the current hash, publish a NEW
item automatically, retry an uncertain POST blindly, request Administrator just to unblock setup, or
overwrite a project context/profile during discovery.

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

## 3. First connection and first content type

1. Scaffold the project from `templates/project-skeleton/` with `scripts/wp_scaffold_project.py`.
2. Store all site credential variables in the root gitignored `.env.wp-publish` with mode `0600`.
   The parser reads this file directly; never source it into the shell or put secrets in AI context.
3. Run `scripts/wp_site_scan.py`; it may use only GET and OPTIONS.
4. Present the proposed blog/service-page/product profile and exact missing capabilities.
5. Confirm endpoint, fields, H1 ownership, HTML policy, SEO meta and image policy with the user.
6. Set only the confirmed content type to `ready=true`.

Do not invent site rules. The scan proposal is evidence, not active configuration.

## 4. Per-job pipeline

### P0 — Normalize and lock input

- Validate with `scripts/wp_job_contract.py`.
- If the source is a Sheet row, first use `scripts/wp_sheet_contract.py`; it emits the same job.
- Lock Markdown, HTML or a Google Doc export with `scripts/wp_intake.py`.
- Load the matching confirmed content profile. Missing context or capability stops the run.
- Initialize the atomic journal with `scripts/wp_state.py`.

### P1 — Route reconciliation (read-only)

Fetch the exact WordPress target and run `scripts/wp_route.py`. NEW may create/resume only its own
draft; AUDIT must resolve exactly one existing target. Any mismatch is `ROUTE-CONFLICT`.

### P2 — Prepare bundle without external writes

- NEW calls `wp-publish-new`; AUDIT records a fresh raw snapshot and immutable backup.
- Run `image-onpage` for every referenced image. Alt text is required except for explicitly
decorative images. Caption is optional and must not be invented merely to fill a field.
- Run `scripts/wp_strong.py`; the shared engine converts eligible `<strong>` to `<b>` while
preserving protected heading/link cases.
- Apply the confirmed `html_policy`: article cleanup may remove safe editor residue; builder markup is
preserved unless the profile explicitly allows a transform.
- Gate final H1 ownership, content, assets, unresolved tokens and transform report.

### P3 — Approval

Approval binds `publish-request.json`, prepared HTML, image manifest and transform report. Any change
invalidates approval and returns the run to preparation.

For multiple jobs, read [batch-approval.md](references/batch-approval.md). Gate all bundles, present
one complete manifest/hash, and request one confirmation for the batch. Each job still receives its
own approval/state and WordPress readback; never approve future or changed jobs implicitly.

### P4 — WordPress write and readback

- NEW writes draft only to the profile endpoint.
- AUDIT compares the fresh revision before writing.
- Replace asset tokens only with verified WordPress media URLs.
- GET the item with `context=edit` and compare ID, status, title, content and required meta.

### P5 — Optional tracker readback

- `tracker.type=none`: complete after WordPress readback.
- `tracker.type=google_sheet`: update by immutable Row ID with `scripts/wp_sheet_io.py`, read the row
  back, then transition through `TRACKER_VERIFIED`.

## 5. Completion gate

A run is complete only when its bundle and approval are current, final HTML/image gates pass,
WordPress readback matches, NEW remains draft, AUDIT has a backup, and any configured tracker is read
back successfully. A local dry-run is not external completion.

## 6. Self-test

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 -m unittest discover -s workflows/wp-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-publish-new/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-rest-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
python3 -m pytest tools/strong-to-b/test_strong_to_b.py -q
```
