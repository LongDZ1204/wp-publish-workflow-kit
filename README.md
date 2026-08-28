# WP Publish Workflow Kit

A portable, approval-bound workflow for publishing content from Google Sheets/Docs to WordPress.

> Người mới: không cần tự cài bằng lệnh. Dùng prompt AI ở phần **Quick start**, sau đó làm theo
> **[hướng dẫn từng bước](docs/huong-dan-nguoi-moi.md)**.

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
snippets/                       Yoast/Rank Math REST meta adapters
templates/                      Safe starter files
docs/                           Setup and Sheet documentation
```

## Requirements

- Python 3.10+
- A dedicated WordPress Editor account with an Application Password; do not use Administrator
- Access to Google Sheets and the selected content source
- A source document containing exactly one H1; the workflow keeps that H1 in the WordPress body
- `Pillow`, `certifi`, and `beautifulsoup4`; `pytest` for development tests

## Quick start

Open Codex in your working folder and send this prompt. The AI should install dependencies, scaffold
the project and run read-only checks; it must not write to WordPress during setup.

```text
Hãy cài WP Publish Workflow Kit từ:
https://github.com/LongDZ1204/wp-publish-workflow-kit

Hãy setup project cho [website/domain]. Chỉ cài và chạy preflight read-only.
Chưa tạo hoặc cập nhật nội dung WordPress. Hỏi tôi từng thông tin còn thiếu, mỗi lần một mục.
Credential phải dùng user Editor riêng. Hãy chạy wp_setup_credentials.py trong terminal để tôi
nhập Application Password vào ô ẩn; không yêu cầu tôi gửi password qua chat.
Mỗi file content có đúng một H1; giữ H1 đó trong body WordPress.
Kết thúc bằng READY FOR PILOT hoặc danh sách phần còn thiếu.
```

The beginner guide shows how to create a WordPress Application Password, prepare the Sheet, enable
Yoast/Rank Math meta through REST and run a safe NEW draft pilot:
[`docs/huong-dan-nguoi-moi.md`](docs/huong-dan-nguoi-moi.md).

Manual commands for maintainers are in [`docs/setup.md`](docs/setup.md).

For team use, clone this repository into a shared workspace or reference it from a local Codex
marketplace. The `.codex-plugin/plugin.json` manifest exposes the skills; project data and credentials
remain outside Git through the supplied ignore rules.

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

## Contributing

Create a branch, keep client/runtime data outside Git, run the complete test block above, and open a
pull request with a short explanation of the workflow behaviour being changed.

This repository is distributed under the MIT License. See [`LICENSE`](LICENSE).

## Security

Never commit WordPress credentials, Google tokens, project bundles, source snapshots, uploaded media,
or client-specific Sheet/Doc IDs. See [`SECURITY.md`](SECURITY.md).
