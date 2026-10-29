# Superset Upgrade Feasibility POC

This repository reproduces the local Docker shape of the production Superset
deployment, starting at Apache Superset 4.1.1 and upgrading the same metadata
database to the latest stable release (6.1.0 as of 2026-10-28). It includes
PostgreSQL metadata storage, Redis, seeded PostgreSQL and MySQL datasets, and
Superset's example SQLite dashboard/data.

## Requirements

- Docker Engine and Docker Compose
- At least 4 GB of free memory for the containers
- Internet access while loading Superset's example data from GitHub

## Start the 4.1.1 baseline

```bash
cp .env.example .env
docker compose up --build -d
docker compose logs -f superset-init
docker compose ps
```

The web UI is at <http://localhost:8088>. The default local login is
`admin` / `local-admin-change-me`; change these values in `.env` before
starting, and set a unique `SUPERSET_SECRET_KEY`. Keep that key unchanged
through the upgrade. The Compose ports bind to loopback for local access. The
PostgreSQL metadata store, a separate `poc_data` PostgreSQL database, a
seeded MySQL `poc_mysql` database, and Superset's SQLite example data are
initialized on first start. The example dashboard uses the SQLite datasets.
Talisman HTTPS enforcement is disabled for this local HTTP-only setup; do not
copy that setting to production. Wait for `superset` to show `healthy` before
registering source databases or using the UI.

Register the PostgreSQL and MySQL data sources and datasets in Superset:

```bash
docker compose exec -T superset python /app/sample-data/register-sources.py
```

This registers `public.poc_orders` from PostgreSQL and `poc_mysql.poc_orders`
from MySQL, in addition to Superset's SQLite example source. These sources
are for local POC use only.

## Record the baseline

With the baseline running, example data loaded, and the PostgreSQL source
registered:

```bash
python3 scripts/snapshot.py before
```

This saves counts for dashboards, charts, datasets, and registered database
connections in `artifacts/before.json`. The `artifacts/` directory is ignored
by Git so that local test results and credentials are not accidentally
committed.

## Upgrade to 6.1.0

Back up the POC metadata database, then stop Superset before changing the
version. The backup is local and ignored by Git:

```bash
mkdir -p artifacts
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > artifacts/metadata-before.sql
docker compose stop superset
```

Keep the metadata volume:

```bash
sed -i 's/^SUPERSET_VERSION=.*/SUPERSET_VERSION=6.1.0/' .env
docker compose build superset-init superset
docker compose up -d
docker compose logs -f superset-init
```

The init job runs `superset db upgrade` against the existing PostgreSQL
metadata database and then starts the web container. Do **not** run
`docker compose down -v`: that deletes the metadata and the point of this POC.
Take a PostgreSQL backup first for a real upgrade.

After the upgraded service is healthy, run:

```bash
python3 scripts/snapshot.py after
python3 scripts/compare-snapshots.py artifacts/before.json artifacts/after.json
```

The comparison exits non-zero if any previously listed object is missing.
Also open the example dashboard in the UI and run this query in SQL Lab
against each registered PostgreSQL and MySQL source:

```sql
SELECT COUNT(*) FROM poc_orders;
```

A name comparison is a retention check, not a substitute for checking
dashboard contents, permissions, scheduled reports, alerts, and
representative queries.

## Results and production recommendation

See [UPGRADE-RESULTS.md](UPGRADE-RESULTS.md) for the recorded POC results,
before/after comparison, risks, and a production upgrade recommendation.

This POC does not upgrade production. The production procedure should begin
with a restorable metadata-database backup and a tested staging copy, then
upgrade the application image and run database migrations as a one-shot
prestart job before starting web/worker processes. Pin an explicit image tag,
keep the same `SECRET_KEY` and metadata database, and roll back by restoring
the backup together with the old image; a downgraded Superset binary cannot
safely use a metadata database after forward migrations.
