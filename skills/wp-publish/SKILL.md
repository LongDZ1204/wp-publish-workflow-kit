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

- `NEW` creates or resumes exactly one WordPress draft; it never publishes automatically.
- `AUDIT` updates exactly one existing item from a fresh snapshot and immutable backup.
- Every referenced image passes `image-onpage`; missing non-decorative alt text stops the run, while a
  missing caption remains empty unless the source or approved context supplies one.
- Every prepared HTML file passes the deterministic shared `strong-to-b` engine.
- External writes require explicit approval for the current bundle hash.
- Completion requires WordPress readback and, only when configured, tracker readback.

For a bulk request, also read `../../workflows/wp-publish/references/batch-approval.md`. Prepare and
gate every job, show one exact batch manifest/hash, and ask once; each job still executes and verifies
independently.

For a new project, scaffold first, run the read-only site scan, and ask the user to confirm the first
content-type profile before enabling it. Credentials stay in one ignored root `CLAUDE.local.md`; do
not copy secrets into project folders, jobs, logs or Git.
