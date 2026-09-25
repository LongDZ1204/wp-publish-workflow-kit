# Publish bundle contract

Each job has one current inspectable bundle inside its project/content-type item folder:

```text
bundle/
├── source-lock.json
├── publish-request.json
├── content.prepared.html
├── image-manifest.json
├── transform-report.json
├── run-state.json
├── gate-report.json
├── audit-plan.json          # AUDIT only: selected mode and preservation/removal decisions
├── audit-gate-report.json   # AUDIT only: checked against the fresh raw backup
└── approval.json
```

`publish-request.json` follows the v2 job contract. `job_id` replaces mandatory `row_id`; legacy
Sheet requests remain readable. NEW needs a slug. AUDIT needs a target URL or post ID **and**
`update_mode=MINIMAL_DIFF|REBUILD`, merged from the approved editorial audit when the visible Sheet
does not contain it. The AUDIT lock copies post ID, status, modified time, raw SHA-256 and unique
backup path from a fresh `wp_fetch.py` metadata file into the approved request.

Approval SHA-256 binds the exact bytes and names of `publish-request.json`,
`content.prepared.html`, `image-manifest.json` and `transform-report.json`. Any change invalidates the
approval. AUDIT additionally binds `audit-plan.json` and `audit-gate-report.json`. Source files and
external exports are locked by hash before preparation; the AUDIT backup hash is checked again
before writing. See [audit-publish-flow.md](../../../docs/audit-publish-flow.md).
