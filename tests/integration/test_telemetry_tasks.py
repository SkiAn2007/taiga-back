# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest
import rudderstack.analytics as rudder_analytics

from taiga.telemetry import tasks

pytestmark = pytest.mark.django_db


def test_send_telemetry_configures_rudder_and_tracks_daily_event(settings, monkeypatch):
    settings.RUDDER_WRITE_KEY = "dummy-write-key"
    settings.DATA_PLANE_URL = "https://dataplane.example.com"
    calls = []
    monkeypatch.setattr(rudder_analytics, "track", lambda **kwargs: calls.append(kwargs))

    tasks.send_telemetry()

    assert rudder_analytics.write_key == "dummy-write-key"
    assert rudder_analytics.dataPlaneUrl == "https://dataplane.example.com"
    assert [c["event"] for c in calls] == ["Daily telemetry"]
