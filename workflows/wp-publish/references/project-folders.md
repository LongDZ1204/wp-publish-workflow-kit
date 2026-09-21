# Standard project folders

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

Each item folder may contain `intake/`, `assets/`, `bundle/`, `backups/` and `runs/`. Keep content,
images and evidence with their project and content type. Skills, workflows and deterministic tools
remain shared at repository level. All site credentials remain together in the root gitignored
`.env.wp-publish`, parsed directly with mode `0600` and never sourced into the shell.

Scaffolding is non-destructive. A legacy `knowledge/publish-context.json` is reported and preserved;
it is not silently migrated or overwritten.
