# Copyright (c) 2015 Intel Corporation
# Copyright (c) 2018 SBCloud
# All Rights Reserved.
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

import enum


class VERSIONS(enum.Enum):
    MINOR_0_ROCKY = 0  # v1.0: corresponds to Rocky API
    MINOR_1_START_END_TIMING = 1  # v1.1: Add start/end timei for audit
    MINOR_2_FORCE = 2  # v1.2: Add force field to audit
    MINOR_3_DATAMODEL = 3  # v1.3: Add list datamodel API
    MINOR_4_WEBHOOK_API = 4  # v1.4: Add webhook trigger API
    MINOR_MAX_VERSION = 4


# This is the version 1 API
BASE_VERSION = 1
# String representations of the minor and maximum versions
_MIN_VERSION_STRING = '{}.{}'.format(BASE_VERSION,
                                     VERSIONS.MINOR_0_ROCKY.value)
_MAX_VERSION_STRING = '{}.{}'.format(BASE_VERSION,
                                     VERSIONS.MINOR_MAX_VERSION.value)


def service_type_string():
    return 'infra-optim'


def min_version_string():
    """Returns the minimum supported API version (as a string)"""
    return _MIN_VERSION_STRING


def max_version_string():
    """Returns the maximum supported API version (as a string).

    If the service is pinned, the maximum API version is the pinned
    version. Otherwise, it is the maximum supported API version.

    """
    return _MAX_VERSION_STRING
