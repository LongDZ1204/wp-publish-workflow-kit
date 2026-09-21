# Intake contract

`wp_intake.py` snapshots a readable content file and an optional image inventory without changing
either. It writes:

```text
intake/
├── content.snapshot.md|html
├── assets.json
└── intake.json
```

`intake.json` records adapter, original reference/revision, media type, SHA-256 values, asset count
and lock time. Google Docs must first be exported to HTML or Markdown by an available connector; the
export is then treated as the immutable source snapshot.

`assets.json` uses `{"version":1,"images":[]}`. Each referenced image must later receive a stable
asset ID and pass `image-onpage`. Alt text is required unless decorative. Caption is optional and is
not generated solely to fill an empty field.
