# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import pytest
from django.core.exceptions import ImproperlyConfigured

from taiga.base.apps import check_removed_storage_settings


@pytest.mark.parametrize("name", ["DEFAULT_FILE_STORAGE", "STATICFILES_STORAGE", "THUMBNAIL_DEFAULT_STORAGE"])
def test_removed_storage_setting_is_rejected_instead_of_silently_ignored(settings, name):
    setattr(settings, name, "some.storage.Backend")

    with pytest.raises(ImproperlyConfigured, match=name):
        check_removed_storage_settings()


def test_current_settings_pass_the_check():
    check_removed_storage_settings()
