# Security policy

## Secrets

Use temporary `WP_URL`, `WP_USER`, and `WP_APP_PASS` process variables, or the ignored
`.env.wp-publish` file with mode `0600`. The file is parsed directly; do not source it globally into
the shell. `CLAUDE.local.md` is supported only as a migration fallback and should not hold new
secrets because AI runtimes may load it as instruction context.
Never commit Application Passwords, OAuth tokens, cookies, Google service-account JSON, or Basic Auth
headers.

Project bundles may contain unpublished content, source revisions, post IDs, media IDs and absolute
local paths. Keep runtime `projects/` data out of a public repository.

If a credential is committed, revoke it at the provider first, then remove it from Git history. A
follow-up commit that only deletes the visible secret is not sufficient.

## Reporting

Report security issues privately to the repository owner. Do not include live credentials or client
content in an issue, pull request, screenshot, or test fixture.
