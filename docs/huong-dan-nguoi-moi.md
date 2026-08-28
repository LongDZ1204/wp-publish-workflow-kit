# Hướng dẫn người mới sử dụng WP Publish Workflow Kit

Tài liệu này dành cho người chưa từng chạy workflow. Mục tiêu của lần đầu không phải đăng thật ngay,
mà là tạo được **một bài NEW ở trạng thái WordPress draft**, kiểm tra kết quả, rồi mới mở route AUDIT.

## 1. Hiểu workflow trong 2 phút

```text
Google Sheet       Google Doc / Markdown       Codex + workflow       WordPress
  giao việc    +      nguồn nội dung       ->   chuẩn bị + duyệt   ->  draft/update
     ^                                                   |
     └────────────────── readback trạng thái ────────────┘
```

- **Google Sheet** là hàng đợi công việc và nơi theo dõi trạng thái.
- **Google Doc hoặc Markdown** là nguồn nội dung; không dán toàn bộ bài vào Sheet.
- **Bundle** là bộ file trung gian để kiểm tra trước khi ghi WordPress.
- **Approval hash** là dấu vân tay của đúng bộ nội dung đã duyệt. File đổi thì phải duyệt lại.
- **Readback** là đọc ngược dữ liệu từ WordPress và Sheet sau khi ghi để chứng minh thao tác thành công.

Workflow có hai route tách biệt:

| Route | Dùng khi | Kết quả |
|---|---|---|
| `NEW` | Bài chưa tồn tại trên WordPress | Tạo đúng một bài `draft`, không tự public |
| `AUDIT` | Cập nhật bài đã tồn tại | Backup HTML hiện tại, cập nhật rồi kiểm tra lại live |

## 2. Workflow làm gì và không làm gì

Workflow hỗ trợ:

- phân route NEW/AUDIT từ Sheet;
- chuẩn bị nội dung và ảnh;
- tối ưu thẻ `<strong>` theo rule đã định;
- khóa bản duyệt bằng hash;
- ghi WordPress có kiểm tra xung đột;
- ghi và đọc lại trạng thái trên Sheet;
- dừng an toàn khi nguồn, quyền hoặc trạng thái không rõ ràng.

Workflow không tự:

- viết hoặc duyệt chất lượng bài thay con người;
- public bài NEW;
- tạo WordPress user hay cấp quyền;
- cài Google connector;
- đoán brand context, category, author hoặc SEO meta adapter;
- tự retry POST khi chưa biết WordPress đã nhận lệnh hay chưa.

## 3. Những thứ cần chuẩn bị

### Trên máy người chạy

- Git.
- Python 3.10 trở lên.
- Codex desktop/CLI có hỗ trợ plugin.
- Quyền đọc Google Sheet/Doc hoặc file Markdown local.

### Trên WordPress

- URL website chính xác.
- Một tài khoản WordPress có quyền phù hợp với post và media.
- `Application Password`: mật khẩu riêng cho REST API, có thể thu hồi mà không đổi mật khẩu đăng nhập.
- Xác định plugin SEO đang dùng, ví dụ Yoast hoặc Rank Math, và kiểm tra meta có cho phép ghi qua REST.
- Chốt WordPress giữ H1 trong body hay theme tự sinh H1.

### Trên Google Sheet

Dùng đúng 11 cột trong [google-sheet-template.md](google-sheet-template.md). Hai dropdown bắt buộc:

- `Loại bài`: `AUDIT`, `NEW`.
- `Trạng thái`: `Chờ chạy`, `Chờ xác nhận`, `Chờ đăng`, `Hoàn tất`, `Cần xử lý`.

### Context của website

Cần chốt tối thiểu:

- brand, ngôn ngữ, thị trường và spelling;
- domain, `site_key` và timezone;
- chính sách định dạng ảnh, dung lượng và chiều rộng tối đa;
- H1 trong body;
- Sheet ID và tab;
- SEO meta adapter;
- category/tag/author mặc định nếu có.

## 4. Cài repository và plugin

### Bước 1 — Clone source

```bash
git clone https://github.com/LongDZ1204/wp-publish-workflow-kit.git
cd wp-publish-workflow-kit
```

