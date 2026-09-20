# Hướng dẫn cài WP Publish cho người mới

WP Publish giúp lấy bài từ Google Doc hoặc file Markdown, chuẩn bị ảnh và đưa bài lên WordPress.
Bài mới luôn được tạo ở trạng thái **Nháp** để bạn kiểm tra trước. Bài audit chỉ cập nhật đúng bài đã
có và luôn tạo bản backup trước khi sửa.

Bạn không cần tự gõ lệnh. Cách dễ nhất là gửi link GitHub cho Codex hoặc một AI có thể thao tác trên
máy, rồi để AI cài và kiểm tra từng bước. Riêng bước lưu Application Password (Bước 3) bạn tự mở file
và dán theo template — không cần lệnh, không cần AI.

## Cách nhanh nhất: nhờ AI cài

Mở Codex tại folder làm việc của bạn và gửi nguyên prompt này:

```text
Hãy cài WP Publish Workflow Kit từ:
https://github.com/LongDZ1204/wp-publish-workflow-kit

Hãy setup project cho website [điền tên website/domain].
Chỉ cài và chạy kiểm tra read-only, chưa tạo hoặc cập nhật bài trên WordPress.
Hỏi tôi lần lượt từng thông tin còn thiếu, mỗi lần giải thích ngắn cách lấy.
File content luôn có đúng 1 H1. Khi setup, hỏi tôi theme site có in tiêu đề bài thành H1 không để chốt `body_h1_count` (0 hoặc 1).
Application Password tôi tự dán vào CLAUDE.local.md theo template ở Bước 3; bạn không nhận password qua chat.
Khi hoàn tất, báo rõ READY FOR PILOT hoặc danh sách phần còn thiếu.
```

`Read-only` nghĩa là chỉ đọc và kiểm tra kết nối, chưa ghi gì lên website. AI cần dừng trước mọi thao
tác tạo hoặc cập nhật bài để xin bạn xác nhận.

## Bạn cần chuẩn bị 5 thứ

1. URL website, ví dụ `https://example.com`.
2. Một WordPress user riêng có role Editor và một Application Password.
3. Link Google Sheet cùng tên tab quản lý bài.
4. Link Google Doc hoặc file Markdown chứa nội dung.
5. Tên plugin SEO đang dùng: **Yoast SEO** hoặc **Rank Math**.

Không cần chuẩn bị bản content riêng trong folder workflow. Google Doc hoặc Markdown là nguồn chính;
AI sẽ kéo nội dung về khi chạy.

## Bước 1 — Tạo WordPress user đúng quyền

Nên tạo một user riêng cho workflow:

- Username gợi ý: `wp-publish`.
- Role: **Editor**.
- Không dùng tài khoản Administrator đang quản trị website.

Editor là lựa chọn mặc định vì workflow cần upload ảnh, tạo bài Nháp, cập nhật bài đã public và có thể
cập nhật bài do user khác tạo. Author chỉ quản lý bài của chính họ; Contributor không upload được ảnh.
Administrator có quyền cài plugin, sửa theme và quản lý user nên rộng hơn mức workflow cần.

Cách tạo:

1. Đăng nhập WordPress bằng tài khoản quản trị.
2. Vào **Users → Add New**.
3. Nhập username, email và tạo mật khẩu đăng nhập mạnh.
4. Tại **Role**, chọn **Editor**.
5. Bấm **Add New User**.

