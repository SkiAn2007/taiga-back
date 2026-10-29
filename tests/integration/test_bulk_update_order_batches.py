# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from taiga.projects import models
from taiga.projects.services import bulk_update_order as services

from .. import factories as f

pytestmark = pytest.mark.django_db


def test_bulk_update_order_runs_in_batches_of_500_rows():
    project = f.ProjectFactory.create()
    points = models.Points.objects.bulk_create(
        [models.Points(project=project, name=f"p{i}", order=i) for i in range(1100)])

    with CaptureQueriesContext(connection) as queries:
        services._bulk_update_order(models.Points, project, [(p.id, p.order + 1) for p in points])

    updates = [q for q in queries if q["sql"].startswith('UPDATE "projects_points"')]
    assert len(updates) == 3  # 500 + 500 + 100
    assert models.Points.objects.filter(project=project, order=1100).exists()
