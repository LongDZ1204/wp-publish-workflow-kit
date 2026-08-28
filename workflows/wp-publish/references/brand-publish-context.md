# Brand và publish context

Workflow load hai lớp:

1. `projects/<client>/context.md`: brand, voice, language, market, spelling, keyword/entity.
2. `projects/<client>/knowledge/publish-context.md`: technical publishing policy.

`publish-context.md` tối thiểu cần:

- `site_key` và `rest_base`.
- Source content luôn có đúng một H1; workflow giữ H1 đó trong body WordPress.
- image `format_policy`, `max_kb`, `max_width`, existing-media policy.
- default category/tag/author nếu được operator chốt; không có thì Sheet phải cung cấp.
- `spreadsheet_id`, Sheet tab/range và timezone.
- `ready=false` cho đến khi REST, Sheet và media round-trip đã được verify.
- `pilot_allowed=true` chỉ cho một pilot NEW draft-only có phê duyệt rõ ràng.
- `seo_meta_adapter` là `yoast` hoặc `rankmath`; REST capability đã được test.

Không copy full brand context vào Sheet. Không tự điền TODO bằng suy đoán.
