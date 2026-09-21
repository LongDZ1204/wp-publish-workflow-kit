# __CLIENT_SLUG__ publish context

Site-specific decisions for workflow `wp-publish`. Keep brand/business facts in `context.md`.

After the read-only site scan, confirm these fields separately for blog, service page and product:

- WordPress endpoint and post type;
- required fields/taxonomies;
- body H1 ownership;
- HTML cleanup/preservation policy;
- SEO meta adapter;
- image policy;
- exact required capabilities.

Do not confirm unused profiles during setup. When a type is first requested, confirm it just in time,
run one draft pilot, verify REST and rendered output, then certify only that type as `batch-ready`.
