# Public taiga-back fork on current dependencies: design

Date: 2026-10-29. Status: draft for owner approval.

## Intent and why

Upstream `taiga-back` still pins `Django>=3.2.19,<4`. Django 3.2 has been out of
support since April 2024 (upstream issue #195), and Python 3.13 already breaks
it (`cgi.parse_header`). Upstream maintainers are active (last push 2026-10-27)
but have left both upgrade PRs (#229 Django 5.2, #232 Django 6) open without a
single comment.

The owner wants a **public fork** that runs on current dependencies. It is a
research project: the goal is to learn how far the upgrade goes and to publish a
usable result, not to follow a release schedule. Other people should be able to
install it, so tests, CI and upgrade notes are part of the product.

## Goals

1. Run on **Django 6.1** and the Python versions it supports (3.12+) with all
   tests green in CI.
2. **Upgrade in place over an existing Taiga 6.x database.** A person with a
   working original `taiga-back` replaces the backend, runs migrations, and
   keeps all data. This is the most important requirement.
3. Update every dependency to its current release where the code allows it.
4. Replace `index_together` with `Meta.indexes` and ship the migration that
   makes this safe on existing databases.
5. Keep the HTTP API and data formats compatible with the original `taiga-front`.
6. Document the upgrade path (README/CHANGELOG, requirements, PostgreSQL and
   Python minimums).

## Non-goals

- New Taiga features or behaviour changes.
- Django 5.2 LTS support as a separate target (superseded by the decision below).
- Supporting Python or PostgreSQL versions that Django 6.1 itself drops.
- Rewriting working code for style.

## Anti-goals (a failure even if the tests pass)

- Migrations that lose or silently change data on an existing database.
- Rewriting, squashing or deleting existing migration files so that the history
  no longer matches the original project. New migrations are added on top.
- Index changes that rebuild large indexes (long locks) when a rename is enough.
- Breaking the API contract used by `taiga-front`.

## Decisions made by the owner

- Base the fork on **upstream PR #232** ("Upgrade Django to 6 and refactor
  dependencies and tests"), which brings Django 6.0 (pinned `>=6,<6.1`), `psycopg` 3, Python 3.12,
  the `STORAGES` setting, `iterator(chunk_size=...)`, replacement of
  `django.utils.baseconv`, `datetime.timezone.utc` and a CI update.
  This overrides two earlier statements in the conversation: the 5.2 LTS target
  and the deferral of psycopg3. Both now ride along with #232 as is.
- On top of #232: raise Django from 6.0 to **6.1** (the owner's addition after
  the first draft), add the `index_together` -> `Meta.indexes` replacement with its
  migration, and update all dependencies.
- The result is published as a public fork.

## Facts about the starting point (checked 2026-10-29)

- PR #232 head is 20 commits ahead of and 43 behind upstream `main`. A trial
  merge into current `main` gives exactly one conflict, in `docker/Dockerfile`
  (`main` added `WORKDIR /taiga-back` and changed the "Get the code" block).
- #232 rewrites four old migrations from raw SQL to the ORM:
  `projects/migrations/0030_auto_20151128_0757.py`,
  `projects/migrations/0046_triggers_to_update_tags_colors.py`,
  `projects/history/migrations/0011_auto_20160629_1036.py`,
  `projects/votes/migrations/0002_auto_20150805_1600.py`.
  Existing databases have already applied them, so they do not re-run there;
  only fresh installs execute the new code.
- #232 has no new migration for the `index_together` change.
- `index_together` appears in 11 files. `providing_args` appears in 3,
  `NullBooleanField` in `taiga/base/api/serializers.py:728`.
- 241 migrations, 119 test files. CI runs Python 3.10 on PostgreSQL 13 and the
  Docker image is `python:3.11-slim`; both need raising for Django 6.0.
- Pins that are still old in #232: `bleach<6` (the code in `mdrender/service.py`
  uses module-level `ALLOWED_TAGS`/`ALLOWED_ATTRIBUTES` removed in bleach 6),
  `psd-tools<1.10` (1.26 needs Python >=3.11), `asana<4` (v4 is a full rewrite
  that touches the Asana importer), `rudder-sdk-python==1.0.0b1` (a pre-release;
  2.1.9 exists).
- Third-party libraries from the original Kaleidos stack:
  - `django-sampledatahelper` 0.5: `register.py:47` uses
    `models.NullBooleanField` and `model_helper.py` imports
    `FieldDoesNotExist` from `django.db.models.fields`; both are gone, so it
    will not import. It is used only by `sample_data` management command.
  - `djmail` 2.0.0, `django-sites` 0.11, `django-sr` 0.0.4, `django-jinja`
    2.11.0 (declares up to Django 4.2), `serpy` 0.3.1: no removed API found by
    grep, but untested on Django 6.
  - Already fine: `django-picklefield` 3.4.0, `easy-thumbnails` 2.10.1,
    `django-pglocks` 2.1.0, `django-ipware` 8.0.0.
