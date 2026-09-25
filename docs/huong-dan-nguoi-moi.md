# Hướng dẫn cài WP Publish cho người mới

WP Publish giúp lấy bài từ Google Doc, file Markdown hoặc HTML, chuẩn bị ảnh và đưa bài lên WordPress.
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
Sau khi kết nối, chạy site scan read-only và chỉ xác nhận context chung của project.
Khi tôi yêu cầu blog/service-page/product, chỉ hỏi profile của đúng loại đó ngay lúc cần.
Chạy một draft pilot; chỉ bật đăng hàng loạt cho loại đó sau REST readback và rendered QA đạt.
Google Sheet là tùy chọn; để tracker.type=none nếu tôi chưa dùng.
Application Password tôi tự lưu vào .env.wp-publish theo template ở Bước 3; bạn không nhận password qua chat.
Khi hoàn tất, báo rõ READY FOR PILOT hoặc danh sách phần còn thiếu.
```

`Read-only` nghĩa là chỉ đọc và kiểm tra kết nối, chưa ghi gì lên website. AI cần dừng trước mọi thao
tác tạo hoặc cập nhật bài để xin bạn xác nhận.

## Bạn cần chuẩn bị 4 thứ

1. URL website, ví dụ `https://example.com`.
2. Một WordPress user riêng có role Editor và một Application Password.
3. Link Google Doc, file Markdown hoặc file HTML chứa nội dung và các ảnh đi kèm.
4. Tên plugin SEO đang dùng: **Yoast SEO** hoặc **Rank Math**.

Google Sheet không bắt buộc. Bạn có thể bật sau nếu cần quản lý trạng thái hàng loạt.

## Yêu cầu về AI & Google

Workflow chạy bằng cách AI đọc/ghi giúp bạn:

- **Google Docs** chỉ cần connector khi dùng link Doc; bạn luôn có thể xuất Doc thành HTML/Markdown
  hoặc cung cấp file local.
- **Google Sheets** chỉ cần connector khi bạn bật tracker; không có Sheet vẫn chạy đầy đủ.
- **WordPress**: không cần cài thêm gì — script của kit gọi thẳng REST API bằng Application Password
  đã tạo ở Bước 2.

Mọi thứ khác (Python, thư viện) AI sẽ tự cài theo prompt quick-start.

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

## Bước 3 — Lưu Application Password vào file bảo mật

Credential nằm trong `.env.wp-publish` ở thư mục gốc kit. File đã bị `.gitignore` chặn, được đặt
quyền `0600` và được parser đọc trực tiếp — không chạy `source .env.wp-publish`.

Cách khuyến nghị là chạy script setup; password được nhập trong hộp thoại che nội dung:

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py \
  --site-key ten-ngan --url https://domain.com --user wp-publish --input-mode dialog
```

Nếu cần nhập tay, copy `templates/wp-publish.env.example` thành `.env.wp-publish`, rồi dùng prefix
site viết hoa, thay dấu gạch ngang bằng gạch dưới. Sau khi lưu, đặt quyền file bằng
`chmod 600 .env.wp-publish`:

```dotenv
# site: ten-ngan
WP_TEN_NGAN_URL="https://domain.com"
WP_TEN_NGAN_USER="wp-publish"
WP_TEN_NGAN_APP_PASS="xxxx xxxx xxxx xxxx xxxx xxxx"
```

Dùng nhiều site thì thêm ba biến với prefix khác trong cùng file. Nếu bản cũ đã có
`CLAUDE.local.md`, chạy lệnh dưới để migrate; lệnh giữ nguyên file cũ để bạn tự xóa sau khi kiểm tra:

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py --migrate-legacy
```

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

**Check báo OK là dừng ở đây** — nhiều site chạy Yoast/Rank Math bản mới đã mở sẵn hai trường này
qua REST, không cần cài gì thêm. Xác nhận chắc chắn nhất là lần ghi SEO meta đầu tiên khi tạo draft
pilot (Bước 8); rất hiếm khi cần can thiệp sau điểm đó.

Chỉ khi AI báo **chưa mở** qua REST mới cần cài một snippet nhỏ vào website. Lưu ý quan trọng:
workflow chỉ cầm user role **Editor** nên **AI không thể tự cài** (cài plugin/snippet cần quyền
Administrator — thứ workflow cố tình không dùng). Bạn hoặc quản trị viên website tự làm, khoảng 5 phút:

**Cách khuyến nghị — plugin WPCode / Code Snippets (không đụng code của theme):**

1. Đăng nhập wp-admin bằng tài khoản quản trị.
2. Vào **Code Snippets → Add Snippet** (chưa có plugin thì cài trước: Plugins → Add New → tìm
   "WPCode" → Install → Activate).
3. Chọn **Add Your Custom Code**, loại **PHP Snippet**.
4. Copy nguyên đoạn mã đúng plugin SEO của site (ở cuối bước này), dán vào, đặt tên
   `WP Publish SEO REST Meta`.
