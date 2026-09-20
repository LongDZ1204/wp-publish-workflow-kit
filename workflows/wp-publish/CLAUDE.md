# Workflow `wp-publish` — chuẩn bị, duyệt và đẩy bài lên WordPress

## 1. Vai trò và ranh giới

Đây là **cửa vào duy nhất cho vận hành đăng/cập nhật bài viết từ Google Sheet**. Sheet quyết định ý định
`NEW` hay `AUDIT`; WordPress chỉ được dùng để đối chiếu trạng thái thật và fail closed khi hai phía mâu
thuẫn.

Workflow gọi các component, không viết lại logic của chúng:

- `skills/wp-publish-new/` — tạo bài mới ở trạng thái `draft`.
- `skills/wp-rest-publish/` — cập nhật bài đã tồn tại, có backup + gate.
- `skills/image-onpage/` — gate ảnh bắt buộc cho cả hai route.
- `skills/strong-to-b/` — biến đổi HTML xác định, bắt buộc cho cả hai route.
- `skills/internal-link-insertion/` — integration ngoài repository, chỉ chạy khi đã cài và plan đã duyệt.

**NEVER**:

1. Không tự đổi route vì slug; route đến từ `Loại bài` trên Sheet.
2. Không coi WordPress/Sheet trả lỗi hoặc HTML WAF là “không tìm thấy”.
3. Không push khi chưa có xác nhận rõ ràng của operator cho đúng approval hash.
4. Không tự publish bài mới; đích mặc định luôn là `draft`.
5. Không retry mù thao tác POST; phải reconcile trạng thái thật trước.
6. Không tự sửa skill/context từ learning candidate.
7. Không đổi URL/filename ảnh live trong route audit nếu chưa được duyệt.
8. Không bỏ hoặc tự sinh H1; source content phải có đúng một H1. Body giữ đúng `body_h1_count` trong publish-context (0 nếu theme đã in tiêu đề bài thành H1, 1 nếu body chịu trách nhiệm H1).

## 2. Nguồn sự thật

| Dữ liệu | Nguồn sự thật |
|---|---|
| Ý định NEW/AUDIT, input, lịch | Google Sheet |
| Trạng thái post/media hiện tại | WordPress REST `context=edit` |
| Brand, voice, language, market | `projects/<client>/context.md` |
| Quy tắc publish riêng site | `projects/<client>/knowledge/publish-context.md` |
| Nội dung được duyệt | bundle trong `content/07-publish-ready/<slug>/` |
| Bản WP trước audit | `content/_audit-snapshots/` |
| Lỗi hiện hành | Sheet + `run-state.json` |
| Learning đã duyệt | `learnings.md` hoặc `publish-context.md` |

Đọc [bundle-contract.md](references/bundle-contract.md), [sheet-schema.md](references/sheet-schema.md)
và [state-machine.md](references/state-machine.md) trước mỗi ca chạy. Project mới phải được scaffold theo
[project-folders.md](references/project-folders.md) bằng `scripts/wp_scaffold_project.py`.
Credential nằm trong `CLAUDE.local.md` (gitignored), format theo `templates/CLAUDE.local.example.md`:
user riêng role Editor, mỗi site một khối `### <site> WordPress (REST API)`. Operator tự dán; script
`scripts/wp_setup_credentials.py` là tuỳ chọn có kiểm tra role. Không nhận password qua chat, không
đưa password vào command line.

## 3. Pipeline bắt buộc

### P0 — Chọn dòng và khóa context (read-only)

1. Đọc đúng một dòng Sheet theo `Row ID`.
2. Validate input bằng `scripts/wp_sheet_contract.py`.
3. Xác định client/site từ publish context gắn với tab, không lặp lại trên từng dòng.
4. Đọc `projects/<client>/context.md` và `projects/<client>/knowledge/publish-context.md`.
5. Thiếu field/site rule bắt buộc → `BRAND-MISSING` hoặc `INPUT-MISSING`, ghi Sheet rồi dừng.

Khởi tạo và cập nhật journal bằng `scripts/wp_state.py`; mọi transition được ghi atomically vào
`run-state.json` để resume đúng `run_id`.

### P1 — Đối chiếu route (read-only)

Fetch WordPress bằng post ID/slug và tạo `wp-state.json`, sau đó chạy:

```bash
python3 workflows/wp-publish/scripts/wp_route.py \
  --row row.json --wp-state wp-state.json --out route.json
```

