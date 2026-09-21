# Brand and publish context

The workflow loads two project-local layers:

1. `projects/<client>/context.md`: brand, voice, language, market and editorial facts.
2. `projects/<client>/publish-context.json`: technical publishing profiles.

The v2 publish context stores `site_key`, optional tracker, timezone and a `content_profiles` object.
Each `blog`, `service-page` or `product` profile has its own endpoint, post type, ready gate, H1
ownership, HTML policy, required fields/capabilities, image policy, SEO adapter and schema hash.

`clean_article` permits only explicitly defined safe article cleanup. `preserve_builder` protects
theme/page-builder wrappers and inline behavior. No profile becomes ready from detection alone; the
user confirms it once for that content type. Do not copy credentials or full brand context here.
