# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest

from taiga.projects.services import bulk_update_order as services

from .. import factories as f

pytestmark = pytest.mark.django_db

CASES = [
    (services.bulk_update_epic_status_order, f.EpicStatusFactory),
    (services.bulk_update_userstory_status_order, f.UserStoryStatusFactory),
    (services.bulk_update_points_order, f.PointsFactory),
    (services.bulk_update_task_status_order, f.TaskStatusFactory),
    (services.bulk_update_issue_status_order, f.IssueStatusFactory),
    (services.bulk_update_issue_type_order, f.IssueTypeFactory),
    (services.bulk_update_priority_order, f.PriorityFactory),
    (services.bulk_update_severity_order, f.SeverityFactory),
    (services.bulk_update_swimlane_order, f.SwimlaneFactory),
]


@pytest.mark.parametrize("update_order, factory", CASES, ids=[c[0].__name__ for c in CASES])
def test_bulk_update_order_only_touches_rows_of_the_given_project(update_order, factory):
    project = f.ProjectFactory.create()
    other_project = f.ProjectFactory.create()
    own = factory.create(project=project, order=1)
    foreign = factory.create(project=other_project, order=1)

    update_order(project, project.owner, [(own.id, 7), (foreign.id, 9)])

    own.refresh_from_db()
    foreign.refresh_from_db()
    assert (own.order, foreign.order) == (7, 1)
