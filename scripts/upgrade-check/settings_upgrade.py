# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Test settings pointed at the throw-away database of run_upgrade_check.sh."""
import os

from tests.config import *  # noqa

DATABASES["default"].update(  # noqa
    NAME=os.environ["UPGRADE_DB_NAME"], HOST=os.environ["UPGRADE_DB_HOST"],
    PORT=os.environ["UPGRADE_DB_PORT"], USER="taiga", PASSWORD="taiga")
