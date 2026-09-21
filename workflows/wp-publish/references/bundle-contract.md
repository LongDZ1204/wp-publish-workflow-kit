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
└── approval.json
```

`publish-request.json` follows the v2 job contract. `job_id` replaces mandatory `row_id`; legacy
Sheet requests remain readable. NEW needs a slug and AUDIT needs a target URL or post ID.

Approval SHA-256 binds the exact bytes and names of `publish-request.json`,
`content.prepared.html`, `image-manifest.json` and `transform-report.json`. Any change invalidates the
approval. Source files and external exports are locked by hash before preparation.
