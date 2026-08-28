# WP REST — ghi chú kỹ thuật

## Endpoint cốt lõi

| Việc | Call |
|---|---|
| Tìm bài theo slug + lấy raw | `GET /wp-json/wp/v2/posts?slug=<slug>&context=edit&_fields=id,content,modified` |
| Lấy 1 bài theo id | `GET /wp-json/wp/v2/posts/<id>?context=edit&_fields=id,content,modified,link` |
| Cập nhật nội dung | `POST /wp-json/wp/v2/posts/<id>` body `{"content": "<html>"}` |
| Page (không phải post) | thay `posts` bằng `pages` |

`context=edit` BẮT BUỘC để lấy `content.raw` (bản HTML nguồn) và cần auth. Không có `context=edit`
thì chỉ nhận `content.rendered` (đã qua wpautop + shortcode expand — KHÔNG dùng để sửa).

## Auth

Basic Auth = base64(`user:app_password`). App Password có dấu cách trong chuỗi — **giữ nguyên dấu cách**.
HTTP 401 = sai user/password hoặc site tắt Application Passwords. HTTP 403 = user không đủ quyền sửa
bài đó. Mặc định tạo user riêng role Editor; không dùng Administrator. Editor có `upload_files`,
`edit_others_posts` và `edit_published_posts`, đủ cho NEW draft + AUDIT bài hiện có. HTTP 200 ở
`context=edit` = auth OK.

Chạy `workflows/wp-publish/scripts/wp_setup_credentials.py` để nhập password qua prompt ẩn, kiểm role
và capability rồi lưu file local mode `0600`.

## `modified`, revision, `date`

- POST update KHÔNG kèm `date` → WordPress tự set `modified` = now. Đây là **freshness signal** tốt,
  thường muốn giữ. Nếu cần giữ nguyên modified cũ (hiếm) thì gửi `date`/`modified` tường minh.
- Mỗi POST update tạo 1 **revision**. Hoàn tác: WP-admin → mở bài → panel Revisions → chọn bản trước
  → Restore. Đây là lý do update NỘI DUNG an toàn hơn nhiều so với sửa theme/plugin (không revision).

## Classic Editor (đa số site cũ)

- `content.raw` = HTML thuần, đoạn cách nhau bằng dòng trống (KHÔNG có `<p>` — wpautop thêm khi render).
  → Khi chèn đoạn mới, dùng `\n\n` phân tách, **đừng** tự bọc `<p>`.
- Ảnh = shortcode `[caption id="attachment_123" align="aligncenter" width="800"]<img .../> Caption text[/caption]`.
  Alt nằm trong `<img alt="...">`; caption là text sau `/>` trước `[/caption]`. Sửa caption thì match
  đoạn sau `/>` cho khỏi đụng alt.
- Bold: nhiều site dùng `<b>` cho câu trả lời L0 và `<strong>` cho heading (`<h2><strong>...`) + link
  (`<a><strong>...`). Bám đúng convention hiện có; đừng chạy strong-to-b blanket (đổi tag ngoài phạm vi).

## Gutenberg (block editor)

- `content.raw` chứa block comment: `<!-- wp:paragraph -->\n<p>...</p>\n<!-- /wp:paragraph -->`.
- Sửa TEXT bên trong `<p>...</p>` / `<li>` thì an toàn. **Tuyệt đối không phá** cặp comment
  `<!-- wp:... -->` … `<!-- /wp:... -->` (hỏng = block vỡ, editor báo lỗi recovery).
- Thêm đoạn mới phải thêm cả block wrapper: `<!-- wp:paragraph -->\n<p>câu mới</p>\n<!-- /wp:paragraph -->`.
- Bảng = `<!-- wp:table -->`; ảnh = `<!-- wp:image -->`. Đừng string-replace cắt ngang các khối này.
- `detect_format()` trong `wp_lib.py` phân biệt bằng sự hiện diện của `<!-- wp:`.

## Ảnh / media

- REST content chỉ tham chiếu URL ảnh; **không upload file** qua endpoint này. Ảnh mới: operator up qua
  Media Library (hoặc `POST /wp/v2/media`) rồi mới nhúng URL. Thường tách khỏi đợt push text.
- Swap ảnh giữ nguyên URL/filename = chỉ cần up đè trong Media (giữ tên) — content không đổi. Nếu đổi
  filename thì phải sửa cả `src`/`alt`/`caption` trong content (thành 1 edit trong edits.json).

## Bẫy thường gặp

- Chuỗi `old` copy từ trình soạn có smart-quote (`’` `“` `”`) khác thẳng (`'` `"`) → count=0. Luôn lấy
  `old` từ `.raw.html` thật, không gõ tay.
- `&amp;` `&nbsp;` `&sup2;` trong raw: match theo đúng entity như trong raw.
- Payload có ký tự unicode → gửi JSON UTF-8 (script đã lo). Không cần escape thủ công.
- CDN/cache (LiteSpeed, Cloudflare): verify live có thể trễ vài giây–phút. Dùng cache-bust query; nếu
  vẫn thấy bản cũ, chờ rồi `--verify-only`.
