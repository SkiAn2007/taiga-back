# taiga-back Django 6.1 fork Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring branch `django6-work` (upstream `main` + PR #232) to Django 6.1 with all dependencies updated and an upgrade path that works in place over an existing Taiga 6.x database.

**Architecture:** Start from the green-or-not baseline of `django6-work`, bump Django to 6.1, then fix breakage in small tasks, each with its own test. Index changes ship as `RenameIndex(old_fields=...)` migrations so existing databases are renamed, not rebuilt. A scripted upgrade check (original code + `sample_data` -> fork `migrate`) is the release gate.

**Tech Stack:** Python 3.12+, Django 6.1, `psycopg` 3, PostgreSQL, pytest (`pytest.ini`, settings `tests.config`), Docker, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-29-django-upgrade-fork-design.md`

## Global Constraints

- Target Django **6.1**; Python 3.12+; exact Python/PostgreSQL minimums copied from the Django 6.1 release notes (Task 1 records them).
- `psycopg` 3 stays (from #232); no return to `psycopg2`.
- Existing migration files are never edited, squashed or deleted beyond what #232 already changed; new migrations are added on top.
- Index changes rename existing indexes; they do not drop and recreate them.
- API and data formats stay compatible with the original `taiga-front`.
- Licence MPL-2.0, keep file headers; commits use `git commit -s` (DCO, see `DCOLICENSE`).
- Dependency updates are best effort and never block the release; a library that cannot move stays on its newest working version with the reason in `CHANGELOG.md`.
- Never touch the owner's live Taiga instance or its data.

## Review Focus

- Populated database: `migrate` over rows from a 6.x dump keeps every table's row count and does not change the OID of renamed indexes (Task 7, Task 9).
- Empty database: `migrate` from zero succeeds and the tag-colour triggers from migration `0046` still exist afterwards (Task 9).
- `bleach` 6 sanitising Markdown with `<script>`, `<img onerror=...>` and `javascript:` links gives the same output as before (Task 5).
- `import taiga.importers.asana` and the other importers still import when the `asana` pin is kept or changed (Task 6).
- The Docker image builds and `manage.py check` passes inside it with no network at run time (Task 10).

---

### Task 1: Baseline on `django6-work`

**Files:**
- Create: `docs/superpowers/notes/baseline-2026-10-29.md`

**Interfaces:**
- Produces: the list of failing tests and the Django 6.1 / Python / PostgreSQL minimums, used by Tasks 3-6 and 10.

- [ ] **Step 1:** Read the Django 6.1 release notes and write the supported Python versions, minimum PostgreSQL, and removed/deprecated APIs relevant to this codebase into the notes file.
- [ ] **Step 2:** Start PostgreSQL at the version from Step 1 in Docker (`open -a Docker` first if it is stopped); create venv with `python3.12 -m venv .venv && .venv/bin/pip install -r requirements-devel.txt -r requirements-contribs.txt`.
- [ ] **Step 3:** Run `.venv/bin/pytest -x -q -p no:cacheprovider` unchanged on the branch; record failures by file in the notes file.
- [ ] **Step 4:** Commit: `git add docs/superpowers/notes && git commit -s -m "docs: baseline test results for django6-work"`.

### Task 2: Reference "6.x" database from original code

**Files:**
- Create: `scripts/upgrade-check/build_reference_db.sh`

**Interfaces:**
- Produces: `build_reference_db.sh <out_dir>` writes `<out_dir>/reference.dump` (`pg_dump -Fc`), `<out_dir>/reference.schema.sql` (`pg_dump --schema-only`) and `<out_dir>/rowcounts.tsv` (table, count); Task 9 consumes all three.

- [ ] **Step 1:** Script checks out upstream `main` (`git worktree add`), creates its own venv with Python 3.12 and the original `requirements.txt` (Django 3.2 needs Python <= 3.12), creates an empty database, runs `manage.py migrate` and `manage.py sample_data`.
- [ ] **Step 2:** Run it: `scripts/upgrade-check/build_reference_db.sh /tmp/taiga-ref`. Expected: three files, `rowcounts.tsv` shows projects, user stories, tasks, attachments with non-zero counts.
- [ ] **Step 3:** Commit script only (not the outputs): `git add scripts/upgrade-check && git commit -s -m "chore: script to build reference 6.x database"`.

### Task 3: Bump Django to 6.1

**Files:**
- Modify: `requirements.in`, `requirements.txt`, `settings/common.py`, plus whatever the sweep finds.

**Interfaces:**
- Consumes: the baseline notes from Task 1.
- Produces: a branch where `manage.py check` passes on Django 6.1.

- [ ] **Step 1:** Change `Django>=6,<6.1` to `Django>=6.1,<6.2` in `requirements.in`; regenerate `requirements.txt` with `pip-compile` (as the file header says) and install.
- [ ] **Step 2:** Run `.venv/bin/python -W error::DeprecationWarning manage.py check` and `.venv/bin/pytest -x -q -W error::DeprecationWarning`; expected: failures only from removed/deprecated APIs.
- [ ] **Step 3:** Fix each failure at its source, one commit per cause. Re-run until Step 2 is green. Keep the `filterwarnings` entries in `pytest.ini` that are still needed and delete obsolete ones.
- [ ] **Step 4:** Commit: `git commit -s -m "chore: upgrade to Django 6.1"`.

### Task 4: Remaining `NullBooleanField` and removed-API leftovers

**Files:**
- Modify: `taiga/base/api/serializers.py:728`
- Test: `tests/unit/test_django_compat.py`

- [ ] **Step 1:** Write `test_serializer_field_mapping_has_no_removed_fields`: iterate `serializers.ModelSerializer.field_mapping` and assert every key is an attribute of `django.db.models` (fails on `NullBooleanField`).
- [ ] **Step 2:** Run `pytest tests/unit/test_django_compat.py -v`; expected FAIL.
- [ ] **Step 3:** Remove the `models.NullBooleanField: BooleanField` entry; `BooleanField(null=True)` already maps through `models.BooleanField`.
- [ ] **Step 4:** Run the test; expected PASS. Commit.

### Task 5: `bleach` 6 with golden-file tests

**Files:**
- Modify: `taiga/mdrender/service.py`, `taiga/auth/serializers.py`, `taiga/users/validators.py`, `requirements.in`
- Create: `tests/unit/mdrender/golden/` (input `.md` + expected `.html` pairs), `tests/unit/mdrender/test_sanitizer_golden.py`

**Interfaces:**
- Produces: `render(project, text) -> str` unchanged in signature.

- [ ] **Step 1:** With the **old** `bleach<6` still installed, generate the golden pairs from cases: plain Markdown, tables, task lists, `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, `[x](javascript:alert(1))`, inline SVG, emoji, mentions. Commit the pairs.
- [ ] **Step 2:** Write `test_render_matches_golden` parametrised over the pairs; run it on the old bleach: PASS.
- [ ] **Step 3:** Set `bleach>=6,<7`; adapt `mdrender/service.py` to bleach 6 (module-level `ALLOWED_TAGS`/`ALLOWED_ATTRIBUTES` are now `bleach.sanitizer.ALLOWED_*` or passed explicitly). Run the test; any golden difference must be either fixed or recorded in `CHANGELOG.md` with a reason.
- [ ] **Step 4:** Check the two other `bleach` users still behave: `pytest tests -k "auth or users" -q`. Commit.

