# Checklist chuẩn bị WP Publish

## Người và quyền

- [ ] Có operator chịu trách nhiệm duyệt bundle/hash.
- [ ] Có WordPress user riêng cho REST, mặc định role Editor; không dùng Administrator.
- [ ] Nếu dùng tracker: có quyền đọc/ghi đúng Google Sheet tab.
- [ ] Có quyền đọc Google Doc hoặc file Markdown/HTML nguồn và ảnh đi kèm.

## Website

- [ ] Domain và `site_key` đúng.
- [ ] User đã điền `projects/<client>/wp-credentials.env`; agent đặt quyền `0600` và xác nhận
  WordPress `users/me` trả HTTP 200 trước khi coi kết nối là hợp lệ.
- [ ] Đã chạy site scan read-only; không dùng Administrator chỉ để vượt setup.
- [ ] Chỉ content type user đang yêu cầu được xác nhận endpoint, field, H1 ownership và HTML policy.
- [ ] `seo_meta_adapter` là `yoast` hoặc `rankmath` và đã test REST.
- [ ] Category/tag/author mặc định đã chốt hoặc có input.
- [ ] Media upload, reuse và readback đã test.

## Project local

- [ ] `projects/<client>/context.md` có brand fact thật.
- [ ] `publish-context.md` ghi quyết định vận hành.
- [ ] `publish-context.json` có profile riêng cho blog/service-page/product.
- [ ] `tracker.type=none` nếu chưa dùng Sheet.
- [ ] Profile chưa được yêu cầu giữ `status=unconfirmed`.
- [ ] Profile đã xác nhận nhưng chưa qua pilot giữ `status=pilot-ready`, `ready=false`.

## Pilot

- [ ] Dùng nội dung test không chứa dữ liệu khách hàng.
- [ ] Route `NEW`, slug chưa tồn tại.
- [ ] Dừng ở `Chờ xác nhận` trước write.
- [ ] Tạo đúng một WordPress draft.
- [ ] WP readback và tracker readback (nếu bật) đều đạt.
- [ ] Rendered QA đạt cho content, ảnh, heading, link và SEO metadata.
- [ ] Rerun không tạo trùng post/media.
- [ ] Sau pilot + rendered QA mới certify đúng loại bài thành `batch-ready`.
- [ ] Batch manifest bị chặn nếu có loại bài chưa `batch-ready`.

## AUDIT bài đã có

- [ ] Quyết định editorial đã chốt `MINIMAL_DIFF` hoặc `REBUILD` cho đúng post ID/URL.
- [ ] Có snapshot `content.raw` mới và backup có tên riêng, hash khớp metadata.
- [ ] `audit-plan.json` ghi đúng chênh lệch cấu trúc, passage giữ nguyên, ảnh và cặp link/anchor được duyệt bỏ.
- [ ] Gate HTML/ảnh và audit đều đạt trước khi trình hash duyệt.
- [ ] Lệnh ghi `wp_push_audit.py` đã dry-run; post vẫn khớp `modified` và raw hash trước khi ghi.
- [ ] REST readback khớp, rồi kiểm trang render desktop/mobile và schema nếu nội dung có ảnh hưởng.
