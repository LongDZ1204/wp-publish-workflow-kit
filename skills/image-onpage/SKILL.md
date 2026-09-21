---
name: image-onpage
description: "Audit and prepare existing article images for on-page SEO: inventory, semantic filename, size/format, alt, caption, and WordPress media mapping. Use for both new WordPress posts and audited existing posts. Does not generate new visuals; use brand-infographic for that."
---

# Image on-page

Tối ưu ảnh **có sẵn** và sinh `image-manifest.json` để workflow publish tiêu thụ. Đọc
[`standards.md`](standards.md) cho chuẩn chung và brand/site overrides trong
`projects/<client>/context.md` plus the selected profile in `projects/<client>/publish-context.json`.

## Hai mode

- `prepare-new`: chuẩn hóa mọi ảnh local trước upload; giữ file gốc, output sang thư mục mới.
- `audit-existing`: inventory mọi ảnh; giữ URL/filename ảnh live mặc định. Chỉ process file mới hoặc ảnh
  có `approved_replace=true`.

Mode là bắt buộc trong cả NEW và AUDIT. “Audit ảnh” không đồng nghĩa đổi URL ảnh live.

## Input contract

JSON gồm `profile` và `images`. Mỗi image cần `asset_id`, `alt` (trừ decorative), cùng một trong
`source` hoặc `existing_url`.

```json
{
  "profile": {"format_policy": "preserve", "max_kb": 150, "max_width": 1200},
  "images": [
    {
      "asset_id": "hero",
      "source": "projects/client/content/blog/example/assets/hero.jpg",
      "filename": "editorial-review-workflow.jpg",
      "heading": "Editorial review workflow",
      "alt": "Editor reviewing article structure before WordPress publication",
      "caption": "",
      "decorative": false
    }
  ]
}
```

Alt/caption là quyết định semantic: phải xem ảnh thật, heading và brand context; script không tự bịa.

## Chạy deterministic

```bash
python3 skills/image-onpage/scripts/image_prepare.py \
  --mode prepare-new --request image-request.json \
  --output-dir projects/<client>/content/<content-type>/<slug>/assets/prepared \
  --manifest projects/<client>/content/<content-type>/<slug>/bundle/image-manifest.json
```

Script:

- không ghi đè ảnh nguồn;
- validate filename/alt;
- resize/compress theo profile;
- giữ JPG/PNG khi `format_policy=preserve`;
- sinh manifest đối soát trước/sau;
- fail closed khi không đạt trần dung lượng hoặc file collision.

WordPress upload/reuse thuộc skill publish, không thuộc skill này.

## Gate

- Mọi `<img>`/asset token có đúng một manifest item.
- Informative image có alt cụ thể; decorative image có `alt=""`.
- Không lặp alt trong cùng bài.
- Audit existing không đổi URL nếu chưa approved.
- Không tự sinh caption cho có.

## Test

```bash
python3 -m unittest discover -s skills/image-onpage/tests -p 'test_*.py'
```
