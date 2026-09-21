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

Each item folder uses `intake/`, `assets/original/`, `assets/prepared/`, `bundle/`, `backups/` and
`runs/`; the exact tree is documented in the generated `content/README.md`. Keep content, images and
evidence with their project and content type. Skills, workflows and deterministic tools remain
shared at repository level. All site credentials remain together in the root gitignored
`.env.wp-publish`, parsed directly with mode `0600` and never sourced into the shell.

Scaffolding is non-destructive. A legacy `knowledge/publish-context.json` is reported and preserved;
it is not silently migrated or overwritten.
