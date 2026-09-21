# State machine and resume contract

```text
NEW → CONTEXT_LOCKED → ROUTED → PREPARED → GATED → APPROVED
    → MEDIA_READY → WP_WRITTEN → WP_VERIFIED

tracker=none:          WP_VERIFIED → COMPLETE
tracker=google_sheet:  WP_VERIFIED → TRACKER_VERIFIED → COMPLETE

Any state → STOPPED
STOPPED → state before the error after its condition is fixed
```

Project profile readiness is a separate per-content-type state machine:

```text
unconfirmed → pilot-ready → batch-ready
```

Job completion does not implicitly change profile state. The explicit certification command requires
the matching pilot run plus rendered-QA evidence before enabling batch use.

`SHEET_VERIFIED` is accepted as a migration alias for `TRACKER_VERIFIED`. New state files use v2,
`job_id`, `run_id` and a tracker object. A legacy `row_id` maps to `job_id=sheet:<row_id>`.

GET may retry with bounded backoff. POST must never be retried blindly; reconcile by post ID, slug or
persisted media mapping. Resume only when job/run IDs, task type, client and source lock match.
