#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Release gate: upgrade a database built by the original code (build_reference_db.sh)
# with this fork, then check a fresh install too. Exit 0 only if everything passes.
#
# Usage: run_upgrade_check.sh <ref_dir>      (run from the repository root, venv active or .venv present)
set -euo pipefail

REF=${1:?usage: run_upgrade_check.sh <ref_dir>}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
PG=taiga-upgrade-pg
PORT=${UPGRADE_DB_PORT:-55432}
PG_IMAGE=${PG_IMAGE:-postgres:15}
WORK=$(mktemp -d)

cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

psql_() { docker exec "$PG" psql -U taiga -d "$1" -tA -c "$2"; }
migrate() {
    (cd "$ROOT" && UPGRADE_DB_NAME="$1" UPGRADE_DB_HOST=127.0.0.1 UPGRADE_DB_PORT="$PORT" \
        PYTHONPATH="$ROOT:$HERE" DJANGO_SETTINGS_MODULE=settings_upgrade "$PY" manage.py migrate -v 0)
}
index_oids() { psql_ "$1" "select indexrelid, indexrelid::regclass from pg_index i join pg_class c on c.oid=i.indrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' order by 1"; }
dump_schema() { docker exec "$PG" pg_dump -U taiga -d "$1" --schema-only --no-owner; }

docker rm -f "$PG" >/dev/null 2>&1 || true
docker run -d --name "$PG" -p "$PORT:5432" -e POSTGRES_USER=taiga -e POSTGRES_PASSWORD=taiga -e POSTGRES_DB=taiga "$PG_IMAGE" >/dev/null
until docker exec "$PG" pg_isready -h 127.0.0.1 -U taiga -d taiga >/dev/null 2>&1; do sleep 1; done

echo "== upgrade over the reference database"
docker exec -i "$PG" pg_restore -U taiga -d taiga --no-owner < "$REF/reference.dump"
index_oids taiga > "$WORK/oids.before"
migrate taiga

echo "-- row counts"
while IFS=$'\t' read -r table expected; do
    [ "$table" = django_migrations ] && continue # the fork adds migrations on purpose
    actual=$(psql_ taiga "select count(*) from \"$table\"")
    [ "$actual" = "$expected" ] || { echo "FAIL row count $table: expected $expected, got $actual"; exit 1; }
done < "$REF/rowcounts.tsv"

echo "-- index OIDs (a rename must keep the OID; nothing may be rebuilt)"
index_oids taiga > "$WORK/oids.after"
for oid in $(cut -d'|' -f1 "$WORK/oids.before"); do
    grep -q "^$oid|" "$WORK/oids.after" || { echo "FAIL index with oid $oid was dropped or rebuilt"; exit 1; }
done

echo "-- schema"
dump_schema taiga > "$WORK/upgraded.sql"
"$PY" "$HERE/compare_schema.py" "$REF/reference.schema.sql" "$WORK/upgraded.sql"

echo "== fresh install"
psql_ postgres "create database taiga_fresh" >/dev/null
migrate taiga_fresh
dump_schema taiga_fresh > "$WORK/fresh.sql"
"$PY" "$HERE/compare_schema.py" --fresh "$REF/reference.schema.sql" "$WORK/fresh.sql"
triggers=$(psql_ taiga_fresh "select count(*) from pg_trigger where not tgisinternal")
[ "$triggers" -gt 0 ] || { echo "FAIL no triggers after fresh install (migration 0046)"; exit 1; }
echo "triggers on fresh install: $triggers"

echo "UPGRADE CHECK PASSED"