### Bước 2 — Cài dependency Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Trên Windows PowerShell, lệnh kích hoạt môi trường là:

```powershell
.venv\Scripts\Activate.ps1
```

### Bước 3 — Cài plugin vào Codex

```bash
codex plugin marketplace add LongDZ1204/wp-publish-workflow-kit --ref main
codex plugin add wp-publish-workflow-kit@seo-cowork-tools
```

Khởi động lại ứng dụng, mở một task mới và thử:

```text
Scaffold một project demo cho wp-publish, chưa ghi WordPress.
```

Nếu chưa muốn cài plugin, vẫn có thể mở repository này bằng Codex và yêu cầu đọc
`skills/wp-publish/SKILL.md` trước khi chạy.

## 5. Setup một website mới

Ví dụ client slug là `demo-client`:

```bash
mkdir -p projects/demo-client
cp templates/context.example.md projects/demo-client/context.md
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client demo-client
```

Sau đó:

1. Điền fact đã xác minh vào `projects/demo-client/context.md`.
2. Điền `projects/demo-client/knowledge/publish-context.md`.
3. Copy template machine config:

   ```bash
   cp templates/publish-context.example.json \
     projects/demo-client/knowledge/publish-context.json
   ```

4. Giữ `ready=false` trong lần setup đầu.
5. Chỉ đổi thành `ready=true` sau khi REST, Sheet, SEO meta và media round-trip đều đã test.

Folder `projects/` được Git bỏ qua để tránh đưa credential, source bài và context khách hàng lên repo.

## 6. Cấp WordPress credential an toàn

Cách khuyến nghị là biến môi trường — giá trị chỉ tồn tại trong terminal hiện tại:

```bash
export WP_URL='https://example.com'
export WP_USER='wordpress-api-user'
export WP_APP_PASS='xxxx xxxx xxxx xxxx xxxx xxxx'
```

Trên Windows PowerShell:

```powershell
$env:WP_URL='https://example.com'
$env:WP_USER='wordpress-api-user'
$env:WP_APP_PASS='xxxx xxxx xxxx xxxx xxxx xxxx'
```

Không đặt Application Password trong:

- Google Sheet;
- `context.md` hoặc `publish-context.json`;
- command đã commit;
- ảnh chụp/log gửi công khai;
- GitHub repository.

