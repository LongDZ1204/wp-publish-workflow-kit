---
name: wp-rest-publish
description: Safely update one existing WordPress post from a fresh content.raw snapshot using exact minimal edits, an immutable backup, operator approval, a REST write, and live readback. Use only for the AUDIT route; do not use to create a new post.
---

# WordPress REST update

Update the content of one existing WordPress post while preserving all untouched HTML, blocks,
shortcodes, tables, embeds, and media references.

## Invariants

- Fetch a fresh `content.raw` snapshot before editing.
- Store an immutable backup before any write.
- Build exact `{old, new}` replacements; every `old` value must match once.
- Preserve frozen passages and structural element counts.
- Keep exactly one source H1 in the WordPress body.
- Stop when WordPress returns HTML, a challenge page, an unexpected status, or ambiguous state.
- Require explicit approval for the exact prepared artifact.
- Re-fetch after the write and verify both changed and frozen content.
- Never create a post; this skill only updates a known existing post.

## Credentials

Use a dedicated WordPress Editor account. Do not use Administrator. Run the interactive setup from
the repository root; the operator enters the Application Password in a hidden terminal prompt:

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py \
  --site-key '<site-key>' --url 'https://example.com' --user 'wp-publish'
```

Temporary environment variables are an advanced alternative:

```bash
export WP_URL='https://example.com'
export WP_USER='api-user'
export WP_APP_PASS='application-password'
```

The setup script writes the repository-ignored `CLAUDE.local.md` with mode `0600`. Never ask the user
to paste an Application Password into chat or put it directly in a reusable command or log.

## Run sequence

From the repository root:

```bash
python3 skills/wp-rest-publish/scripts/wp_fetch.py \
  --site '<site-key>' --slug '<slug>' --out '<workdir>' \
  --backup 'projects/<client>/content/_audit-snapshots'

python3 skills/wp-rest-publish/scripts/wp_apply_edits.py \
  --html '<workdir>/<post>.raw.html' --edits edits.json \
  --frozen frozen.json --dry-run

python3 skills/wp-rest-publish/scripts/wp_apply_edits.py \
  --html '<workdir>/<post>.raw.html' --edits edits.json \
  --frozen frozen.json --out '<workdir>/new.html'
```

Show the operator the diff summary and verification plan. After approval, push and verify:

```bash
python3 skills/wp-rest-publish/scripts/wp_push_verify.py \
  --site '<site-key>' --id '<post-id>' --html '<workdir>/new.html' \
  --seo-adapter '<yoast|rankmath>' --seo-title '<SEO title>' \
  --meta-description '<meta description>' \
  --expect 'new passage' --keep 'frozen passage'
```

Read `references/wp-rest-notes.md` for Gutenberg blocks, media behaviour, authentication errors,
revision handling, and cache-delayed public verification.
