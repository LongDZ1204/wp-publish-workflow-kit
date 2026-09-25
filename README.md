# WP Publish Workflow Kit

A portable, approval-bound workflow for preparing and publishing content to WordPress. The core job
does not depend on Google Sheets: Markdown, HTML and exported Google Doc snapshots enter the same
contract, while Google Sheets can be enabled later as an optional tracking adapter.

It supports two routes:

- `NEW`: prepare assets and HTML, bind approval to a content hash, then create exactly one draft.
- `AUDIT`: snapshot and back up one existing item, apply an explicitly approved `MINIMAL_DIFF`
  or `REBUILD`, then read back the unchanged post ID and inspect the rendered page.

The workflow keeps credentials global and gitignored, but separates each project's context, content,
images, scans and run data. Blog, service-page and product profiles are confirmed independently.

## Repository layout

```text
.codex-plugin/plugin.json       Codex plugin manifest
skills/wp-publish/              Public workflow entrypoint
skills/wp-publish-new/          NEW draft executor
skills/wp-rest-publish/         Existing-content executor
skills/image-onpage/            Shared image preparation skill
skills/strong-to-b/             Shared strong-to-b skill
tools/strong-to-b/              Deterministic HTML engine
workflows/wp-publish/           Contracts, discovery, state machine and tests
templates/project-skeleton/     Visible per-client folder template
templates/wp-publish.env.example Credential format without secrets
docs/                           Setup and optional Sheet documentation
```

## Requirements

- Python 3.10+
- A dedicated WordPress account with the exact capabilities reported by the read-only scan
- An Application Password stored only in the root `.env.wp-publish` with file mode `0600`
- Content plus any referenced images; the initial adapters are Markdown, HTML and Google Doc export
- `Pillow`, `certifi`, and `beautifulsoup4`; `pytest` for development tests

For an existing article, follow [the AUDIT publishing flow](docs/audit-publish-flow.md). The
editorial audit decides the mode and content; this kit controls the WordPress update.

## Quick start

Open Codex in your working folder and send:

```text
Hãy cài WP Publish Workflow Kit từ:
https://github.com/LongDZ1204/wp-publish-workflow-kit

Setup project cho [website/domain]. Chỉ scaffold và chạy site scan read-only; chưa ghi WordPress.
Credential dùng user riêng, lưu trong .env.wp-publish và không nhận password qua chat.
Sau scan, chỉ xác nhận context chung. Khi tôi yêu cầu loại nội dung nào, hãy xác nhận profile loại đó
ngay lúc cần, chạy một draft pilot, rồi chỉ bật batch sau REST readback và rendered QA đạt.
Google Sheet để type=none nếu tôi chưa dùng.
Kết thúc bằng READY FOR PILOT hoặc danh sách chính xác phần còn thiếu.
```

Setup copies the visible `templates/project-skeleton/` to `projects/<client>/`, then the read-only
scan writes a proposed profile under `projects/<client>/scans/`. Runtime projects are gitignored so
client content and evidence are never packaged by accident. Content profiles stay unconfirmed until
requested; each becomes batch-ready only after its own verified pilot. See
[the beginner guide](docs/huong-dan-nguoi-moi.md) and
[the maintainer setup](docs/setup.md).

## Optional Google Sheet tracking

Publishing works with `tracker.type=none`. To add a Sheet later, follow
[docs/google-sheet-template.md](docs/google-sheet-template.md); every Sheet row is converted to the
same v2 job contract and read back by immutable `Row ID`.

## Test

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 -m unittest discover -s workflows/wp-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-publish-new/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-rest-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
python3 -m pytest tools/strong-to-b/test_strong_to_b.py -q
python3 scripts/check_distribution.py
```

## Security

Never commit credentials, Google tokens, project bundles, source snapshots, uploaded media or
client-specific IDs. See [SECURITY.md](SECURITY.md).

This repository is distributed under the MIT License. See [LICENSE](LICENSE).
