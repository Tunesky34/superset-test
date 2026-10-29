#!/bin/bash
set -e

echo "Running superset init"
superset db upgrade

if ! superset fab list-users | grep -Fq "${ADMIN_USERNAME:-admin}"; then
  superset fab create-admin \
    --username "${ADMIN_USERNAME:-admin}" \
    --firstname "${ADMIN_FIRSTNAME:-Admin}" \
    --lastname "${ADMIN_LASTNAME:-User}" \
    --email "${ADMIN_EMAIL:-admin@example.com}" \
    --password "${ADMIN_PASSWORD:-changeme}"
fi

superset init
if [[ ! -e /app/superset_home/.poc_examples_loaded ]]; then
  superset load_examples
  touch /app/superset_home/.poc_examples_loaded
fi

echo "Superset init finished"
