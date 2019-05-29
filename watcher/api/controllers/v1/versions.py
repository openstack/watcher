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


# This is the version 1 API
BASE_VERSION = 1

# Here goes a short log of changes in every version.
#
# v1.0: corresponds to Rocky API
# v1.1: Add start/end time for continuous audit
# v1.2: Add force field to audit

MINOR_0_ROCKY = 0
MINOR_1_START_END_TIMING = 1
MINOR_2_FORCE = 2

MINOR_MAX_VERSION = MINOR_2_FORCE

# String representations of the minor and maximum versions
_MIN_VERSION_STRING = '{}.{}'.format(BASE_VERSION, MINOR_0_ROCKY)
_MAX_VERSION_STRING = '{}.{}'.format(BASE_VERSION, MINOR_MAX_VERSION)


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
