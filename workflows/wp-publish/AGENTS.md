# Workflow `wp-publish` — entrypoint cho Codex/agent ngoài Claude Code

Quy trình đầy đủ nằm ở [`CLAUDE.md`](CLAUDE.md). Đọc file đó trước khi làm bất kỳ bước nào.

Hai lưu ý bắt buộc cho agent ngoài Claude Code:

1. Không dựa vào auto-memory để lấy brand/site rule; phải đọc `projects/<client>/context.md` và
   `projects/<client>/publish-context.json` trực tiếp.
2. Không dùng kết quả local/dry-run làm bằng chứng đã cập nhật WordPress hoặc Sheet. Completion cần
   readback từ cả hai nguồn thật.
