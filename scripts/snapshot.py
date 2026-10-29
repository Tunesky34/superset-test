#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OBJECTS = {
    "dashboards": ("dashboard", "dashboard_title"),
    "charts": ("chart", "slice_name"),
    "datasets": ("dataset", "table_name"),
    "databases": ("database", "database_name"),
}


def load_dotenv():
    env_file = ROOT / ".env"
    if not env_file.exists():
        raise SystemExit("Missing .env; copy .env.example to .env first")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def request_json(url, token=None, body=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except (HTTPError, URLError) as error:
        detail = error.read().decode(errors="replace") if isinstance(error, HTTPError) else str(error)
        raise RuntimeError(f"Request failed for {url}: {detail}") from error


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"before", "after"}:
        raise SystemExit(f"Usage: {sys.argv[0]} before|after")

    load_dotenv()
    api = os.environ.get("SUPERSET_URL", "http://localhost:8088")
    login = request_json(
        f"{api}/api/v1/security/login",
        body={
            "username": os.environ.get("ADMIN_USERNAME", "admin"),
            "password": os.environ.get("ADMIN_PASSWORD", "local-admin-change-me"),
            "provider": "db",
            "refresh": True,
        },
    )
    token = login.get("access_token")
    if not token:
        raise RuntimeError("Superset login response did not contain an access token")

    snapshot = {}
    for key, (endpoint, name_field) in OBJECTS.items():
        response = request_json(
            f"{api}/api/v1/{endpoint}/?q=(page:0,page_size:1000)", token=token
        )
        results = response.get("result")
        if not isinstance(results, list):
            raise RuntimeError(f"Unexpected {endpoint} API response: missing result list")
        if key == "datasets":
            names = []
            for item in results:
                table_name = item.get(name_field)
                if table_name is None:
                    continue
                database = item.get("database")
                if isinstance(database, dict):
                    database_name = database.get("database_name", str(database.get("id", "")))
                else:
                    database_name = str(database or item.get("database_id", ""))
                names.append(
                    ".".join(
                        part
                        for part in (database_name, item.get("schema"), table_name)
                        if part
                    )
                )
            snapshot[key] = sorted(names)
        else:
            snapshot[key] = sorted(
                item[name_field] for item in results if item.get(name_field) is not None
            )
        snapshot[f"{key}_count"] = response.get("count", len(results))

    version = subprocess.run(
        ["docker", "compose", "exec", "-T", "superset", "superset", "version"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    version_output = re.sub(r"\x1b\[[0-9;]*m", "", version.stdout)
    version_match = re.search(r"\bSuperset\s+(\d+\.\d+\.\d+)\b", version_output)
    if not version_match:
        raise RuntimeError(
            f"Could not identify Superset version in CLI output: {version_output}"
        )
    snapshot["superset_version"] = version_match.group(1)

    output_dir = ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{sys.argv[1]}.json"
    output_file.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"Saved {output_file.relative_to(ROOT)}")
    for key in OBJECTS:
        print(f"{key}: {snapshot[f'{key}_count']}")
    print(snapshot["superset_version"])


if __name__ == "__main__":
    main()