- Plugins (`taiga-contrib-github-auth`, `-gitlab-auth`, `-slack`, `-protected`):
  `requirements-contribs.in` pins tag `6.10.2`, which does not exist upstream
  (latest is `6.10.0`); `requirements-contribs.txt` pins `6.8.0`.
  Compatibility with Django 6 is unverified.

## Constraints

- Licence is MPL-2.0 with a DCO sign-off requirement (`DCOLICENSE`); the fork
  keeps both and keeps the file headers.
- Django 6.1 requires Python 3.12+ and a newer PostgreSQL minimum than 13; the
  builder confirms exact minimums from the Django 6.1 release notes before
  writing them into docs and CI. (The #232 description says Python 3.10+ and
  PostgreSQL 12+, which looks wrong.)

## What the builder must do

1. Create the working branch from current upstream `main` containing the #232
   commits, resolving the `docker/Dockerfile` conflict. Rebase versus merge is
   the builder's call.
2. Bump Django to 6.1: change the pin, run the suite with
   `-W error::DeprecationWarning`, and fix everything removed or deprecated
   between 6.0 and 6.1 (release notes are the source).
3. Finish the `index_together` removal. For every affected model, produce a
   migration that **renames** the existing database index
   (`RenameIndex(..., old_fields=...)`) instead of dropping and recreating it,
   then confirm `makemigrations --check` is clean.
4. Fix `NullBooleanField` in `taiga/base/api/serializers.py` and other leftovers
   found by running the app on Django 6.
5. Update dependencies and handle the code changes that come with them
   (bleach 6 in `mdrender`, asana importer, rudder SDK, psd-tools).
6. For each Kaleidos library that fails on Django 6, report the failure with
   evidence and propose fork, replace or vendor. The owner decides per library
   (see open questions).
7. Fix the plugin requirement pins and check the plugins against Django 6.1.
8. Update CI (Python, PostgreSQL versions), the Docker image, README and
   CHANGELOG with an upgrade section.

## Acceptance checks

- Full test suite passes in CI on the new matrix.
- `manage.py makemigrations --check --dry-run` reports no changes.
- **Upgrade test (automated):** build a Taiga 6.x database by running the
  original upstream code with `manage.py sample_data` (the owner's live data is
  small and not shared), run the fork's `manage.py migrate` over it, then confirm row counts of the main tables are
  unchanged, the schema diff against the original is limited to index renames,
  and the original `taiga-front` can log in and open a project.
- A fresh install (empty database, `migrate` from zero) also works, since #232
  changed four historical migrations.
  Compare `pg_dump --schema-only` of that database with one built by the
  original code; differences must be explained (index names only).

## Owner's own check

The owner runs a live Taiga in Docker with a separate database. After
development the owner starts a **second instance** from the fork's Docker image
against a copy of that database and checks by hand that the project behaves as
before. The builder's job is to make that image buildable and the upgrade steps
clear in the README; the builder never touches the live instance or its data.

## Open questions (owner)

- Fork name and where it is hosted (GitHub account/org, repository name).
- Policy for broken Kaleidos libraries (fork, replace, vendor); decided per
  library once the evidence is in.

## Calls made by the author (not decided by the owner)

- Use `RenameIndex(old_fields=...)` for index migrations.
- Pin plugins to `6.10.0`, the newest existing tag.
- Treat `django-sampledatahelper` as dev-only: do not let it block the release.
- Require the upgrade-over-existing-database test as a release gate.
- If a dependency has no release supporting Django 6.1 yet, hold it at the
  newest version that works and record it in the CHANGELOG instead of blocking.
- Dependency updates are best effort and never block the release. A library
  that cannot be moved stays on its newest working version, with the reason in
  the CHANGELOG. A broken Kaleidos library is vendored in-tree as a stopgap so
  work continues; the owner can still choose fork or replace later.
- `bleach` 6: update the sanitizer in `mdrender` and add golden-file tests that
  compare rendered HTML before and after; any difference is justified in the PR.
- `asana`: upgrade to 4+/5.x only if the importer can be tested against a mocked
  API; otherwise keep `asana<4` and document it. `rudder-sdk-python`: move to
  2.x with a smoke test. `psd-tools`: move to the current release.
- CI matrix: Python 3.12 to the newest version Django 6.1 supports, PostgreSQL
  at Django 6.1's minimum and the newest stable (18, as in open PR #266).
- Strip Kaleidos-specific image publishing and secrets-dependent CI jobs. README
  and install URLs get placeholders until the fork host is known.
- Plugins: verify and document compatibility; patch a plugin only if the fix is
  trivial, and record it as a separate fork pin.
- Keep #232's rewritten historical migrations, verified by the schema
  comparison above.
- The `taiga-front` login check is manual.
