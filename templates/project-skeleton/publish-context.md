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

Only a confirmed content profile may be changed to `ready=true` in `publish-context.json`.
