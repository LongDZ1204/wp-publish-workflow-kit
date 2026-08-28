# Google Sheet template

Use one client-specific tab with these columns:

| Column | Entered by | Purpose |
|---|---|---|
| `Row ID` | workflow | Immutable key; hide the column if preferred |
| `Bài / Title` | operator | WordPress title |
| `Loại bài` | operator | Dropdown: `AUDIT`, `NEW` |
| `Nguồn content` | operator | Google Doc URL/ID or local Markdown path |
| `Slug / URL WP` | operator | NEW: exact slug; AUDIT: exact current URL |
| `Meta description` | operator | Meta description requested for the post |
| `Ngày public dự kiến` | operator | Planning date, not actual publication time |
| `Trạng thái` | workflow | Five-state dropdown below |
| `URL draft/live` | workflow | Draft editor URL for NEW or verified live URL for AUDIT |
| `Note` | both | Current error/action detail; error code first |
| `Cập nhật lúc` | workflow | Last workflow write timestamp |

Status dropdown:

- `Chờ chạy`: input is ready; workflow has not run.
- `Chờ xác nhận`: bundle passed gates; approval is required before a WordPress write.
- `Chờ đăng`: NEW draft was created and verified; a human must publish it.
- `Hoàn tất`: NEW is live or AUDIT was updated, with readback verified.
- `Cần xử lý`: workflow stopped; the current reason is in `Note`.

Use strict dropdown validation. Do not expose technical run state, approval files, post IDs or source
revisions as separate Sheet columns; those belong in the local bundle.

A CSV header starter is available at `templates/sheet-template.csv`.
