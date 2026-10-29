import json
import os
import time
from urllib.parse import quote

import requests


base_url = os.environ.get("SUPERSET_URL", "http://localhost:8088")
username = os.environ.get("ADMIN_USERNAME", "admin")
password = os.environ.get("ADMIN_PASSWORD", "local-admin-change-me")
session = requests.Session()

last_connection_error = None
last_status = None
for _ in range(60):
    try:
        health = session.get(f"{base_url}/health", timeout=2)
    except (requests.ConnectionError, requests.Timeout) as error:
        last_connection_error = error
    else:
        if health.ok:
            break
        last_status = health.status_code
    time.sleep(2)
else:
    if last_connection_error:
        raise RuntimeError(
            "Superset did not become reachable within 120 seconds"
        ) from last_connection_error
    raise RuntimeError(f"Superset health endpoint returned HTTP {last_status} for 120 seconds")

login = session.post(
    f"{base_url}/api/v1/security/login",
    json={"username": username, "password": password, "provider": "db", "refresh": True},
    timeout=30,
)
login.raise_for_status()
session.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

csrf = session.get(f"{base_url}/api/v1/security/csrf_token/", timeout=30)
csrf.raise_for_status()
session.headers["X-CSRFToken"] = csrf.json()["result"]

databases_response = session.get(
    f"{base_url}/api/v1/database/", params={"q": "(page:0,page_size:1000)"}, timeout=30
)
databases_response.raise_for_status()
databases = databases_response.json()["result"]


def register_database(name, uri, raw_password):
    database = next(
        (item for item in databases if item.get("database_name") == name), None
    )
    if database is not None:
        return database

    database_response = session.post(
        f"{base_url}/api/v1/database/",
        json={
            "database_name": name,
            "sqlalchemy_uri": uri,
            "expose_in_sqllab": True,
            "allow_run_async": True,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
            "allow_file_upload": False,
            "extra": json.dumps(
                {"metadata_params": {}, "engine_params": {}, "metadata_cache_timeout": {}}
            ),
        },
        timeout=30,
    )
    if not database_response.ok:
        detail = database_response.text
        encoded_password = quote(raw_password, safe="")
        if encoded_password:
            detail = detail.replace(encoded_password, "***")
        if raw_password and raw_password != encoded_password:
            detail = detail.replace(raw_password, "***")
        raise RuntimeError(
            f"Registering {name} failed with HTTP {database_response.status_code}: {detail}"
        )
    database = database_response.json()
    databases.append(database)
    return database


def register_dataset(database, schema):
    datasets_response = session.get(
        f"{base_url}/api/v1/dataset/",
        params={"q": "(page:0,page_size:1000)"},
        timeout=30,
    )
    datasets_response.raise_for_status()
    for item in datasets_response.json()["result"]:
        database_ref = item.get("database")
        if isinstance(database_ref, dict):
            same_database = database_ref.get("id") == database["id"]
        elif isinstance(database_ref, str):
            same_database = database_ref == database["database_name"]
        else:
            same_database = item.get("database_id") == database["id"]
        actual_schema = item.get("schema")
        same_schema = actual_schema == schema or (
            schema == os.environ.get("MYSQL_DATABASE", "poc_mysql")
            and actual_schema in (None, "")
        )
        if (
            same_database
            and item.get("table_name") == "poc_orders"
            and same_schema
        ):
            return

    dataset_response = session.post(
        f"{base_url}/api/v1/dataset/",
        json={
            "database": database["id"],
            "schema": schema,
            "table_name": "poc_orders",
        },
        timeout=30,
    )
    if not dataset_response.ok:
        raise RuntimeError(
            f"Registering {database['database_name']} dataset failed with "
            f"HTTP {dataset_response.status_code}: {dataset_response.text}"
        )


postgres_user = os.environ.get("POSTGRES_USER", "superset")
postgres_password = os.environ.get("POSTGRES_PASSWORD", "local-postgres-change-me")
postgres_uri = (
    f"postgresql+psycopg2://{postgres_user}:{quote(postgres_password, safe='')}"
    f"@{os.environ.get('POSTGRES_HOST', 'postgres')}:5432/poc_data"
)
postgres_database = register_database("POC PostgreSQL", postgres_uri, postgres_password)
register_dataset(postgres_database, "public")

mysql_user = os.environ.get("MYSQL_USER", "superset_data")
mysql_password = os.environ.get("MYSQL_PASSWORD", "local-mysql-change-me")
mysql_uri = (
    f"mysql+mysqldb://{mysql_user}:{quote(mysql_password, safe='')}"
    f"@{os.environ.get('MYSQL_HOST', 'mysql')}:3306/"
    f"{os.environ.get('MYSQL_DATABASE', 'poc_mysql')}"
)
mysql_database = register_database("POC MySQL", mysql_uri, mysql_password)
register_dataset(mysql_database, os.environ.get("MYSQL_DATABASE", "poc_mysql"))

print("Registered POC PostgreSQL and MySQL datasets")