Tài liệu gốc: [WordPress Roles and Capabilities](https://wordpress.org/documentation/article/roles-and-capabilities/).

## Bước 2 — Tạo WordPress Application Password

`Application Password` là mật khẩu riêng để công cụ kết nối WordPress qua REST API. `REST API` là
cổng cho phép phần mềm đọc hoặc cập nhật dữ liệu WordPress; mật khẩu này có thể thu hồi riêng và không
làm đổi mật khẩu đăng nhập chính.

Làm lần lượt:

1. Đăng nhập WordPress Admin.
2. Vào **Users → All Users** rồi mở user Editor vừa tạo. Nếu đang đăng nhập bằng chính user đó, vào
   **Users → Profile**.
3. Kéo xuống phần **Application Passwords**.
4. Nhập tên dễ nhớ, ví dụ `WP Publish Workflow`.
5. Bấm **Add New Application Password** hoặc **Generate**.
6. Copy mật khẩu ngay. WordPress chỉ hiển thị đầy đủ một lần.
7. Giữ mật khẩu trong clipboard và chuyển sang bước lưu bên dưới.

## Bước 3 — Tự dán Application Password vào file bảo mật (không cần AI)

Credential chỉ là một khối văn bản trong file `CLAUDE.local.md` ở thư mục gốc kit — file này đã bị
`.gitignore` chặn nên không bao giờ lên Git. Bạn tự làm, không cần AI hay lệnh nào:

1. Mở `templates/CLAUDE.local.example.md`, copy toàn bộ nội dung thành file mới `CLAUDE.local.md`
   ở thư mục gốc kit (Notepad hoặc TextEdit đều mở được).
2. Điền giá trị thật vào khối mẫu:

   ```markdown
   ### ten-ngan WordPress (REST API)
   - URL: https://domain.com
   - User: wp-publish
   - App Password: xxxx xxxx xxxx xxxx xxxx xxxx
   ```

   - `ten-ngan`: tên ngắn bạn đặt cho site (dùng lại ở các bước sau).
   - App Password dán nguyên xi như WordPress cấp, kể cả các dấu cách.
3. Lưu file. Xong — mọi script của kit tự đọc file này, password không bao giờ nằm trên dòng lệnh.

Nếu thư mục đã có sẵn `CLAUDE.local.md` (site trước đó đã làm): KHÔNG ghi đè file — chỉ thêm
một khối mẫu vào cuối file rồi điền giá trị site mới. Dùng nhiều site thì mỗi site một khối
trong cùng file, script tự chọn khối theo tên site hoặc domain. Muốn thêm vòng kiểm tra tự động
(đăng nhập + role, chặn Administrator) thì chạy
`python3 workflows/wp-publish/scripts/wp_setup_credentials.py --site-key ten-ngan --url https://domain.com --user wp-publish`
— không bắt buộc.

Không dán mật khẩu vào chat, Google Sheet, Google Doc hay file nào khác.

Nếu Bước 7 (preflight) báo lỗi đăng nhập, mở lại file kiểm ba thứ: URL đúng chưa, user đúng chưa,
App Password copy đủ chưa (WordPress chỉ hiện password một lần — thiếu thì tạo password mới).

## Bước 4 — Chọn Yoast SEO hoặc Rank Math

Bạn chỉ cần trả lời AI một trong hai giá trị:

- `yoast` nếu website dùng Yoast SEO;
- `rankmath` nếu website dùng Rank Math.

Yoast và Rank Math không có mật khẩu REST riêng. Workflow vẫn dùng Application Password của WordPress.
Điểm cần kiểm tra là website có cho phép ghi SEO title và meta description qua REST hay chưa.

Hãy gửi AI prompt này:

```text
Website dùng [Yoast SEO/Rank Math]. Hãy kiểm tra read-only xem SEO title và meta description
có thể đọc/ghi qua WordPress REST chưa. Chưa được sửa bài thật.
```

Nếu AI báo SEO meta chưa mở qua REST, làm theo một trong hai cách:

1. Khuyến nghị: nhờ AI cài đúng snippet trong repository.
2. Hoặc nhờ quản trị viên website cài thủ công bằng WPCode/Code Snippets.

Prompt cho AI:

```text
Hãy cài snippet REST phù hợp với plugin SEO của website từ folder snippets/ trong repository.
Dùng staging nếu có, backup trước, không chạm vào bài viết. Sau khi bật snippet, kiểm tra lại
quyền đọc/ghi SEO meta và báo kết quả.
```

File đúng cho từng plugin:

- Yoast SEO: `snippets/yoast-seo-rest-meta.php`.
- Rank Math: `snippets/rank-math-rest-meta.php`.

Nếu quản trị viên cài bằng WPCode:

1. Vào **Code Snippets → Add Snippet**.
2. Chọn loại **PHP Snippet**.
3. Copy nội dung file đúng với plugin SEO đang dùng.
4. Đặt tên `WP Publish SEO REST Meta`.
5. Chọn chạy toàn website và bật snippet.
6. Nhờ AI chạy lại kiểm tra read-only.

Snippet chỉ mở hai trường SEO cho user đã có quyền sửa bài; nó không chứa và không cần Application
Password. WordPress yêu cầu post meta được đăng ký với `show_in_rest` thì mới đọc/ghi được qua REST.
Xem [WordPress REST meta guide](https://developer.wordpress.org/rest-api/extending-the-rest-api/modifying-responses/#read-and-write-a-post-meta-field-in-post-responses)
và [Yoast REST API](https://developer.yoast.com/customization/apis/rest-api/).

## Bước 5 — Chuẩn bị Google Sheet

Dùng 11 cột trong [Google Sheet template](google-sheet-template.md). Bạn chỉ cần nhập các cột nội dung;
workflow tự cập nhật các cột theo dõi.

Hai dropdown cần có sẵn:

- `Loại bài`: `NEW`, `AUDIT`.
- `Trạng thái`: `Chờ chạy`, `Chờ xác nhận`, `Chờ đăng`, `Hoàn tất`, `Cần xử lý`.

Ý nghĩa ngắn:

| Trạng thái | Nghĩa là gì |
|---|---|
| `Chờ chạy` | Dòng đã đủ thông tin và chưa chạy |
| `Chờ xác nhận` | AI đã chuẩn bị xong, đang chờ bạn duyệt |
| `Chờ đăng` | Bài NEW đã lên WordPress ở dạng Nháp |
| `Hoàn tất` | Bài đã đăng hoặc bài AUDIT đã cập nhật và kiểm tra xong |
| `Cần xử lý` | Workflow dừng; xem lý do trong cột `Note` |

## Bước 6 — Chuẩn bị file content có H1

Mỗi file content phải có **đúng một H1**:

- Google Doc: đặt tiêu đề bài bằng style **Heading 1**.
- Markdown: dùng một dòng bắt đầu bằng `# `.
- HTML: dùng đúng một cặp `<h1>...</h1>`.

Không dùng thêm H1 thứ hai ở phần thân bài. Các phần lớn tiếp theo dùng H2, rồi H3 nếu cần.

Một trang WordPress chỉ nên có đúng một H1, và H1 đó có thể do theme in ra từ tiêu đề bài. Vì vậy cần
chốt `body_h1_count` trong `publish-context.json`:

- `0`: theme đã render tiêu đề bài thành H1 của trang (phần lớn theme chuẩn) → body KHÔNG chứa H1,
  các đề mục bắt đầu bằng H2.
- `1`: theme không in H1 (một số theme/page builder) → body giữ đúng một H1 từ file content.

Cách kiểm: mở một bài đã có trên site, xem nguồn trang (Ctrl+U) — nếu tiêu đề bài nằm trong `<h1>`
thì chọn `0`, ngược lại chọn `1`. Gate sẽ dừng nếu số H1 trong body khác con số đã khai báo.

## Bước 7 — Nhờ AI chạy kiểm tra trước khi demo

Gửi prompt:

```text
Chạy preflight WP Publish cho project [tên project].
Chỉ kiểm tra: project context, Google Sheet/tab, WordPress REST, quyền post/media,
H1 trong content, `body_h1_count` đã chốt và SEO meta của [yoast/rankmath]. Chưa tạo hoặc cập nhật bài.
```

`Preflight` là vòng kiểm tra trước khi chạy thật. Kết quả cần là `READY FOR PILOT`. Nếu còn thiếu, AI
phải nêu đúng phần thiếu và hướng dẫn bạn lấy hoặc sửa phần đó.

## Bước 8 — Chạy demo NEW an toàn

Tạo một dòng test trên Sheet:

| Cột | Giá trị mẫu |
|---|---|
| `Bài / Title` | WP Publish Integration Test |
| `Loại bài` | NEW |
| `Nguồn content` | Link Google Doc test có đúng 1 H1 |
| `Slug / URL WP` | wp-publish-integration-test |
| `Meta description` | Nội dung kiểm tra workflow |
| `Trạng thái` | Chờ chạy |

Đầu tiên chỉ chuẩn bị và dừng để duyệt:

```text
Chạy WP Publish cho Row ID [row-id] theo route NEW.
Chỉ chuẩn bị bundle và dừng ở Chờ xác nhận; chưa ghi WordPress.
```

Sau khi bạn kiểm tra title, H1, nội dung, ảnh và meta, AI sẽ đưa một `approval hash`. Đây là mã xác
nhận đúng phiên bản bạn vừa duyệt; nội dung đổi thì mã cũng đổi.

Khi đồng ý tạo Nháp, trả lời:

```text
Tôi duyệt approval hash [mã]. Tạo WordPress draft, không public.
```

Kết quả đúng:

- WordPress có đúng một bài mới ở trạng thái Nháp;
- body có đúng `body_h1_count` H1 đã khai báo;
- SEO title và meta description đọc lại đúng;
- Sheet chuyển sang `Chờ đăng` và có URL draft;
- chạy lại không tạo bài hoặc ảnh trùng.

## Khi nào dùng AUDIT?

Chỉ dùng `AUDIT` khi bài đã tồn tại trên WordPress. Workflow phải kéo HTML hiện tại, tạo backup, trình
phần thay đổi và chờ bạn duyệt trước khi cập nhật.

## Quy tắc an toàn cần nhớ

1. NEW luôn tạo Nháp, không tự public.
2. AUDIT luôn backup trước khi sửa.
3. File content luôn có đúng một H1; body giữ đúng `body_h1_count` H1 đã khai báo.
4. Không gửi mật khẩu vào Sheet, Doc hoặc GitHub.
5. AI phải dừng xin duyệt trước khi ghi WordPress.
6. Chỉ gọi là hoàn tất sau khi đọc lại WordPress và Sheet đều khớp.

Phần cài thủ công dành cho người kỹ thuật nằm ở [setup.md](setup.md). Checklist ngắn nằm ở
[checklist-chuan-bi.md](checklist-chuan-bi.md).