- `NEW` + chưa có post → `NEW_PREPARE`.
- `NEW` + draft do cùng run tạo → `NEW_RESUME`.
- `AUDIT` + tìm thấy đúng post → `AUDIT_PREPARE`.
- Mọi mâu thuẫn → `ROUTE-CONFLICT`, dừng; không tự đổi loại.

### P2 — Chuẩn bị bundle (chưa ghi WordPress)

- Google Doc: connector kéo chữ + ảnh; lưu **một** snapshot hiện hành và `source-lock.json`.
- Markdown local: không copy nguồn; `source-lock.json` giữ path + SHA-256.
- Source Google Doc/Markdown/HTML phải có đúng một H1; thiếu hoặc trùng H1 thì dừng.
- Ảnh gốc về `content/06-assets/`; không copy vào bundle.
- Route `NEW` gọi `wp-publish-new`.
- Route `AUDIT` fetch `content.raw` + immutable backup rồi gọi `wp-rest-publish` để dựng bản mới.

### P3 — Shared mandatory normalization

Áp dụng cho **cả NEW và AUDIT**:

1. `image-onpage` sinh/kiểm `image-manifest.json`.
   - NEW: full prepare ảnh mới.
   - AUDIT: audit toàn bộ; giữ URL live mặc định, full prepare chỉ với ảnh mới/thay đã duyệt.
2. Chạy `scripts/wp_strong.py` để gọi engine `strong-to-b` trên HTML đã dựng và sinh
   `transform-report.json`.
3. Nếu có internal-link plan đã duyệt: chạy `internal-link-insertion`; nếu không, bỏ qua không cảnh báo.
4. Chạy gate bundle; in diff + bảng ảnh + báo cáo strong.

### P4 — Operator approval gate

Approval gắn với hash của `publish-request.json`, `content.prepared.html`, `image-manifest.json` và
`transform-report.json`. Chỉ sau khi operator xác nhận rõ cho đúng hash, chạy lệnh approve để tạo
`approval.json`.

Nếu file đổi sau approval → approval invalid, quay lại P3/P4.

### P5 — Ghi WordPress

- `NEW`: upload/reuse media, thay asset token, gate final, tạo hoặc resume đúng WordPress draft.
- `AUDIT`: fresh fetch + so `modified`; lệch snapshot → dừng. Push qua `wp-rest-publish`.
- Google Doc: connector đọc lại revision/`modifiedTime`; khác `source-lock.json` → `SOURCE-STALE`.
- POST timeout → query trạng thái thật trước khi quyết định retry.

### P6 — Verify và Sheet readback

1. GET post `context=edit`; so `content.raw`, status, title, image count và post ID.
2. NEW phải còn `draft`; AUDIT phải đúng status live trước đó.
3. Ghi Sheet theo `Row ID` (upsert, không append mù).
4. Đọc lại đúng dòng, đối chiếu các field vừa ghi.
5. Chỉ khi cả WP + Sheet readback xanh mới chuyển `VERIFIED`.

Dùng `scripts/wp_sheet_io.py prepare` để tạo patch chỉ chứa tracking field được phép; sau khi connector
ghi và đọc lại đúng dòng, dùng `scripts/wp_sheet_io.py verify` để chặn `SHEET-READBACK`.

### P7 — Learning compact

Chỉ ghi event khi STOP hoặc `VERIFY-DIFF`. Chạy:

```bash
python3 workflows/wp-publish/scripts/wp_learn.py record --index workflows/wp-publish/learning-index.json --event event.json
python3 workflows/wp-publish/scripts/wp_learn.py candidates --index workflows/wp-publish/learning-index.json
```

Learning candidate không có quyền sửa file. Đọc [learning-policy.md](references/learning-policy.md).

## 4. Gate hoàn thành

Một ca chỉ hoàn thành khi:

- Bundle đúng contract, approval còn hiệu lực.
- Không còn local path, asset token hoặc marker Markdown trong HTML final.
- HTML final có đúng `body_h1_count` H1 theo publish-context.
- Image gate và strong report xanh.
- NEW là draft; AUDIT có backup + revision/readback.
- Không tạo trùng post/media/Sheet row khi rerun.
- Sheet readback khớp.

## 5. Lệnh self-test

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 -m unittest discover -s workflows/wp-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-publish-new/tests -p 'test_*.py'
python3 -m unittest discover -s skills/wp-rest-publish/tests -p 'test_*.py'
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
python3 -m pytest tools/strong-to-b/test_strong_to_b.py -q
```
