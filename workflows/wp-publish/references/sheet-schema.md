# Optional Google Sheet tracker contract

Sheet is an optional input adapter and operational tracker. Core publishing works with
`tracker.type=none`. When enabled, the row is normalized to the v2 job contract and the workflow must
complete writeback/readback by immutable Row ID.
The local scripts validate and verify data; an authorized Sheets connector performs the actual
read/write. Project tracker configuration identifies the spreadsheet and tab. Resolve exactly one
row per Row ID before any update; duplicates or a missing row stop the run.

## Visible columns

| Column | Owner | Notes |
|---|---|---|
| `Row ID` | workflow | khóa immutable, tự sinh, có thể ẩn |
| `Bài / Title` | operator | tiêu đề dự kiến |
| `Loại bài` | operator | chỉ `NEW` hoặc `AUDIT`; workflow không tự đổi |
| `Nguồn content` | operator | Google Doc URL/ID, local Markdown path or local HTML path |
| `Slug / URL WP` | operator | NEW nhập exact slug; AUDIT nhập exact URL hiện tại |
| `Meta description` | operator | meta cần đẩy; adapter site quyết định khả năng ghi REST |
| `Ngày public dự kiến` | operator | input lịch, không phải thời gian public thực tế |
| `Trạng thái` | workflow | tiến độ vận hành dạng dropdown |
| `URL draft/live` | workflow | NEW trả URL draft; AUDIT trả URL live đã verify |
| `Note` | workflow/operator | lỗi hiện hành, hash duyệt hoặc lưu ý; mã lỗi đặt đầu note |
| `Cập nhật lúc` | workflow | timestamp tự động khi workflow ghi dòng |

`Client`, `site_key`, default category/tag/author và chính sách media lấy từ publish context của tab;
không lặp lại trên từng dòng. `Run ID`, post ID, source revision, approval hash đầy đủ và bước kỹ thuật
được giữ trong bundle/run-state. Chiến lược audit `MINIMAL_DIFF`/`REBUILD` do workflow audit đã duyệt quyết
định, không phải input vận hành trên Sheet.

Giá trị `Trạng thái` và mốc được phép ghi:

| Trạng thái | Khi nào |
|---|---|
| `Chờ chạy` | dòng đã đủ input nhưng workflow chưa được chạy |
| `Chờ xác nhận` | bản chuẩn bị đã đạt gate; cần operator xác nhận trước khi ghi WordPress |
| `Chờ đăng` | chỉ dùng cho NEW: draft đã tạo và verify; chờ người thật bấm public |
| `Hoàn tất` | NEW đã public hoặc AUDIT đã cập nhật live, và readback thành công |
| `Cần xử lý` | workflow dừng vì lỗi/thiếu dữ liệu; xem nguyên nhân hiện hành trong `Note` |

Không đưa trạng thái kỹ thuật thoáng qua như `Đang chuẩn bị` lên dropdown. Không được ghi `Hoàn tất` chỉ
vì tạo draft thành công.

## Writeback invariants

- Upsert bằng `Row ID`; không append mù.
- `Loại bài` không bị workflow tự đổi.
- `Note` chỉ giữ lỗi hiện hành; lịch sử đầy đủ nằm trong run-state.
- Write xong phải readback đúng `Row ID` và các field vừa ghi.
- Ô bắt buộc trống → `INPUT-MISSING`, dừng.
