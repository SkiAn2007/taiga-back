# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC


"""
Behaviour of the local parse_header replacement used by taiga.base.api.utils.mediatypes
(django.http.multipartparser.parse_header was removed in Django 5.0).
"""


def test_parse_header_compat_shim_basic():
    """
    Regression: parse_header was removed from django.http.multipartparser in
    Django 5.0. The compat shim must parse a simple content-type header correctly.
    """
    from taiga.base.api.utils.mediatypes import _MediaType

    mt = _MediaType("application/json; charset=utf-8")
    assert mt.main_type == "application"
    assert mt.sub_type == "json"
    assert mt.params.get("charset") == "utf-8"


def test_parse_header_compat_shim_no_params():
    """Compat shim handles headers with no parameters."""
    from taiga.base.api.utils.mediatypes import _MediaType

    mt = _MediaType("application/json")
    assert mt.main_type == "application"
    assert mt.sub_type == "json"
    assert mt.params == {}


def test_parse_header_compat_shim_wildcard():
    """Compat shim handles wildcard media types."""
    from taiga.base.api.utils.mediatypes import _MediaType

    mt = _MediaType("*/*")
    assert mt.main_type == "*"
    assert mt.sub_type == "*"


def test_media_type_matches_exact():
    """media_type_matches returns True for identical types."""
    from taiga.base.api.utils.mediatypes import media_type_matches

    assert media_type_matches("application/json", "application/json") is True


def test_media_type_matches_wildcard():
    """media_type_matches returns True when rhs is a wildcard."""
    from taiga.base.api.utils.mediatypes import media_type_matches

    assert media_type_matches("application/json", "*/*") is True


def test_is_form_media_type():
    """is_form_media_type works correctly after the parse_header shim."""
    from taiga.base.api.request import is_form_media_type

    assert is_form_media_type("application/x-www-form-urlencoded") is True
    assert is_form_media_type("multipart/form-data") is True
    assert is_form_media_type("application/json") is False
