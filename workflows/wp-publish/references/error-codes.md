# Error codes

Tập mã đóng; chi tiết cụ thể để trong `details`, không sinh mã theo câu chữ.

| Code | Stop? | Meaning |
|---|---:|---|
| `INPUT-MISSING` | yes | thiếu field Sheet/bundle bắt buộc |
| `BRAND-MISSING` | yes | thiếu context/site rule cần cho quyết định |
| `ROUTE-CONFLICT` | yes | ý định Sheet mâu thuẫn trạng thái WP |
| `SOURCE-STALE` | yes | nguồn đổi sau lock/approval |
| `IMG-MISSING` | yes | file/URL ảnh bắt buộc không tồn tại |
| `IMG-COUNT` | yes | inventory và HTML lệch |
| `IMG-DUP` | yes | trùng tên nhưng không đủ bằng chứng cùng asset |
| `IMG-SIZE` | yes | ảnh vẫn vượt ngưỡng dung lượng sau tối ưu |
| `ALT-MISSING` | yes | ảnh informative thiếu alt |
| `STRONG-DIFF` | yes | strong transform/report lệch |
| `WP-WAF` | yes | WP trả HTML/challenge thay JSON |
| `WP-TIMEOUT` | yes | trạng thái POST chưa reconcile được |
| `VERIFY-DIFF` | yes | readback khác payload được duyệt |
| `SHEET-WRITE` | yes | writeback thất bại |
| `SHEET-READBACK` | yes | đọc lại Sheet không khớp |
| `RESUME-CONFLICT` | yes | run state không khớp input hiện tại |
| `CLEANUP-REQUIRED` | yes | có orphan/công việc cleanup cần người duyệt |
