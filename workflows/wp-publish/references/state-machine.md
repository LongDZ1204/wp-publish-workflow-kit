# State machine và resume contract

`State machine` là bảng trạng thái cho phép workflow biết bước nào được chuyển sang bước nào; dùng để
rerun không tạo bài/media/Sheet row trùng.

## States

```text
NEW → CONTEXT_LOCKED → ROUTED → PREPARED → GATED → APPROVED
    → MEDIA_READY → WP_WRITTEN → WP_VERIFIED → SHEET_VERIFIED → COMPLETE

Mọi state → STOPPED
STOPPED → state trước lỗi (sau khi input/condition được xử lý)
```

## Route outcomes

| Sheet | WP truth | Outcome |
|---|---|---|
| NEW | không có post | `NEW_PREPARE` |
| NEW | draft + cùng `post_id/run_id` trong state | `NEW_RESUME` |
| NEW | post khác đã tồn tại | STOP `ROUTE-CONFLICT` |
| AUDIT | đúng post tồn tại | `AUDIT_PREPARE` |
| AUDIT | không tìm thấy / nhiều kết quả | STOP `ROUTE-CONFLICT` |

## Retry

- GET: tối đa ba lần, backoff tăng dần; HTML/WAF luôn dừng.
- POST: không retry mù. Sau timeout phải GET/reconcile theo post ID, slug hoặc media mapping.
- Mỗi media ID phải persist ngay sau response thành công.

## Resume

- Chỉ resume khi `row_id`, `run_id`, task type, client và source lock khớp.
- File đã đổi sau approval → quay về `PREPARED`, xóa hiệu lực approval (không xóa evidence file).
- Draft đã tạo nhưng Sheet lỗi → resume verify/writeback, không chuyển sang AUDIT.
