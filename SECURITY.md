# Security policy

## Secrets

Copy `templates/wp-publish.env.example` once to the ignored root `wp-credentials.env`. Keep a
site-prefixed WordPress block per project and optional Google Sheets service-account JSON in that
single file. Set mode `0600`. The parser reads it directly; do not source it into the shell.
Per-project files, `.env.wp-publish` and temporary process variables remain compatible fallbacks.
`CLAUDE.local.md` is a migration fallback and should not hold new secrets because AI runtimes may
load it as instruction context.
Never commit Application Passwords, OAuth tokens, cookies, Google service-account JSON, or Basic Auth
headers.

Project bundles may contain unpublished content, source revisions, post IDs, media IDs and absolute
local paths. Keep runtime `projects/` data out of a public repository.

If a credential is committed, revoke it at the provider first, then remove it from Git history. A
follow-up commit that only deletes the visible secret is not sufficient.

## Reporting

Report security issues privately to the repository owner. Do not include live credentials or client
content in an issue, pull request, screenshot, or test fixture.