### Task 6: Update the other dependencies

**Files:**
- Modify: `requirements.in`, `requirements.txt`, `requirements-devel.in`, `requirements-devel.txt`, `requirements-tests.txt`, `taiga/importers/asana/`

- [ ] **Step 1:** Remove every cap whose reason was Django 3.2 (`django-picklefield`, `easy-thumbnails`, `psd-tools` to the current release, `rudder-sdk-python` to 2.x). Regenerate lock files.
- [ ] **Step 2:** Run the full suite; fix breakage per library, one commit each. For `rudder-sdk-python` add one smoke test that the analytics client can be constructed with a dummy key and `track` is callable.
- [ ] **Step 3:** `asana`: write a test with a mocked client that exercises the Asana importer's project listing. If it can be written against `asana` 5.x, upgrade; if not, restore `asana<4` and add the reason to `CHANGELOG.md`.
- [ ] **Step 4:** `pip list --outdated` in the venv must list only deliberately held packages; list them in `CHANGELOG.md`. Commit.

### Task 7: Replace `index_together` with renaming migrations

**Files:**
- Modify: `taiga/projects/models.py`, `taiga/projects/custom_attributes/models.py`, `taiga/projects/attachments/models.py`, `taiga/timeline/models.py` (check; these are the models whose `Meta` carried `index_together` or `indexes` in upstream `main`)
- Create: one new migration per app, e.g. `taiga/projects/migrations/00NN_rename_index_together.py`
- Test: `tests/integration/test_index_migrations.py`

**Interfaces:**
- Consumes: reference database from Task 2.
- Produces: migrations using `migrations.RenameIndex(model_name=..., new_name=..., old_fields=(...))`.

