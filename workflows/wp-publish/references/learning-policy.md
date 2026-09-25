# Compact learning policy

Learning là recommendation loop, không phải self-modifying production.

## Storage

- Sheet: chỉ status/error hiện hành.
- `runs/<run-id>/bundle/run-state.json`: một record cho mỗi lần chạy, cập nhật tại chỗ; lần chạy
  sau dùng `run-id` mới và giữ nguyên lịch sử cũ.
- `learning-index.json`: một record per stable `learning_key`, aggregate counter.
- `learnings.md`: chỉ luật đã được operator duyệt; không chứa raw log.
- Không tạo `learnings-archive.md`; Git history là archive.

## Stable key

`<ERROR_CODE>|<client-or-global>|<step>`; cùng key tăng counter, không append entry.

Mỗi record chỉ giữ: count, distinct run count, first/last seen, tối đa ba sample run IDs, status và
candidate summary. Smooth run không ghi event mới.

## Promotion

- Ít nhất ba `run_id` khác nhau.
- Có root cause, proposed deterministic guard, target file và required regression test.
- operator duyệt trước khi sửa skill/script/context.
- Site-specific → `projects/<client>/publish-context.md` after explicit user confirmation.
- Cross-client technical → workflow/tool/skill tương ứng.
- Không có check chạy được → không promote thành rule.

## Size guard

- `learnings.md` hard cap 15KB.
- Một key chỉ một entry; update tại chỗ.
- Index chỉ giữ tối đa ba evidence IDs per key.
- Candidate resolved không tạo bản sao; đổi `status` tại chỗ.
