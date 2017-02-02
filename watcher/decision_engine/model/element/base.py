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

import abc
import collections

from lxml import etree
from oslo_log import log
import six

from watcher.objects import base
from watcher.objects import fields as wfields

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Element(base.WatcherObject, base.WatcherObjectDictCompat,
              base.WatcherComparableObject):

    # Initial version
    VERSION = '1.0'

    fields = {}

    def __init__(self, context=None, **kwargs):
        for name, field in self.fields.items():
            # The idea here is to force the initialization of unspecified
            # fields that have a default value
            if (name not in kwargs and not field.nullable and
                    field.default != wfields.UnspecifiedDefault):
                kwargs[name] = field.default
        super(Element, self).__init__(context, **kwargs)

    @abc.abstractmethod
    def accept(self, visitor):
        raise NotImplementedError()

    def as_xml_element(self):
        sorted_fieldmap = []
        for field in self.fields:
            try:
                value = str(self[field])
                sorted_fieldmap.append((field, value))
            except Exception as exc:
                LOG.exception(exc)

        attrib = collections.OrderedDict(sorted_fieldmap)

        element_name = self.__class__.__name__
        instance_el = etree.Element(element_name, attrib=attrib)

        return instance_el
