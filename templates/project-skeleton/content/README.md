# Project content storage

Create one folder per WordPress item under its content type:

```text
content/<blog|service-page|product>/<slug>/
├── intake/                 # locked content snapshot + assets.json
├── assets/
│   ├── original/           # immutable supplied images
│   └── prepared/           # optimized/renamed derivatives
├── bundle/                 # prepared HTML, manifests, gates and approval
├── backups/                # immutable pre-update WordPress snapshots
└── runs/                   # per-run state and readback evidence
```

Do not mix items or content types. Source content and images may come from anywhere, but the locked
snapshot and all publishing evidence belong to this item folder.
