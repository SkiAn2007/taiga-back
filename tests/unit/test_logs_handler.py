# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos INC

import logging

from taiga.base.utils.logs import CustomAdminEmailHandler


def test_custom_admin_email_handler_sends_mail_to_admins(settings, mailoutbox):
    settings.ADMINS = [("Admin", "admin@example.com")]
    record = logging.LogRecord("taiga", logging.ERROR, __file__, 1, "something broke", None, None)

    CustomAdminEmailHandler().emit(record)

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["admin@example.com"]
