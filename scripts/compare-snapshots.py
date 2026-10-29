#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def read_snapshot(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read snapshot {path}: {error}") from error


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {sys.argv[0]} BEFORE.json AFTER.json")
    before = read_snapshot(sys.argv[1])
    after = read_snapshot(sys.argv[2])

    missing = []
    for key in ("dashboards", "charts", "datasets", "databases"):
        previous = set(before.get(key, []))
        current = set(after.get(key, []))
        lost = sorted(previous - current)
        previous_count = before.get(key + "_count", len(previous))
        current_count = after.get(key + "_count", len(current))
        print(
            f"{key}: {previous_count} -> {current_count}"
        )
        if lost:
            missing.append((key, lost))
        if current_count < previous_count:
            missing.append((key, [f"count decreased by {previous_count - current_count}"]))

    print(f"Superset: {before.get('superset_version')} -> {after.get('superset_version')}")
    if missing:
        for key, names in missing:
            print(f"Missing {key}: {', '.join(names)}")
        raise SystemExit(1)
    print("PASS: no previously listed dashboards, charts, datasets, or databases were lost")


if __name__ == "__main__":
    main()
