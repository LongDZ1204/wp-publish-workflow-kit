# Checklist chuẩn bị WP Publish

## Người và quyền

- [ ] Có operator chịu trách nhiệm duyệt bundle/hash.
- [ ] Có WordPress user riêng cho REST, quyền post/media vừa đủ.
- [ ] Có quyền đọc/ghi đúng Google Sheet tab.
- [ ] Có quyền đọc Google Doc hoặc file Markdown nguồn.

## Website

- [ ] Domain và `site_key` đúng.
- [ ] Application Password đã tạo và lưu ngoài Git.
- [ ] H1 ownership đã chốt.
- [ ] SEO meta adapter đã test.
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