5. Chọn chạy toàn website (**Run everywhere**) rồi bật snippet, lưu.
6. Quay lại chat, nhờ AI chạy lại phép kiểm read-only ở trên cho tới khi báo OK.

**Cách khác — functions.php / mu-plugin** (nếu không muốn thêm plugin): nhờ quản trị viên dán đoạn
mã vào `functions.php` của child theme, hoặc lưu thành file trong `wp-content/mu-plugins/`.

Đoạn mã — chỉ cài ĐÚNG MỘT cái tương ứng plugin SEO đang dùng:

<details>
<summary><strong>Yoast SEO</strong> (bấm để mở — file gốc <code>snippets/yoast-seo-rest-meta.php</code>)</summary>

```php
<?php
/**
 * Allow authenticated editors to read and write the Yoast SEO title and
 * meta description through the standard WordPress REST API.
 *
 * Install only when Yoast SEO is the site's active SEO plugin.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function () {
		$keys = array( '_yoast_wpseo_title', '_yoast_wpseo_metadesc' );

		foreach ( array( 'post', 'page' ) as $post_type ) {
			foreach ( $keys as $key ) {
				register_post_meta(
					$post_type,
					$key,
					array(
						'type'              => 'string',
						'single'            => true,
						'show_in_rest'      => true,
						'sanitize_callback' => 'sanitize_text_field',
						'auth_callback'     => static function ( $allowed, $meta_key, $post_id ) {
							return current_user_can( 'edit_post', $post_id );
						},
					)
				);
			}
		}
	}
);
```
</details>

<details>
<summary><strong>Rank Math</strong> (bấm để mở — file gốc <code>snippets/rank-math-rest-meta.php</code>)</summary>

```php
<?php
/**
 * Allow authenticated editors to read and write the Rank Math SEO title and
 * meta description through the standard WordPress REST API.
 *
 * Install only when Rank Math is the site's active SEO plugin.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function () {
		$keys = array( 'rank_math_title', 'rank_math_description' );

		foreach ( array( 'post', 'page' ) as $post_type ) {
			foreach ( $keys as $key ) {
				register_post_meta(
					$post_type,
					$key,
					array(
						'type'              => 'string',
						'single'            => true,
						'show_in_rest'      => true,
						'sanitize_callback' => 'sanitize_text_field',
						'auth_callback'     => static function ( $allowed, $meta_key, $post_id ) {
							return current_user_can( 'edit_post', $post_id );
						},
					)
				);
			}
		}
	}
);
```
</details>

