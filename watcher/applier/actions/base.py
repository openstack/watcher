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


import abc

import six

from watcher.common import clients


@six.add_metaclass(abc.ABCMeta)
class BaseAction(object):
    # NOTE(jed) by convention we decided
    # that the attribute "resource_id" is the unique id of
    # the resource to which the Action applies to allow us to use it in the
    # watcher dashboard and will be nested in input_parameters
    RESOURCE_ID = 'resource_id'

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self._input_parameters = {}
        self._osc = osc

    @property
    def osc(self):
        if not self._osc:
            self._osc = clients.OpenStackClients()
        return self._osc

    @property
    def input_parameters(self):
        return self._input_parameters

    @input_parameters.setter
    def input_parameters(self, p):
        self._input_parameters = p

    @property
    def resource_id(self):
        return self.input_parameters[self.RESOURCE_ID]

    @abc.abstractmethod
    def execute(self):
        """Executes the main logic of the action

        This method can be used to perform an action on a given set of input
        parameters to accomplish some type of operation. This operation may
        return a boolean value as a result of its execution. If False, this
        will be considered as an error and will then trigger the reverting of
        the actions.

        :returns: A flag indicating whether or not the action succeeded
        :rtype: bool
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def revert(self):
        """Revert this action

        This method should rollback the resource to its initial state in the
        event of a faulty execution. This happens when the action raised an
        exception during its :py:meth:`~.BaseAction.execute`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def precondition(self):
        """Hook: called before the execution of an action

        This method can be used to perform some initializations or to make
        some more advanced validation on its input parameters. So if you wish
        to block its execution based on this factor, `raise` the related
        exception.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def postcondition(self):
        """Hook: called after the execution of an action

        This function is called regardless of whether an action succeded or
        not. So you can use it to perform cleanup operations.
        """
        raise NotImplementedError()

    @abc.abstractproperty
    def schema(self):
        """Defines a Schema that the input parameters shall comply to

        :returns: A schema declaring the input parameters this action should be
                  provided along with their respective constraints
        :rtype: :py:class:`voluptuous.Schema` instance
        """
        raise NotImplementedError()

    def validate_parameters(self):
        self.schema(self.input_parameters)
        return True
