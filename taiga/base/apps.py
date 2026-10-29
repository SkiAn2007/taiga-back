# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

# Removed in Django 5.1; Django stores them but never reads them, so media would silently
# lose its protected storage (signed URLs) or move from S3 to the local disk.
REMOVED_STORAGE_SETTINGS = ("DEFAULT_FILE_STORAGE", "STATICFILES_STORAGE", "THUMBNAIL_DEFAULT_STORAGE")


def check_removed_storage_settings():
    from django.conf import settings

    for name in REMOVED_STORAGE_SETTINGS:
        if hasattr(settings, name):
            raise ImproperlyConfigured(
                f"The {name} setting is ignored since Django 5.1. Move it into STORAGES "
                "(see docker/config.py and step 5 of the upgrade notes in README.md).")


class BaseAppConfig(AppConfig):
    name = "taiga.base"
    verbose_name = "Base App Config"

    def ready(self):
        check_removed_storage_settings()
        from .signals.thumbnails import connect_thumbnail_signals
        from .signals.cleanup_files import connect_cleanup_files_signals

        connect_thumbnail_signals()
        connect_cleanup_files_signals()