Snippet chỉ mở hai trường SEO cho user đã có quyền sửa bài; nó không chứa và không cần Application
Password. WordPress yêu cầu post meta được đăng ký với `show_in_rest` thì mới đọc/ghi được qua REST.
Xem [WordPress REST meta guide](https://developer.wordpress.org/rest-api/extending-the-rest-api/modifying-responses/#read-and-write-a-post-meta-field-in-post-responses)
và [Yoast REST API](https://developer.yoast.com/customization/apis/rest-api/).

## Bước 5 — Chuẩn bị Google Sheet (tùy chọn)

Nếu chưa cần Sheet, bỏ qua bước này và giữ `tracker.type=none`. Khi cần quản lý hàng loạt, dùng 11
cột trong [Google Sheet template](google-sheet-template.md). Agent cần connector Google Sheets có
quyền đọc/ghi; bộ kit chuẩn bị bản cập nhật và kiểm tra dòng sau khi connector ghi, không tự kết nối
Google Sheets chỉ bằng file CSV mẫu.

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

## Bước 6 — Chuẩn bị content và ảnh

Bạn có thể đưa Google Doc, Markdown hoặc HTML, miễn nội dung và ảnh đủ để chuẩn bị bài. Bản HTML cuối
cùng phải tuân theo H1 ownership đã xác nhận cho content type:

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
Chỉ kiểm tra: project context, WordPress REST, endpoint/field/quyền post-media,
H1 ownership, HTML policy, ảnh và SEO meta của [yoast/rankmath]. Nếu có tracker thì kiểm tra thêm
Google Sheet/tab. Chưa tạo hoặc cập nhật bài.
```

`Preflight` là vòng kiểm tra trước khi chạy thật. Kết quả cần là `READY FOR PILOT`. Nếu còn thiếu, AI
phải nêu đúng phần thiếu và hướng dẫn bạn lấy hoặc sửa phần đó.

## Bước 8 — Chạy demo NEW an toàn

Tạo một job NEW test trực tiếp; hoặc tạo một dòng Sheet nếu bạn đã bật tracker:

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
Chạy WP Publish cho job [job-id hoặc Row ID] theo route NEW.
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
- nếu có Sheet, dòng chuyển sang `Chờ đăng` và có URL draft;
- chạy lại không tạo bài hoặc ảnh trùng.

Sau đó AI phải mở bản Nháp bằng phiên đã đăng nhập và kiểm tra giao diện thật: nội dung, ảnh, heading,
link và SEO metadata. Khi REST readback lẫn năm kiểm tra render đều đạt, workflow lưu bằng chứng và
chuyển **đúng loại nội dung vừa test** sang `batch-ready`.

Từ thời điểm đó, các bài cùng loại có thể chạy hàng loạt: AI chuẩn bị toàn bộ bundle, đưa một manifest
tổng hợp để bạn duyệt một lần, rồi tạo từng draft và readback từng bài. Không hỏi lại từng bài, nhưng
bài lỗi sẽ dừng riêng và được liệt kê trong báo cáo batch.

## Khi nào dùng AUDIT?

Chỉ dùng `AUDIT` khi bài đã tồn tại trên WordPress. Workflow phải kéo HTML hiện tại, tạo backup, trình
phần thay đổi và chờ bạn duyệt trước khi cập nhật. Người làm audit chọn `MINIMAL_DIFF` khi sửa từng
đoạn hoặc `REBUILD` khi thay body/structure; AI không tự suy mode từ URL hay độ dài bản nháp. Xem
[luồng AUDIT chi tiết](audit-publish-flow.md) để biết các bước riêng của hai mode.

## Cấu trúc thư mục khi chạy

Mọi thứ nằm trong **một thư mục duy nhất** — bản kit bạn tải về. Hai phần tách bạch:

```
thu-muc-lam-viec/
└── wp-publish-workflow-kit/          ← thư mục kit (clone hoặc tải về)
    │
    │  PHẦN CÓ SẴN (code, public được)
    ├── skills/                        ← AI đọc để biết cách làm (5 skill)
    ├── workflows/                     ← luật + state machine + script
    ├── templates/
    │   └── project-skeleton/          ← cấu trúc project mẫu nhìn thấy ngay
    ├── docs/ · snippets/ · tools/
    │
    │  PHẦN SINH THÊM (dữ liệu riêng, .gitignore chặn khỏi Git)
    ├── .env.wp-publish                ← credential local, mode 0600
    └── projects/
        └── ten-client/                ← script sinh từ project-skeleton khi setup
            ├── context.md                        ← brand fact của client
            ├── publish-context.md                ← ghi chú quyết định cách đăng
            ├── publish-context.json              ← profile blog/service/product
            ├── scans/                            ← kết quả scan read-only + đề xuất
            └── content/                          ← tách blog/service-page/product
                └── blog/<slug>/                   ← mỗi bài có một folder riêng
                    ├── assets/original/<run-id>/  ← ảnh gốc tải về/được cung cấp
                    ├── assets/prepared/<run-id>/  ← ảnh đã chuẩn bị để upload
                    ├── backups/                  ← HTML WordPress trước mỗi lần AUDIT
                    └── runs/<run-id>/
                        ├── intake/               ← snapshot content nguồn
                        ├── snapshot/             ← HTML + metadata WP trước AUDIT
                        ├── work/                 ← ZIP Doc, mapping, bản nháp chuyển đổi
                        └── bundle/               ← HTML duyệt, hash, trạng thái, readback
```

Tạo bộ khung client bằng một lệnh:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client ten-client
```

Lệnh này chỉ tạo bộ khung client. Khi có bài cụ thể, tạo một lần chạy riêng:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_item.py \
  --client ten-client --content-type blog --slug ten-bai --run-id 2026-09-25-audit-01
```

Mỗi lần cập nhật lại cùng bài dùng `run-id` mới. Ảnh WordPress được giữ URL thì không cần tải về;
nếu tải hoặc thêm ảnh, đặt file gốc trong `assets/original/<run-id>/`. Git bỏ qua toàn bộ `projects/`,
vì vậy phải backup riêng folder này; các bản HTML trong `backups/` không tự thay thế backup database
hoặc media WordPress.

Muốn chuyển máy hoặc backup: lưu riêng `projects/` và loại `.env.wp-publish` khỏi file ZIP; không
xoá file credential đang dùng trên máy. Git không giữ dữ liệu trong `projects/`.

## Quy tắc an toàn cần nhớ

1. NEW luôn tạo Nháp, không tự public.
2. AUDIT luôn backup trước khi sửa.
   AUDIT cần chọn rõ `MINIMAL_DIFF` (sửa từng đoạn) hoặc `REBUILD` (thay body theo bản đã duyệt);
   người làm audit quyết định mode trước khi AI chuẩn bị bài. Xem
   [luồng đăng bài AUDIT](audit-publish-flow.md).
3. File content luôn có đúng một H1; body giữ đúng `body_h1_count` H1 đã khai báo.
4. Không gửi mật khẩu vào Sheet, Doc hoặc GitHub.
5. AI phải dừng xin duyệt trước khi ghi WordPress.
6. Chỉ gọi là hoàn tất sau khi đọc lại WordPress và tracker (nếu đã bật) đều khớp.
7. Pilot blog chỉ mở batch cho blog; service page và product vẫn phải xác nhận/test khi được yêu cầu.

Phần cài thủ công dành cho người kỹ thuật nằm ở [setup.md](setup.md). Checklist ngắn nằm ở
[checklist-chuan-bi.md](checklist-chuan-bi.md).
