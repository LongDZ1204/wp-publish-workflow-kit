# Read-only site discovery

The first connection runs `wp_site_scan.py` with GET and OPTIONS only. It inventories the current
user, capabilities, REST content types, taxonomies and endpoint schemas. Credentials are never
written to the result.

The scan creates a timestamped evidence folder and a `publish-context.proposed.json`. The proposal
never overwrites active context and every profile starts `status=unconfirmed`, `ready=false`,
`pilot_allowed=false` and `batch_ready=false`.

Do not confirm all profiles during setup. When the user first requests blog, service-page or product,
confirm only that type's endpoint, required fields, taxonomies, H1 ownership, HTML policy, SEO
adapter, image policy and missing capabilities. Ask for the exact missing capability or an
appropriate role change; do not request Administrator by default.
