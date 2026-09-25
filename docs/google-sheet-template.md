# Optional Google Sheet tracker template

Google Sheets is not required for publishing. Use this template only after setting the project
tracker to `google_sheet`; each row is normalized into the same v2 job contract used without Sheets.

The kit provides a row validator and a writeback/readback contract, not a built-in Google Sheets
network client. The running agent needs an authorized Sheets connector. Store the spreadsheet ID
and tab name in the project's `publish-context.json` tracker configuration, for example
`{"type":"google_sheet","spreadsheet_id":"...","tab_name":"Blog"}`. Connectors differ by runtime;
resolve the exact spreadsheet and tab before reading or writing rows. Never put credentials in the
Sheet or project JSON.

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

For NEW, creating a WordPress draft moves the row to `Chờ đăng`; it does not auto-publish on the
planned date. Move it to `Hoàn tất` only after a human publishes and the live page is checked.
For AUDIT, `Hoàn tất` requires the existing post to be updated, WordPress/render checks to pass,
and the Sheet writeback to be read back by `Row ID`.

A CSV header starter is available at `templates/sheet-template.csv`.
