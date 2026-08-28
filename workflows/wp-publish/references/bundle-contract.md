# Publish bundle contract

Mỗi bài có đúng một bundle hiện hành:

```text
projects/<client>/content/07-publish-ready/<slug>/
├── source-lock.json
├── source.snapshot.md       # chỉ bắt buộc với nguồn external mutable như Google Doc
├── publish-request.json
├── content.prepared.html
├── image-manifest.json
├── transform-report.json
├── run-state.json
├── gate-report.json
└── approval.json            # chỉ sinh sau xác nhận rõ của operator
```

## Quy tắc

- Google Doc là canonical input nhưng **không push trực tiếp**; snapshot khóa bản được duyệt.
- Markdown local không bị copy; lock lưu absolute/relative path + SHA-256.
- Ảnh nằm ở `content/06-assets/`, bundle chỉ giữ mapping.
- Trước approval có thể refresh bundle tại chỗ; không tạo chuỗi `v1/v2/v3`.
- Sau approval, thay đổi bất kỳ input nào làm approval invalid.
- Không lưu ZIP export sau khi đã tạo snapshot + lấy ảnh.

## `publish-request.json`

Required chung: `row_id`, `run_id`, `client`, `site_key`, `task_type`, `source_type`, `source_ref`,
`title`.

- NEW required thêm: `slug`; optional `category_ids`, `tag_ids`, `featured_asset_id`.
- AUDIT required thêm: `target_url` hoặc `post_id`, `update_mode` (`MINIMAL_DIFF|REBUILD`).

## Approval hash

SHA-256 được tính trên bytes và tên của bốn file:

1. `publish-request.json`
2. `content.prepared.html`
3. `image-manifest.json`
4. `transform-report.json`

Không có đủ bốn file → không được approve.
