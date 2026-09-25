# Standard project folders

The repository includes this structure at `templates/project-skeleton/`. Create a runtime copy with:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_project.py --client example-client
```

```text
projects/<client>/
├── context.md                    # brand/business truth; never overwritten
├── publish-context.md            # human site decisions
├── publish-context.json          # v2 machine profiles
├── scans/<timestamp>/            # immutable read-only scan + proposed profile
└── content/
    ├── blog/<slug>/
    ├── service-page/<slug>/
    └── product/<slug>/
```

Project setup creates the content-type directories, not an item for every future article. When a
job arrives, create one item run:

```bash
python3 workflows/wp-publish/scripts/wp_scaffold_item.py \
  --client example-client --content-type blog --slug article --run-id 2026-09-25-audit-01
```

The exact per-item tree is documented in generated `content/README.md`. Use
`runs/<run-id>/intake/` for the editorial source snapshot; `assets/original/<run-id>/` for supplied
or downloaded image originals; `assets/prepared/<run-id>/` for output images;
`runs/<run-id>/work/` for temporary export/conversion files; `runs/<run-id>/snapshot/` for the
fresh WordPress fetch; `runs/<run-id>/bundle/` for approval, state and readback; and `backups/`
for timestamped pre-update WordPress HTML. The scripts accept explicit paths, so callers must
pass these locations. A new attempt gets a new `run-id`; never reuse a bundle for another job.

Keep content, images and evidence with their project and content type. Shared skills, workflows and
tools remain at repository level. All site credentials remain in root gitignored
`.env.wp-publish`, parsed directly with mode `0600` and never sourced into the shell.

Scaffolding is non-destructive. A legacy `knowledge/publish-context.json` is reported and preserved;
it is not silently migrated or overwritten.
