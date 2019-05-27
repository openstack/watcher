# Copyright (c) 2018 NEC, Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from oslo_upgradecheck import upgradecheck
import six

from watcher._i18n import _
from watcher.common import clients
from watcher import conf

CONF = conf.CONF


class Checks(upgradecheck.UpgradeCommands):

    """Contains upgrade checks

    Various upgrade checks should be added as separate methods in this class
    and added to _upgrade_checks tuple.
    """

    def _minimum_nova_api_version(self):
        """Checks the minimum required version of nova_client.api_version"""
        try:
            clients.check_min_nova_api_version(CONF.nova_client.api_version)
        except ValueError as e:
            return upgradecheck.Result(
                upgradecheck.Code.FAILURE, six.text_type(e))
        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    _upgrade_checks = (
        # Added in Train.
        (_('Minimum Nova API Version'), _minimum_nova_api_version),
    )


def main():
    return upgradecheck.main(
        CONF, project='watcher', upgrade_command=Checks())


if __name__ == '__main__':
    sys.exit(main())
