# WP Publish Workflow Kit

A portable, approval-bound workflow for publishing content from Google Sheets/Docs to WordPress.

> Người mới bắt đầu: đọc **[Hướng dẫn cài đặt và chạy pilot](docs/huong-dan-nguoi-moi.md)** và
> **[Checklist chuẩn bị](docs/checklist-chuan-bi.md)** trước khi kết nối website thật.

It supports two routes:

- `NEW`: prepare images and HTML, bind approval to a content hash, then create exactly one WordPress draft.
- `AUDIT`: fetch the current WordPress HTML, back it up, apply minimal edits, then update and verify the live post.

Both routes fail closed, run image checks, normalize `<strong>` deterministically, and require WordPress
plus Sheet readback before completion.

## Repository layout

```text
.codex-plugin/plugin.json       Codex plugin manifest
skills/wp-publish/              Public workflow entrypoint
skills/wp-publish-new/          NEW draft executor
skills/wp-rest-publish/         Existing-post AUDIT executor
skills/image-onpage/            Image inventory and preparation
skills/strong-to-b/             HTML normalization instructions
tools/strong-to-b/              Deterministic HTML engine
workflows/wp-publish/           State machine, contracts, scripts and tests
templates/                      Safe starter files
docs/                           Setup and Sheet documentation
```

## Requirements

- Python 3.10+
- A WordPress account with an Application Password
- Access to Google Sheets and the selected content source
- `Pillow` and `certifi`; `pytest` for development tests

```bash
python3 -m pip install -r requirements-dev.txt
```

## Quick start

Install the Codex plugin from this repository:

```bash
codex plugin marketplace add LongDZ1204/wp-publish-workflow-kit --ref main
codex plugin add wp-publish-workflow-kit@seo-cowork-tools
```

Restart Codex and use a new task after installation. For local project data, clone the repository:

```bash
git clone https://github.com/LongDZ1204/wp-publish-workflow-kit.git
cd wp-publish-workflow-kit
```

1. Copy `templates/context.example.md` to `projects/<client>/context.md` and fill only verified facts.
2. Scaffold the safe project folders:

   ```bash
   python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client <client>
   ```

3. Fill `projects/<client>/knowledge/publish-context.json` from
   `templates/publish-context.example.json`. Keep `ready=false` until REST, Sheet, meta and media
   round-trips have been tested.
4. Create the Sheet columns described in `docs/google-sheet-template.md`.
5. Provide credentials through environment variables or an ignored `CLAUDE.local.md` file.
6. Run the complete workflow through the `wp-publish` skill. Do not call write executors directly.

Detailed setup: [`docs/setup.md`](docs/setup.md).

For team use, clone this repository into a shared workspace or reference it from a local Codex
marketplace. The `.codex-plugin/plugin.json` manifest exposes the skills; project data and credentials
remain outside Git through the supplied ignore rules.

## Test

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 -m unittest discover -s workflows/wp-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-publish-new/tests -p 'test_*.py'
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
python3 -m pytest tools/strong-to-b/test_strong_to_b.py -q
python3 scripts/check_distribution.py
```

## Contributing

Create a branch, keep client/runtime data outside Git, run the complete test block above, and open a
pull request with a short explanation of the workflow behaviour being changed.

This repository is distributed under the MIT License. See [`LICENSE`](LICENSE).

## Security

Never commit WordPress credentials, Google tokens, project bundles, source snapshots, uploaded media,
or client-specific Sheet/Doc IDs. See [`SECURITY.md`](SECURITY.md).
