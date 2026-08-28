# strong-to-b

Đổi `<strong>` → `<b>` trong HTML, **giữ nguyên** `<strong>` nằm trong **heading** (`h1`–`h6`) và **link** (`<a>`, kể cả khi `<a>` nằm trong `<strong>`).

Phép biến đổi **xác định** — tokenize HTML rồi chỉ splice đúng byte của thẻ `<strong>`/`</strong>` cần đổi. Mọi ký tự khác (attribute, xuống dòng, thẻ HOA, `<b>` có sẵn, nội dung `<script>`/`<style>`/comment) giữ nguyên 100%.

## Dùng

```bash
# mode paste: stdin -> stdout (+ báo cáo ở stderr)
echo '<p><strong>x</strong></p>' | python3 strong_to_b.py

# mode file: ghi scratch/outputs/<ten>.b.html (giữ bản gốc)
python3 strong_to_b.py bai-viet.html
python3 strong_to_b.py bai-viet.html -o /duong/dan/khac.html

# chỉ xem báo cáo
python3 strong_to_b.py bai-viet.html --report-only
```

## Quy tắc vùng cấm

`<strong>` GIỮ NGUYÊN nếu thỏa **bất kỳ**:
- tổ tiên là `h1`–`h6` (strong trong heading)
- tổ tiên là `a` (strong trong link)
- hậu duệ là `a` (link trong strong) → cả cụm strong giữ nguyên

Còn lại → `<b>` (giữ attribute: `<strong class="x">` → `<b class="x">`).

> Muốn đảo quy tắc "strong *chứa* link vẫn đổi sang b"? Sửa `convert()` trong `strong_to_b.py`: bỏ nhánh đánh dấu `prot=True` khi gặp `<a>` trong `pending` (khối `elif tag == "a":`).

## Báo cáo

```
Tổng <strong> tìm thấy : N
Đã đổi sang <b>        : X
Giữ nguyên (vùng cấm)  : Y (trong heading A, trong link B)
```

## Test

```bash
python3 -m pytest -q
```

25 case: convert (p/li/td/label) · protect (heading, link 2 chiều lồng) · giữ attribute · `<b>` cũ · raw block (script/style/comment) · strong lồng nhau · whitespace · thẻ HOA · idempotent · thẻ thiếu đóng.
