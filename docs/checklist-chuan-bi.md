# Checklist chuẩn bị WP Publish

## Người và quyền

- [ ] Có operator chịu trách nhiệm duyệt bundle/hash.
- [ ] Có WordPress user riêng cho REST, mặc định role Editor; không dùng Administrator.
- [ ] Có quyền đọc/ghi đúng Google Sheet tab.
- [ ] Có quyền đọc Google Doc hoặc file Markdown nguồn.

## Website

- [ ] Domain và `site_key` đúng.
- [ ] Application Password đã được script kiểm tra và lưu vào `CLAUDE.local.md` mode `0600`.
- [ ] File content có đúng một H1; `body_h1_count` đã chốt (0 nếu theme in tiêu đề bài thành H1, 1 nếu body giữ H1).
- [ ] `seo_meta_adapter` là `yoast` hoặc `rankmath` và đã test REST.
- [ ] Category/tag/author mặc định đã chốt hoặc có input.
- [ ] Media upload, reuse và readback đã test.

## Project local

- [ ] `projects/<client>/context.md` có brand fact thật.
- [ ] `publish-context.md` ghi quyết định vận hành.
- [ ] `publish-context.json` có Sheet ID/tab/timezone.
- [ ] `ready=false` trong lúc setup.

## Pilot

- [ ] Dùng nội dung test không chứa dữ liệu khách hàng.
- [ ] Route `NEW`, slug chưa tồn tại.
- [ ] Dừng ở `Chờ xác nhận` trước write.
- [ ] Tạo đúng một WordPress draft.
- [ ] WP readback và Sheet readback đều đạt.
- [ ] Rerun không tạo trùng post/media.
- [ ] Sau pilot mới bật `ready=true`.
