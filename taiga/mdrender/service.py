# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

from django.conf import settings

import hashlib
import re
import functools
import bleach
from bleach.css_sanitizer import CSSSanitizer
from bleach.html5lib_shim import convert_entities
from bleach.sanitizer import Cleaner

from django.core.cache import cache
from django.utils.encoding import force_bytes

from markdown import Markdown

from .extensions.autolink import AutolinkExtension
from .extensions.automail import AutomailExtension
from .extensions.semi_sane_lists import SemiSaneListExtension
from .extensions.strikethrough import StrikethroughExtension
from .extensions.wikilinks import WikiLinkExtension
from .extensions.emojify import EmojifyExtension
from .extensions.mentions import MentionsExtension
from .extensions.references import TaigaReferencesExtension
from .extensions.target_link import TargetBlankLinkExtension
from .extensions.refresh_attachment import RefreshAttachmentExtension

# Bleach configuration (bleach >= 6 module constants are immutable, pass these to clean())
ALLOWED_TAGS = set(bleach.ALLOWED_TAGS) | {"p", "table", "thead", "tbody", "th", "tr", "td", "h1",
                                           "h2", "h3", "h4", "h5", "h6", "div", "pre", "span",
                                           "hr", "dl", "dt", "dd", "sup", "img", "del", "br",
                                           "ins", "input", "label"}

ALLOWED_ATTRIBUTES = {
    **bleach.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "alt", "target"],
    "img": ["alt", "src"],
    "input": ["type", "checked"],
    "*": ["class", "style", "id"],
}


class StrictCSSSanitizer(CSSSanitizer):
    """The sanitize_css() of bleach 4.1.0 on top of bleach 6's CSSSanitizer.

    bleach >= 6 only filters CSS property names. bleach 4 also dropped url(...) values and discarded
    a whole style that contained anything but plain words, numbers, colours and rgb()/hsl()-like
    parentheses, so url(), expression() and quoted payloads never pass. Kept identical for parity.
    """
    GAUNTLET = re.compile(
        r"""^(  # consider a style attribute value as composed of:
[/:,#%!.\s\w]    # a non-newline character
|\w-\w           # 3 characters in the form \w-\w
|'[\s\w]+'\s*    # a single quoted string of [\s\w]+ with trailing space
|"[\s\w]+"       # a double quoted string of [\s\w]+
|\([\d,%\.\s]+\) # a parenthesized string of digits, commas, periods, percent signs, whitespace
)*$""", flags=re.U | re.VERBOSE)

    def sanitize_css(self, style):
        style = convert_entities(style)
        style = re.compile(r"url\s*\(\s*[^\s)]+?\s*\)\s*").sub(" ", style)
        if not all(self.GAUNTLET.match(part) for part in style.split(";")):
            return ""
        if not re.match(r"^\s*([-\w]+\s*:[^:;]*(;\s*|$))*$", style):
            return ""
        clean = []
        for prop, value in re.findall(r"([-\w]+)\s*:\s*([^:;]*)", style):
            if value and (prop.lower() in self.allowed_css_properties
                          or prop.lower() in self.allowed_svg_properties):
                clean.append(prop + ": " + value + ";")
        return " ".join(clean)


CSS_SANITIZER = StrictCSSSanitizer(allowed_css_properties=["background"], allowed_svg_properties=[])
ALLOWED_PROTOCOLS = ["http", "https", "ftp", "mailto"]


def _make_extensions_list(project=None):
    return ["pymdownx.tasklist",
            AutolinkExtension(),
            AutomailExtension(),
            SemiSaneListExtension(),
            StrikethroughExtension(),
            WikiLinkExtension(project),
            EmojifyExtension(),
            MentionsExtension(project=project),
            TaigaReferencesExtension(project),
            TargetBlankLinkExtension(),
            RefreshAttachmentExtension(project=project),
            "markdown.extensions.extra",
            "markdown.extensions.codehilite",
            "markdown.extensions.sane_lists",
            "markdown.extensions.toc",
            "markdown.extensions.nl2br"]

def _make_extension_configs():
    return {
        "pymdownx.tasklist": {
            "custom_checkbox": [
                True,
                "Add an empty label tag after the input tag to allow for custom styling"
            ]
        }
    }


import diff_match_patch


def cache_by_sha(func):
    @functools.wraps(func)
    def _decorator(project, text):
        if not settings.MDRENDER_CACHE_ENABLE:
            return func(project, text)

        # Avoid cache of too short texts
        if len(text) <= settings.MDRENDER_CACHE_MIN_SIZE:
            return func(project, text)

        sha1_hash = hashlib.sha1(force_bytes(text)).hexdigest()
        key = "mdrender/{}-{}".format(sha1_hash, project.id)

        # Try to get it from the cache
        cached = cache.get(key)
        if cached is not None:
            return cached

        returned_value = func(project, text)
        cache.set(key, returned_value, timeout=settings.MDRENDER_CACHE_TIMEOUT)
        return returned_value

    return _decorator


def _clean(html):
    cleaner = Cleaner(tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                      protocols=ALLOWED_PROTOCOLS, css_sanitizer=CSS_SANITIZER)
    # keep the alphabetical attribute order of the output stored by earlier versions
    cleaner.serializer.alphabetical_attributes = True
    return cleaner.clean(html)


def _get_markdown(project):
    extensions = _make_extensions_list(project=project)
    extension_configs = _make_extension_configs()
    md = Markdown(extensions=extensions, extension_configs=extension_configs)
    md.extracted_data = {"mentions": [], "references": []}
    return md


@cache_by_sha
def render(project, text):
    md = _get_markdown(project)
    return _clean(md.convert(text))


def render_and_extract(project, text):
    md = _get_markdown(project)
    result = _clean(md.convert(text))
    return (result, md.extracted_data)


class DiffMatchPatch(diff_match_patch.diff_match_patch):
    def diff_pretty_html(self, diffs):
        def _sanitize_text(text):
            return (text.replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;").replace("\n", "<br />"))

        def _split_long_text(text, idx, size):
            splited_text = text.split()

            if len(splited_text) > 25:
                if idx == 0:
                    # The first is (...)text
                    first = ""
                else:
                    first = " ".join(splited_text[:10])

                if idx != 0 and idx == size - 1:
                    # The last is text(...)
                    last = ""
                else:
                    last = " ".join(splited_text[-10:])

                return "{}(...){}".format(first, last)
            return text

        size = len(diffs)
        html = []
        for idx, (op, data) in enumerate(diffs):
            if op == self.DIFF_INSERT:
                text = _sanitize_text(data)
                html.append("<ins style=\"background:#e6ffe6;\">{}</ins>".format(text))
            elif op == self.DIFF_DELETE:
                text = _sanitize_text(data)
                html.append("<del style=\"background:#ffe6e6;\">{}</del>".format(text))
            elif op == self.DIFF_EQUAL:
                text = _split_long_text(_sanitize_text(data), idx, size)
                html.append("<span>{}</span>".format(text))

        return "".join(html)


def get_diff_of_htmls(html1, html2):
    diffutil = DiffMatchPatch()
    diffs = diffutil.diff_main(html1 or "", html2 or "")
    diffutil.diff_cleanupSemantic(diffs)
    return diffutil.diff_pretty_html(diffs)


__all__ = ["render", "get_diff_of_htmls", "render_and_extract"]
