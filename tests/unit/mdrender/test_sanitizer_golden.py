# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pathlib

import pytest

from taiga.mdrender.service import render_and_extract

GOLDEN = pathlib.Path(__file__).parent / "golden"
CASES = sorted(p.stem for p in GOLDEN.glob("*.md"))


@pytest.mark.parametrize("name", CASES)
def test_render_matches_golden(name):
    html, _ = render_and_extract(None, (GOLDEN / f"{name}.md").read_text())

    assert html == (GOLDEN / f"{name}.html").read_text()
