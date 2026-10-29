#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Build a Taiga 6.x reference database with the ORIGINAL upstream code
# (ORIG_REF, default "main"; CI pins the upstream commit the fork started from) and sample_data.
#
# Usage: build_reference_db.sh <out_dir>
# Writes: <out_dir>/reference.dump, reference.schema.sql, rowcounts.tsv
set -euo pipefail

OUT=${1:?usage: build_reference_db.sh <out_dir>}
ORIG_REF=${ORIG_REF:-main}
PG_IMAGE=${PG_IMAGE:-postgres:15}
NET=taiga-ref-net
PG=taiga-ref-pg
IMG=taiga-back-orig
SRC=$(mktemp -d)

mkdir -p "$OUT"
cleanup() {
    docker rm -f "$PG" >/dev/null 2>&1 || true
    docker network rm "$NET" >/dev/null 2>&1 || true
    git worktree remove --force "$SRC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git worktree add --detach "$SRC" "$ORIG_REF" >/dev/null
docker build -q -f "$SRC/docker/Dockerfile" -t "$IMG" "$SRC" >/dev/null

docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" \
    -e POSTGRES_DB=taiga -e POSTGRES_USER=taiga -e POSTGRES_PASSWORD=taiga "$PG_IMAGE" >/dev/null
until docker exec "$PG" pg_isready -h 127.0.0.1 -U taiga -d taiga >/dev/null 2>&1; do sleep 1; done

taiga() {
    docker run --rm --network "$NET" --entrypoint python \
        -e POSTGRES_DB=taiga -e POSTGRES_USER=taiga -e POSTGRES_PASSWORD=taiga -e POSTGRES_HOST="$PG" \
        -e TAIGA_SECRET_KEY=reference-only -e TAIGA_SITES_SCHEME=http -e TAIGA_SITES_DOMAIN=localhost \
        -e CELERY_ENABLED=False -e ENABLE_TELEMETRY=False -e DEBUG=True \
        -e SESSION_COOKIE_SECURE=False -e CSRF_COOKIE_SECURE=False \
        -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_EMAIL=admin@example.com \
        -e DJANGO_SUPERUSER_PASSWORD=reference-only \
        "$IMG" manage.py "$@"
}
taiga migrate
taiga loaddata initial_project_templates
taiga createsuperuser --noinput # sample_data needs a superuser
taiga sample_data

docker exec "$PG" pg_dump -U taiga -d taiga -Fc > "$OUT/reference.dump"
docker exec "$PG" pg_dump -U taiga -d taiga --schema-only --no-owner > "$OUT/reference.schema.sql"
: > "$OUT/rowcounts.tsv"
for t in $(docker exec "$PG" psql -U taiga -d taiga -tAc \
        "select tablename from pg_tables where schemaname='public' order by 1"); do
    printf '%s\t%s\n' "$t" "$(docker exec "$PG" psql -U taiga -d taiga -tAc "select count(*) from \"$t\"")" >> "$OUT/rowcounts.tsv"
done
echo "reference database written to $OUT"
