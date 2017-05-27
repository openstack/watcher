# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Note(gibi): Importing publicly called functions so the caller code does not
# need to be changed after we moved these function inside the package
# Todo(gibi): remove these imports after legacy notifications using these are
# transformed to versioned notifications
from watcher.notifications import action  # noqa
from watcher.notifications import action_plan  # noqa
from watcher.notifications import audit  # noqa
from watcher.notifications import exception  # noqa
from watcher.notifications import goal  # noqa
from watcher.notifications import service  # noqa
from watcher.notifications import strategy  # noqa
