# Project content storage

Create one folder per WordPress item under its content type:

```text
content/<blog|service-page|product>/<slug>/
├── assets/
│   ├── original/<run-id>/  # supplied/downloaded originals for this run
│   └── prepared/<run-id>/  # optimized/renamed derivatives for this run
├── backups/                # immutable pre-update WordPress snapshots
└── runs/<run-id>/
    ├── intake/             # locked editorial content snapshot + assets.json
    ├── snapshot/           # fresh WordPress raw HTML + metadata (AUDIT)
    ├── work/               # Doc ZIP, image mapping, candidate HTML, diffs
    └── bundle/             # prepared HTML, approval, run state and readback
```

Create a run with `workflows/wp-publish/scripts/wp_scaffold_item.py` after project setup. Use a new
`run-id` for each publication attempt; resume the same run only for the same job. Do not overwrite a
past run. Source content may originate elsewhere, but `intake/` preserves its locked copy. Image
preparation reads originals and writes only under `assets/prepared/<run-id>/`. Existing WordPress
images kept by URL need no local download; downloaded images and new supplied files go in
`assets/original/<run-id>/`. The bundle holds the current run's approval and state; `backups/` holds
the pre-update WordPress body independently of the run.
