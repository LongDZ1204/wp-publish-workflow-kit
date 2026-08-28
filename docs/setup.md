# Setup

## 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

## 2. Configure WordPress credentials

Preferred for a temporary session:

```bash
export WP_URL="https://example.com"
export WP_USER="wordpress-user"
export WP_APP_PASS="application-password"
```

The legacy local-file format is also supported in an ignored `CLAUDE.local.md`:

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

## 4. Configure the Sheet

Use the 11-column contract in [`google-sheet-template.md`](google-sheet-template.md). Bind the Sheet
ID, tab and timezone in the local project publish context. The workflow must update rows by immutable
`Row ID`, never by blind append.

## 5. Run checks

```bash
python3 workflows/wp-publish/scripts/wp_selftest.py
python3 scripts/check_distribution.py
```

## 6. Publishing boundary

- NEW is always created as a WordPress draft.
- AUDIT must use a fresh WordPress snapshot and backup.
- The approval hash must match the current bundle immediately before a write.
- A timeout after POST requires GET/reconciliation; never retry blindly.
- Completion requires WordPress and Sheet readback.
