# Setup

This is the manual setup path for maintainers. New users should give the repository URL to Codex and
follow [`huong-dan-nguoi-moi.md`](huong-dan-nguoi-moi.md).

## 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

## 2. Configure WordPress credentials

Use a dedicated WordPress Editor account. Editor can upload media and update published posts created
by other users; Administrator is broader than this workflow needs.

Preferred interactive setup:

```bash
python3 workflows/wp-publish/scripts/wp_setup_credentials.py \
  --site-key example-site --url https://example.com --user wp-publish
```

The script reads the Application Password through a hidden terminal prompt, verifies the account and
required capabilities, refuses Administrator, then stores the credential in ignored
`CLAUDE.local.md` with file mode `0600`.

Environment variables remain available for a temporary advanced session:

```bash
export WP_URL="https://example.com"
export WP_USER="wordpress-user"
export WP_APP_PASS="application-password"
```

The generated local-file format is:

```markdown
### Example WordPress (REST API)
- URL: https://example.com
- User: wordpress-user
- App Password: application-password
```

Never put these values in the Sheet or project context.

## 3. Create a project

```bash
mkdir -p projects/example-client
cp templates/context.example.md projects/example-client/context.md
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client example-client
cp templates/publish-context.example.json projects/example-client/knowledge/publish-context.json
```

Complete the brand context and site policy. Keep `ready=false` until all required integrations have
been tested. A one-time pilot is allowed only when `pilot_allowed=true` and the operator explicitly
approves the pilot.

Source content must contain exactly one H1. The workflow preserves that H1 in the WordPress body and
the gate stops when the final HTML has zero or multiple H1 elements.

## 4. Configure the Sheet

Use the 11-column contract in [`google-sheet-template.md`](google-sheet-template.md). Bind the Sheet
ID, tab and timezone in the local project publish context. The workflow must update rows by immutable
`Row ID`, never by blind append.

## 5. Configure SEO meta REST

Set `seo_meta_adapter` to `yoast` or `rankmath`. There is no separate SEO-plugin REST password; use
the WordPress Application Password above. If the two plugin meta fields are not registered with
`show_in_rest`, install the matching file from `snippets/` through a site-specific plugin, WPCode or
Code Snippets, then verify the REST schema and a staging round-trip.

## 6. Run checks

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 scripts/check_distribution.py
```

## 7. Publishing boundary

- NEW is always created as a WordPress draft.
- AUDIT must use a fresh WordPress snapshot and backup.
- The approval hash must match the current bundle immediately before a write.
- A timeout after POST requires GET/reconciliation; never retry blindly.
- Completion requires WordPress and Sheet readback.
