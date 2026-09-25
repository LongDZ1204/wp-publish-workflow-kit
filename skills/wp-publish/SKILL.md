---
name: wp-publish
description: Prepare and publish NEW or AUDIT WordPress jobs from Markdown, HTML or Google Doc snapshots, with optional Google Sheet tracking, per-project content profiles, approval hashes and readback gates.
---

# WordPress publish workflow

Use this skill as the only public entrypoint for a WordPress publishing job.

Before every run, read:

1. `../../workflows/wp-publish/CLAUDE.md`
2. `../../workflows/wp-publish/references/job-contract.md`
3. `../../workflows/wp-publish/references/intake-contract.md`
4. `../../workflows/wp-publish/references/bundle-contract.md`
5. `../../workflows/wp-publish/references/state-machine.md`
6. `projects/<client>/context.md`
7. `projects/<client>/publish-context.json`

The v2 job declares NEW/AUDIT and source adapter. Google Sheets is an optional tracker/adapter, not a
prerequisite. Never infer or switch route from a slug.
When Sheets is enabled, use an authorized connector to read/write the configured spreadsheet and
tab. `wp_sheet_contract.py` validates a row; `wp_sheet_io.py` prepares an allow-listed patch and
verifies connector readback. Neither script is a Google Sheets network client.

- `NEW` creates or resumes exactly one WordPress draft; it never publishes automatically.
- `AUDIT` updates exactly one existing item from a fresh snapshot and uniquely named backup.
  Its approved editorial plan must declare `MINIMAL_DIFF` or `REBUILD`; read
  `../../docs/audit-publish-flow.md` for the distinct preparation and gate requirements.
- Every referenced image passes `image-onpage`; missing non-decorative alt text stops the run, while a
  missing caption remains empty unless the source or approved context supplies one.
- Every prepared HTML file passes the deterministic shared `strong-to-b` engine.
- External writes require explicit approval for the current bundle hash. AUDIT approval also binds
  its mode, change plan and audit gate report; `wp_push_audit.py` is dry-run by default.
- Completion requires WordPress readback and, only when configured, tracker readback.

For a bulk request, also read `../../workflows/wp-publish/references/batch-approval.md`. Prepare and
gate every job, show one exact batch manifest/hash, and ask once; each job still executes and verifies
independently. Batch creation is allowed only for content-type profiles certified `batch-ready`.

For a new project, scaffold and scan read-only, then confirm project-wide context only. Confirm a
content-type profile just in time when the user first requests that type; after one approved draft
pilot passes REST readback and rendered QA, certify only that profile for batch use. Credentials stay
in one ignored root `.env.wp-publish`; do not copy secrets into project folders, jobs, logs or Git.
For each job, create its item workspace with `wp_scaffold_item.py` and keep the locked source,
images, backup and bundle under the paths in `workflows/wp-publish/references/project-folders.md`.
