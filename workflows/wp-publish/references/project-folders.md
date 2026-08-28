# Standard project folders for wp-publish

Mỗi client dùng đúng cấu trúc sau:

```text
projects/<client>/
├── context.md                              # brand/business source of truth; workflow never overwrites
├── knowledge/
│   ├── publish-context.md                  # site-specific decisions and precedent
│   └── publish-context.json                # machine gate; ready=false until live setup is verified
└── content/
    ├── 06-assets/                          # immutable originals + optimized derivatives
    ├── 07-publish-ready/<slug>/            # one current inspectable bundle per article
    ├── _audit-snapshots/                   # immutable pre-update WordPress raw backups
    └── _inbox/                             # temporary Doc ZIP/export; ignored by git
```

Rules:

- Không copy draft Markdown local vào `07-publish-ready`; chỉ lưu source lock.
- Google Doc có đúng một snapshot hiện hành trong bundle; xóa ZIP export sau khi đã inventory.
- Không lưu ảnh trong bundle; ảnh dùng chung ở `06-assets/`.
- Không ghi đè `context.md`, `memory.md` hoặc publish context đã tồn tại.
- Chưa xác nhận integration thì giữ `ready=false`; đây là stop gate, không phải trạng thái lỗi.

Project mới:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client '<client-slug>'
```

