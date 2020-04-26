# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import requests
from unittest import mock

fakeAuthTokenHeaders = {'X-User-Id': u'773a902f022949619b5c2f32cd89d419',
                        'X-Roles': u'admin, ResellerAdmin, _member_',
                        'X-Project-Id': u'5588aebbcdc24e17a061595f80574376',
                        'X-Project-Name': 'test',
                        'X-User-Name': 'test',
                        'X-Auth-Token': u'5588aebbcdc24e17a061595f80574376',
                        'X-Forwarded-For': u'10.10.10.10, 11.11.11.11',
                        'X-Service-Catalog': u'{test: 12345}',
                        'X-Identity-Status': 'Confirmed',
                        'X-User-Domain-Name': 'domain',
                        'X-Project-Domain-Id': 'project_domain_id',
                        'X-User-Domain-Id': 'user_domain_id',
                        }


class FakePecanRequest(mock.Mock):

    def __init__(self, **kwargs):
        super(FakePecanRequest, self).__init__(**kwargs)
        self.host_url = 'http://test_url:8080/test'
        self.context = {}
        self.body = ''
        self.content_type = 'text/unicode'
        self.params = {}
        self.path = '/v1/services'
        self.headers = fakeAuthTokenHeaders
        self.environ = {}

    def __setitem__(self, index, value):
        setattr(self, index, value)


class FakePecanResponse(mock.Mock):

    def __init__(self, **kwargs):
        super(FakePecanResponse, self).__init__(**kwargs)
        self.status = None


class FakeApp(object):
    pass


class FakeService(mock.Mock):
    def __init__(self, **kwargs):
        super(FakeService, self).__init__(**kwargs)
        self.__tablename__ = 'service'
        self.__resource__ = 'services'
        self.user_id = 'fake user id'
        self.project_id = 'fake project id'
        self.uuid = 'test_uuid'
        self.id = 8
        self.name = 'james'
        self.service_type = 'not_this'
        self.description = 'amazing'
        self.tags = ['this', 'and that']
        self.read_only = True

    def as_dict(self):
        return dict(service_type=self.service_type,
                    user_id=self.user_id,
                    project_id=self.project_id,
                    uuid=self.uuid,
                    id=self.id,
                    name=self.name,
                    tags=self.tags,
                    read_only=self.read_only,
                    description=self.description)


class FakeAuthProtocol(mock.Mock):

    def __init__(self, **kwargs):
        super(FakeAuthProtocol, self).__init__(**kwargs)
        self.app = FakeApp()
        self.config = ''


class FakeResponse(requests.Response):
    def __init__(self, status_code, content=None, headers=None):
        """A requests.Response that can be used as a mock return_value.

        A key feature is that the instance will evaluate to True or False like
        a real Response, based on the status_code.
        Properties like ok, status_code, text, and content, and methods like
        json(), work as expected based on the inputs.
        :param status_code: Integer HTTP response code (200, 404, etc.)
        :param content: String supplying the payload content of the response.
                        Using a json-encoded string will make the json() method
                        behave as expected.
        :param headers: Dict of HTTP header values to set.
        """
        super(FakeResponse, self).__init__()
        self.status_code = status_code
        if content:
            self._content = content
        if headers:
            self.headers = headers