## 7. Chạy kiểm tra trước lần đầu

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 scripts/check_distribution.py
```

Sau đó nhờ Codex chạy read-only check:

```text
Chạy preflight wp-publish cho project demo-client. Chỉ kiểm tra context, quyền đọc Sheet,
WordPress REST và media; chưa tạo hoặc cập nhật post.
```

Không chuyển `ready=true` nếu còn một trong các lỗi:

- REST trả HTML/WAF thay vì JSON;
- không đọc được đúng Sheet tab;
- không biết H1 do theme hay body sở hữu;
- chưa biết meta adapter;
- media upload/readback chưa kiểm tra;
- slug pilot đã tồn tại.

## 8. Demo an toàn đầu tiên: NEW draft

Tạo một dòng Sheet:

| Cột | Giá trị mẫu |
|---|---|
| `Bài / Title` | WP Publish Integration Test |
| `Loại bài` | NEW |
| `Nguồn content` | Google Doc test hoặc file Markdown test |
| `Slug / URL WP` | wp-publish-integration-test |
| `Meta description` | Nội dung test ngắn, không dùng dữ liệu khách hàng |
| `Trạng thái` | Chờ chạy |

Prompt khuyến nghị:

```text
Chạy wp-publish cho Row ID <row-id> của project demo-client theo route NEW.
Chỉ chuẩn bị bundle và dừng ở Chờ xác nhận; chưa ghi WordPress.
```

Codex phải trình:

- route đã khóa là NEW;
- title, slug và nguồn;
- diff/nội dung prepared;
- image manifest;
- strong transform report;
- approval hash;
- các lỗi hoặc warning còn lại.

Sau khi người duyệt kiểm tra xong, xác nhận rõ:

```text
Tôi duyệt đúng approval hash <sha256>. Tạo WordPress draft, không public.
```

Kết quả đúng:

- WordPress có đúng một post mới ở trạng thái `draft`;
- title, slug, body và ảnh đọc lại khớp;
- Sheet chuyển `Chờ đăng`;
- `URL draft/live` có URL draft;
- chạy lại cùng run không tạo post hoặc media trùng.

## 9. Chạy AUDIT sau khi pilot NEW đạt

AUDIT chỉ dùng cho URL đã tồn tại. Prompt mẫu:

```text
Chạy wp-publish cho Row ID <row-id> của project demo-client theo route AUDIT.
Fetch content.raw mới nhất, tạo immutable backup, dựng minimal diff và dừng trước khi push.
```

Trước khi duyệt phải kiểm tra:

- đúng post ID và URL;
- backup đã tồn tại;
- mỗi chuỗi cũ match đúng một lần;
- table, image, iframe, shortcode và vùng frozen không mất;
- WordPress `modified` chưa đổi từ lúc fetch;
- approval hash đúng bản đang xem.

Chỉ xác nhận push khi các gate đều xanh. AUDIT hoàn tất khi nội dung live và Sheet đều được đọc lại.

## 10. Ý nghĩa trạng thái Sheet

| Trạng thái | Người vận hành cần làm gì |
|---|---|
| `Chờ chạy` | Dòng đủ input, có thể giao workflow chạy |
| `Chờ xác nhận` | Mở bundle/diff, duyệt hoặc yêu cầu sửa |
| `Chờ đăng` | NEW draft đã tạo; người thật kiểm tra và public trong WP Admin |
| `Hoàn tất` | AUDIT đã verify hoặc NEW đã public và được xác nhận |
| `Cần xử lý` | Đọc mã lỗi đầu cột `Note`, sửa nguyên nhân rồi resume |

## 11. Lỗi thường gặp

| Mã/triệu chứng | Ý nghĩa | Cách xử lý |
|---|---|---|
| `BRAND-MISSING` | Publish context chưa đủ hoặc chưa ready | Điền/verify context; không tắt gate |
| `INPUT-MISSING` | Dòng Sheet thiếu field bắt buộc | Bổ sung input rồi chạy lại đúng Row ID |
| `ROUTE-CONFLICT` | NEW/AUDIT mâu thuẫn trạng thái WordPress | Kiểm tra lại loại bài và URL; không tự đổi route |
| `SOURCE-STALE` | Nguồn đổi sau lúc khóa bundle | Pull nguồn mới và duyệt lại |
| `WP-WAF` | WordPress trả trang HTML/challenge | Dừng, kiểm tra WAF/CDN; không hiểu là “không có post” |
| `SHEET-READBACK` | Sheet ghi xong nhưng đọc lại không khớp | Kiểm tra quyền/range và reconcile theo Row ID |
| Approval invalid | File đã đổi sau khi duyệt | Tạo hash mới và xin duyệt lại |

## 12. Checklist hoàn tất setup

- [ ] Clone repo và cài Python dependency.
- [ ] Plugin xuất hiện trong Codex sau khi restart.
- [ ] Project context có fact thật, không có credential.
- [ ] Publish context đã chốt H1, media, meta, Sheet và timezone.
- [ ] Đọc được đúng Sheet tab và Row ID.
- [ ] WordPress REST GET trả JSON đúng site.
- [ ] Media upload/readback test thành công.
- [ ] Pilot NEW tạo đúng một draft và không public.
- [ ] Rerun không tạo trùng.
- [ ] Sheet writeback/readback đúng năm trạng thái.
- [ ] Chỉ sau các bước trên mới bật `ready=true` và chạy bài thật.

## 13. Nguyên tắc an toàn cần nhớ

1. Sheet khai báo NEW/AUDIT; workflow không tự đoán route.
2. NEW luôn là draft.
3. AUDIT luôn có fresh snapshot và backup.
4. Mọi write phải gắn với đúng approval hash.
5. Timeout sau POST phải GET/reconcile trước khi retry.
6. Chưa readback WordPress và Sheet thì chưa được gọi là hoàn tất.
7. Learning chỉ tạo candidate; không tự sửa skill hoặc rule production.

Tài liệu kỹ thuật chi tiết: [setup.md](setup.md), [google-sheet-template.md](google-sheet-template.md)
và [SECURITY.md](../SECURITY.md).