- [ ] **Step 1:** Write `test_no_pending_model_changes`: `call_command("makemigrations", "--check", "--dry-run")` raises no `SystemExit`. Write `test_renamed_index_keeps_oid`: load the reference dump, record `pg_class.oid` for each affected index, run the new migrations, assert OIDs are equal and `pg_indexes.indexname` equals the new `Meta.indexes` name.
- [ ] **Step 2:** Run both; expected FAIL (migrations missing).
- [ ] **Step 3:** For each model, give each `models.Index` an explicit `name` (stable, <=30 chars) and generate the migration with `makemigrations`; replace any generated `RemoveIndex`/`AddIndex` pair with `RenameIndex(..., old_fields=...)`.
- [ ] **Step 4:** Run both tests; expected PASS. `sqlmigrate` output for each new migration must contain `ALTER INDEX ... RENAME TO` and no `CREATE INDEX`. Commit.

### Task 8: Kaleidos libraries and plugins

**Files:**
- Modify: `requirements.in`, `requirements-contribs.in`, `requirements-contribs.txt`, `settings/common.py`
- Create (only if needed): `vendor/<lib>/` with the patched package and its licence

- [ ] **Step 1:** In the venv, `python -c "import django_sites, djmail, sr, sampledatahelper, django_jinja, serpy"` and `manage.py check`; record which fail and why in `docs/superpowers/notes/libs-2026-10-29.md`.
- [ ] **Step 2:** For each failure, vendor the minimal patch in-tree (spec stopgap) and add a test that imports it. For `django-sampledatahelper` the patch is `NullBooleanField` and `FieldDoesNotExist`; verify with `manage.py sample_data` on an empty database.
- [ ] **Step 3:** Set plugin pins in both contribs files to `6.10.0` (the newest existing tag); install and import all four; record compatibility in the notes file. Patch a plugin only if the fix is trivial.
- [ ] **Step 4:** Commit.

### Task 9: Upgrade check against the reference database

**Files:**
- Create: `scripts/upgrade-check/run_upgrade_check.sh`, `scripts/upgrade-check/compare_schema.py`

**Interfaces:**
- Consumes: outputs of `build_reference_db.sh` (Task 2), migrations from Task 7.
- Produces: exit code 0 only when all checks pass.

- [ ] **Step 1:** `run_upgrade_check.sh <ref_dir>` restores `reference.dump` into a fresh database, runs the fork's `manage.py migrate`, and compares row counts against `rowcounts.tsv` (must be equal for every table that existed before).
- [ ] **Step 2:** `compare_schema.py <ref_schema.sql> <new_schema.sql>` prints the differing objects; the script accepts only index renames and new objects from migrations added after the reference version and fails on anything else.
- [ ] **Step 3:** Second mode `--fresh`: `migrate` on an empty database, assert the triggers from migration `0046` exist (`pg_trigger`) and compare its schema to the reference schema with the same rules.
- [ ] **Step 4:** Run both modes; expected exit 0. Save the output under `docs/superpowers/notes/upgrade-check-2026-10-29.md`. Commit.

### Task 10: CI, Docker image, docs

**Files:**
- Modify: `.github/workflows/tests-and-coverall.yml`, `docker/Dockerfile`, `README.md`, `CHANGELOG.md`, `tox.ini`

- [ ] **Step 1:** CI matrix: Python 3.12 to the newest version Django 6.1 supports; PostgreSQL at the Task 1 minimum and 18. Remove image publishing and Kaleidos-secret jobs.
- [ ] **Step 2:** Add an `upgrade-check` CI job that runs Tasks 2 and 9 scripts.
- [ ] **Step 3:** `docker build -f docker/Dockerfile -t taiga-back-django6 .`; run `docker run --rm taiga-back-django6 python manage.py check`. Expected: "System check identified no issues".
- [ ] **Step 4:** README gets an "Upgrading from upstream 6.x" section: back up the database, replace the image, run `manage.py migrate`; state Python/PostgreSQL minimums; `CHANGELOG.md` lists every held dependency and behaviour difference.
- [ ] **Step 5:** Commit, push `django6-work` to `fork`, and write the owner's runbook (second instance on a copy of the database) at the end of the README section.

---

## Self-review notes

- Spec coverage: goals 1-6 map to Tasks 3, 7+9, 5+6+8, 7, 4+8, 10; acceptance checks map to Tasks 9 and 10; owner's own check is the runbook in Task 10.
- Open spec items kept open: fork host (README uses `SkiAn2007/taiga-back` URLs until the owner decides), per-library final policy (Task 8 vendors as a stopgap).
