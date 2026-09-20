---
name: wp-publish
description: Route a Google Sheet row and source document into a safe WordPress NEW draft or AUDIT update with image preparation, approval hash, fail-closed writes, and WordPress plus Sheet readback. Use when asked to publish or update WordPress content through the wp-publish workflow.
---

# WordPress publish workflow

Use this skill as the only entrypoint for Sheet-driven WordPress publishing.

Before every run, read:

1. `../../workflows/wp-publish/CLAUDE.md`
2. `../../workflows/wp-publish/references/bundle-contract.md`
3. `../../workflows/wp-publish/references/sheet-schema.md`
4. `../../workflows/wp-publish/references/state-machine.md`
5. `projects/<client>/context.md`
6. `projects/<client>/knowledge/publish-context.md`

The Sheet declares `NEW` or `AUDIT`; WordPress state only verifies that route. Never switch routes
because a slug exists or is absent.

- `NEW` creates or resumes exactly one WordPress `draft`; it never publishes automatically.
- `AUDIT` updates one existing post from a fresh `content.raw` snapshot and immutable backup.
- Every source document contains exactly one H1. The publish context declares `body_h1_count`: 1 when the body keeps that H1, 0 when the theme renders the post title as the page H1.
- Both routes require `image-onpage` and deterministic `strong-to-b` normalization.
- Any external write requires explicit operator approval for the current bundle hash.
- Completion requires WordPress readback and Google Sheet readback for the same immutable `Row ID`.

Use `../../workflows/wp-publish/scripts/wp_scaffold_project.py` for a new client. Keep credentials in
an ignored local credential file created by `../../workflows/wp-publish/scripts/wp_setup_credentials.py`.
Use a dedicated Editor account and refuse Administrator by default. The user enters the Application
Password only in the script's native masked dialog. Run with `--input-mode dialog`, wait for the
process result, and never ask the user to reply “done” or read terminal output. Use terminal input only
when the dialog is unavailable. Never request the secret in chat or put it in the Sheet, bundle,
project context, logs, command arguments, or Git.
