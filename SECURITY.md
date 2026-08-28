# Security policy

## Secrets

Use `WP_URL`, `WP_USER`, and `WP_APP_PASS` environment variables, or an ignored local credential file.
Never commit Application Passwords, OAuth tokens, cookies, Google service-account JSON, or Basic Auth
headers.

Project bundles may contain unpublished content, source revisions, post IDs, media IDs and absolute
local paths. Keep runtime `projects/` data out of a public repository.

If a credential is committed, revoke it at the provider first, then remove it from Git history. A
follow-up commit that only deletes the visible secret is not sufficient.

## Reporting

Report security issues privately to the repository owner. Do not include live credentials or client
content in an issue, pull request, screenshot, or test fixture.
