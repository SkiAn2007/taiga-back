# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_no_pending_model_changes():
    # exits with status 1 (SystemExit) when models and migrations disagree
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
