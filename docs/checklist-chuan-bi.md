# Checklist chuẩn bị WP Publish

## Người và quyền

- [ ] Có operator chịu trách nhiệm duyệt bundle/hash.
- [ ] Có WordPress user riêng cho REST, mặc định role Editor; không dùng Administrator.
- [ ] Nếu dùng tracker: có quyền đọc/ghi đúng Google Sheet tab.
- [ ] Có quyền đọc Google Doc hoặc file Markdown/HTML nguồn và ảnh đi kèm.

## Website

- [ ] Domain và `site_key` đúng.
- [ ] Credential đã lưu đúng prefix site trong `.env.wp-publish`, quyền file `0600`.
- [ ] Đã chạy site scan read-only; không dùng Administrator chỉ để vượt setup.
- [ ] Content type đầu tiên đã xác nhận endpoint, field, H1 ownership và HTML policy.
- [ ] `seo_meta_adapter` là `yoast` hoặc `rankmath` và đã test REST.
- [ ] Category/tag/author mặc định đã chốt hoặc có input.
- [ ] Media upload, reuse và readback đã test.

## Project local

- [ ] `projects/<client>/context.md` có brand fact thật.
- [ ] `publish-context.md` ghi quyết định vận hành.
- [ ] `publish-context.json` có profile riêng cho blog/service-page/product.
- [ ] `tracker.type=none` nếu chưa dùng Sheet.
- [ ] Chỉ profile đã xác nhận mới có `ready=true`.

## Pilot

- [ ] Dùng nội dung test không chứa dữ liệu khách hàng.
- [ ] Route `NEW`, slug chưa tồn tại.
- [ ] Dừng ở `Chờ xác nhận` trước write.
- [ ] Tạo đúng một WordPress draft.
- [ ] WP readback và tracker readback (nếu bật) đều đạt.
- [ ] Rerun không tạo trùng post/media.
- [ ] Sau pilot mới bật `ready=true`.
