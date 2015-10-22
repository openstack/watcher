# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor


class Promise(object):
    executor = ThreadPoolExecutor(
        max_workers=10)

    def __init__(self, func):
        self.func = func

    def resolve(self, *args, **kwargs):
        resolved_args = []
        resolved_kwargs = {}

        for i, arg in enumerate(args):
            if isinstance(arg, Future):
                resolved_args.append(arg.result())
            else:
                resolved_args.append(arg)

        for kw, arg in kwargs.items():
            if isinstance(arg, Future):
                resolved_kwargs[kw] = arg.result()
            else:
                resolved_kwargs[kw] = arg

        return self.func(*resolved_args, **resolved_kwargs)

    def __call__(self, *args, **kwargs):
        return self.executor.submit(self.resolve, *args, **kwargs)
