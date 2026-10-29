# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import importlib.machinery
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).parents[2]
PROTECTED = "taiga_contrib_protected.storage.ProtectedFileSystemStorage"
ENV = {
    "TAIGA_SECRET_KEY": "x", "TAIGA_SITES_SCHEME": "http", "TAIGA_SITES_DOMAIN": "localhost",
    "POSTGRES_DB": "d", "POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_HOST": "h",
    "CELERY_ENABLED": "False",
}


def _load(path):
    # the file does `from .common import *`, so load it as settings.config
    loader = importlib.machinery.SourceFileLoader("settings.config", str(ROOT / path))  # .example has no known suffix
    spec = importlib.util.spec_from_file_location("settings.config", ROOT / path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", ["docker/config.py", "settings/config.py.prod.example"])
def test_shipped_config_serves_media_through_protected_storage(path, monkeypatch):
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)

    config = _load(path)

    assert config.STORAGES["default"]["BACKEND"] == PROTECTED
    assert config.STORAGES["easy_thumbnails"]["BACKEND"] == PROTECTED
    assert not hasattr(config, "DEFAULT_FILE_STORAGE")  # removed in Django 5.1, silently ignored
