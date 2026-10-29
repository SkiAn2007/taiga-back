#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Compare two `pg_dump --schema-only` files.

The only accepted difference is an index that kept its definition but got a new
name. With --fresh (a database built by `migrate` from zero versus the original one)
three known differences are accepted as well:

* Django >= 4.1 creates primary keys as IDENTITY columns where Django 3.2 used serial
  (CREATE SEQUENCE / OWNED BY / SET DEFAULT nextval versus ADD GENERATED ... AS IDENTITY).
* references_project<N> sequences: one per project row, so only the reference database that holds sample data has them.
* history_historyentry: the ORM version of migration history 0011 (upstream PR 232) creates
  NOT NULL columns that the original raw SQL left nullable; the models say NOT NULL.

Usage: compare_schema.py [--fresh] <old.sql> <new.sql>   (exit 1 on any other difference)
"""
import re
import sys
from collections import Counter

INDEX = re.compile(r"^(CREATE (?:UNIQUE )?INDEX) (\S+) (ON .*)$")


def _statements(text):
    text = re.sub(r"^--.*$", "", text, flags=re.M)
    text = re.sub(r"^\\(?:un)?restrict.*$", "", text, flags=re.M)  # random token in recent pg_dump
    for raw in text.split(";\n"):
        statement = " ".join(raw.split())
        if statement and not statement.startswith(("SET ", "SELECT pg_catalog.set_config")):
            yield statement.rstrip(";")


IDENTITY_NOISE = re.compile(
    r"^(CREATE SEQUENCE \S+_id_seq .*|CREATE SEQUENCE public\.references_project\d+ .*|ALTER SEQUENCE .*_id_seq OWNED BY .*"
    r"|ALTER TABLE (?:ONLY )?\S+ ALTER COLUMN id (?:SET DEFAULT nextval\(.*|ADD GENERATED .*))$")
KNOWN_FRESH_TABLE = "CREATE TABLE public.history_historyentry "


def _split(text, fresh=False):
    plain, indexes = Counter(), {}
    for statement in _statements(text):
        if fresh and (IDENTITY_NOISE.match(statement) or statement.startswith(KNOWN_FRESH_TABLE)):
            continue
        match = INDEX.match(statement)
        if match:
            indexes.setdefault(match.group(1) + " " + match.group(3), []).append(match.group(2))
        else:
            plain[statement] += 1
    return plain, indexes


def compare(old_text, new_text, fresh=False):
    """Return (problems, renames); renames is a list of (old_name, new_name)."""
    old_plain, old_indexes = _split(old_text, fresh)
    new_plain, new_indexes = _split(new_text, fresh)
    problems = [f"only in old: {s}" for s in (old_plain - new_plain)]
    problems += [f"only in new: {s}" for s in (new_plain - old_plain)]
    renames = []
    for definition in sorted(set(old_indexes) | set(new_indexes)):
        old_names = sorted(old_indexes.get(definition, []))
        new_names = sorted(new_indexes.get(definition, []))
        if len(old_names) != len(new_names):
            problems.append(f"index count differs ({len(old_names)} -> {len(new_names)}): {definition}")
            continue
        renames += [(o, n) for o, n in zip(old_names, new_names) if o != n]
    return problems, renames


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--fresh"]
    problems, renames = compare(open(args[0]).read(), open(args[1]).read(), fresh="--fresh" in sys.argv)
    for old, new in renames:
        print(f"renamed index: {old} -> {new}")
    for problem in problems:
        print(f"DIFFERENCE {problem}")
    sys.exit(1 if problems else 0)
