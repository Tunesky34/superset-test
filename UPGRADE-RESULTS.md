# Superset 4.1.1 → 6.1.0 upgrade results

## Scope and method

The POC uses the Docker Compose deployment in this repository. It keeps the
PostgreSQL metadata volume while changing the Superset container from 4.1.1
to 6.1.0 and running the supported `superset db upgrade` migration command.
The baseline loads Superset-maintained example dashboard and SQLite datasets;
PostgreSQL and MySQL are also seeded with six sample `poc_orders` rows.

The snapshot script records the Superset version and names/counts for
dashboards, charts, datasets, and registered database connections. The
comparison checks that all dashboard/chart/database names and
database-qualified dataset names present before the migration remain after
it. This gives a repeatable metadata-retention check; it does not prove that
every chart query, permission, alert, or production integration works.

## Results

| Check | 4.1.1 baseline | 6.1.0 target |
|---|---:|---:|
| Superset version | 4.1.1 | 6.1.0 |
| Dashboards | 11 | 11 |
| Charts | 120 | 120 |
| Datasets | 26 | 26 |
| Registered databases | 3 | 3 |
| PostgreSQL `poc_orders` rows | 6 | 6 |
| MySQL `poc_orders` rows | 6 | 6 |
| Snapshot comparison | — | **PASS**; no previously listed dashboards, charts, datasets, or databases were lost |

The target image migrated the existing PostgreSQL metadata database
successfully. Both registered sample sources remained queryable from the
Superset 6.1.0 container using its installed PostgreSQL and MySQL drivers.
The `World Bank's Data` example dashboard opened in the browser, and its map,
line, table, and donut charts rendered.

The browser console reported a 404 for `/static/service-worker.js`; this did
not prevent the dashboard or its charts from rendering. Startup also emitted
the expected POC warnings that no Content Security Policy is configured and
that Flask-Limiter uses in-memory storage. These local-only settings must not
be carried into production.

The exact snapshots and comparison inputs are in the ignored local
`artifacts/before.json`, `artifacts/after.json`, and
`artifacts/metadata-before.sql` files. They are generated during the POC and
are not committed.

## Production recommendation

**Do not upgrade production directly from this POC.** First test against a
restored copy of the actual metadata database, configuration, drivers, and
dashboard/query workload. The jump includes two major release boundaries
(5.0 and 6.0), so a clean migration exit alone is insufficient evidence.

Before attempting production:

1. Make and restore-test a full metadata-database backup. Also back up
   uploaded assets, configuration, secrets, and any external files or
   databases used by the deployment.
2. Keep the existing `SECRET_KEY` unchanged. Superset encrypts database
   passwords and other secrets with it; changing it can make stored
   credentials unusable.
   Keep production HTTPS/Talisman enforcement enabled behind the production
   TLS endpoint; only this loopback-only POC disables it for local HTTP.
3. Pin and test a specific Superset image tag and matching Python database
   drivers, and confirm the metadata database engine/version is supported.
   Superset 6.1.0 requires `clickhouse-connect >=0.13.0` for ClickHouse
   connections.
4. Review the official
   [updating notes](https://github.com/apache/superset/blob/6.1.0/UPDATING.md)
   and [6.1.0 changelog](https://github.com/apache/superset/blob/6.1.0/CHANGELOG/6.1.0.md)
   across every release from 4.1.1 to the chosen target. In particular:
   - Superset 6.0 removes Flask-AppBuilder `AUTH_OID`; migrate OID
     authentication to another supported method before upgrading if used.
   - Superset 5.0 removes legacy chart types, including Event Flow and Sankey
     Loop, and migrates other legacy chart types. Inspect impacted dashboards.
   - Superset 6.0 changes environment-tag color values and removes
     `THEME_OVERRIDES`; review custom configuration and themes.
   - Superset 6.1.0 raises the minimum ClickHouse connector version.
   - Superset 6.1.0's MCP service is optional and runs as a separate process;
     enabling it requires the `fastmcp` extra and production JWT
     authentication. An image upgrade alone does not enable AI integrations.
     Redis deployments using the Global Task Framework should also review
     `DISTRIBUTED_COORDINATION_CONFIG` in the updating notes.
5. Upgrade in staging with maintenance mode/write downtime. Run database
   migrations once as a one-shot prestart task, then start web and worker
   processes with the same config and secret key.
6. Smoke-test SSO, RBAC, database connections, SQL Lab, representative
   dashboards/charts/filters, alerts/reports, async queries, and any custom
   plugins or themes. Review Superset and database logs.
7. Roll back by restoring the pre-upgrade metadata backup and deploying the
   old image/config together. Do not point an old image at a database after
   forward migrations have run.

The configuration in this POC is a local approximation, not a production
config diff. Production-specific authentication, custom feature flags,
workers, async query/WebSocket configuration, proxies, and plugin versions
must be compared against the actual deployment before planning cutover.
For MCP configuration and security requirements, follow the versioned
[Superset updating notes](https://github.com/apache/superset/blob/6.1.0/UPDATING.md)
and deploy the MCP process only after its JWT authentication and network
access have been reviewed.
