# Batch approval

Batch publishing does not ask for confirmation article by article. Prepare and gate every job first,
then build one manifest containing each job ID, title, route and exact bundle hash:

Before building, every content type present in the batch must have passed its pilot and be marked
`batch-ready`. The manifest binds the current profile hash so a later configuration change stops it.

```bash
python3 workflows/wp-publish/scripts/wp_batch_approval.py build \
  --batch-id batch-2026-001 --bundle path/to/job-a/bundle \
  --bundle path/to/job-b/bundle \
  --profile projects/example-client/publish-context.json \
  --out batch-manifest.json
```

Show the complete summary and `manifest_hash` to the user. After one explicit confirmation for that
hash, run `approve` with `--expected-hash`; it creates a normal per-bundle approval bound to the same
batch. Any changed bundle fails verification and is not authorized.

Execution and readback remain per job. A failed job becomes STOPPED with its own evidence; it does not
silently change or retry another job. Report the final counts and exact failed job IDs.
For AUDIT jobs, the batch verifies the current audit gate before manifest creation/approval and
binds `audit-plan.json` plus `audit-gate-report.json` into that job's approval. A Sheet row never
replaces this per-bundle evidence.
