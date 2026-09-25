# Job contract v2

The job is the core publishing input and is independent from any tracker.

```json
{
  "version": 2,
  "job_id": "job-2026-001",
  "run_id": "run-2026-001",
  "client": "example-client",
  "site_key": "example-site",
  "task_type": "NEW",
  "content_type": "blog",
  "title": "Example",
  "slug": "example",
  "source": {"adapter": "local_html", "ref": "article.html"},
  "tracker": {"type": "none"}
}
```

Required for all jobs: `job_id`, `run_id`, `client`, `site_key`, `task_type`, `content_type`, `title`,
`source.adapter` and `source.ref`. Adapters: `local_markdown`, `local_html`, `google_doc`. Content
types: `blog`, `service-page`, `product`. NEW also needs `slug`; AUDIT needs `target_url` or `post_id`
and an explicit `update_mode` (`MINIMAL_DIFF` or `REBUILD`). Never infer the mode from the slug or
changed word count. The approved editorial audit owns that decision.

Trackers are `none` or `google_sheet`. A Sheet row remains backward compatible: `row_id` becomes
`job_id=sheet:<row_id>` and the adapter emits `tracker.type=google_sheet`.
