# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import ast
import pathlib

TAIGA = pathlib.Path(__file__).parents[2] / "taiga"


def test_every_bulk_update_call_in_services_passes_batch_size():
    # Django builds one CASE WHEN per row for the whole list; the cost grows much faster than the row
    # count (about 3 s for 10k rows, minutes for 20k), so every call must run in batches.
    unbatched = []
    for path in TAIGA.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "bulk_update" and not any(k.arg == "batch_size" for k in node.keywords)):
                unbatched.append(f"{path.relative_to(TAIGA.parent)}:{node.lineno}")

    assert unbatched == []
