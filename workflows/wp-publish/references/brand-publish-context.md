# Brand and publish context

The workflow loads two project-local layers:

1. `projects/<client>/context.md`: brand, voice, language, market and editorial facts.
2. `projects/<client>/publish-context.json`: technical publishing profiles.

The v2 publish context stores `site_key`, optional tracker, timezone and a `content_profiles` object.
Each `blog`, `service-page` or `product` profile has its own endpoint, post type, ready gate, H1
ownership, HTML policy, required fields/capabilities, image policy, SEO adapter and schema hash.

Each profile moves independently:

```text
unconfirmed → pilot-ready → batch-ready
```

- `unconfirmed`: scan evidence exists but the user has not requested/confirmed this type.
- `pilot-ready`: required configuration is confirmed; only one explicit draft pilot is allowed.
- `batch-ready`: that pilot passed REST readback and rendered QA, so normal and batch jobs may run.

Use `scripts/wp_profile_status.py confirm` only when the user requests that content type. Use
`certify` only with the matching verified pilot state and a render report whose post ID and five
checks match. A profile/schema change makes prior batch manifests stale.

`clean_article` permits only explicitly defined safe article cleanup. `preserve_builder` protects
theme/page-builder wrappers and inline behavior. No profile becomes ready from detection alone, and
no content type inherits readiness from another. Do not copy credentials or full brand context here.
