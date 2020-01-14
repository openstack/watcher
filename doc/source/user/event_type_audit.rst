..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.


======================
Audit using Aodh alarm
======================

Audit with EVENT type can be triggered by special alarm. This guide walks
you through the steps to build an event-driven optimization solution by
integrating Watcher with Ceilometer/Aodh.

Step 1: Create an audit with EVENT type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first step is to create an audit with EVENT type,
you can create an audit template firstly:

.. code-block:: bash

  $ openstack optimize audittemplate create your_template_name <your_goal> \
    --strategy <your_strategy>

or create an audit directly with special goal and strategy:

.. code-block:: bash

  $ openstack optimize audit create --goal <your_goal> \
    --strategy <your_strategy> --audit_type EVENT

This is an example for creating an audit with dummy strategy:

.. code-block:: bash

  $ openstack optimize audit create --goal dummy \
    --strategy dummy --audit_type EVENT
  +---------------+--------------------------------------+
  | Field         | Value                                |
  +---------------+--------------------------------------+
  | UUID          | a3326a6a-c18e-4e8e-adba-d0c61ad404c5 |
  | Name          | dummy-2020-01-14T03:21:19.168467     |
  | Created At    | 2020-01-14T03:21:19.200279+00:00     |
  | Updated At    | None                                 |
  | Deleted At    | None                                 |
  | State         | PENDING                              |
  | Audit Type    | EVENT                                |
  | Parameters    | {u'para2': u'hello', u'para1': 3.2}  |
  | Interval      | None                                 |
  | Goal          | dummy                                |
  | Strategy      | dummy                                |
  | Audit Scope   | []                                   |
  | Auto Trigger  | False                                |
  | Next Run Time | None                                 |
  | Hostname      | None                                 |
  | Start Time    | None                                 |
  | End Time      | None                                 |
  | Force         | False                                |
  +---------------+--------------------------------------+

We need to build Aodh action url using Watcher webhook API.
For convenience we export the url into an environment variable:

.. code-block:: bash

  $ export AUDIT_UUID=a3326a6a-c18e-4e8e-adba-d0c61ad404c5
  $ export ALARM_URL="trust+http://localhost/infra-optim/v1/webhooks/$AUDIT_UUID"

Step 2: Create Aodh Alarm
~~~~~~~~~~~~~~~~~~~~~~~~~

Once we have the audit created, we can continue to create Aodh alarm and
set the alarm action to Watcher webhook API. The alarm type can be event(
i.e. ``compute.instance.create.end``) or gnocchi_resources_threshold(i.e.
``cpu_util``), more info refer to alarm-creation_

For example:

.. code-block:: bash

  $ openstack alarm create \
    --type event --name instance_create \
    --event-type "compute.instance.create.end" \
    --enable True --repeat-actions False \
    --alarm-action $ALARM_URL
  +---------------------------+------------------------------------------------------------------------------------------+
  | Field                     | Value                                                                                    |
  +---------------------------+------------------------------------------------------------------------------------------+
  | alarm_actions             | [u'trust+http://localhost/infra-optim/v1/webhooks/a3326a6a-c18e-4e8e-adba-d0c61ad404c5'] |
  | alarm_id                  | b9e381fc-8e3e-4943-82ee-647e7a2ef644                                                     |
  | description               | Alarm when compute.instance.create.end event occurred.                                   |
  | enabled                   | True                                                                                     |
  | event_type                | compute.instance.create.end                                                              |
  | insufficient_data_actions | []                                                                                       |
  | name                      | instance_create                                                                          |
  | ok_actions                | []                                                                                       |
  | project_id                | 728d66e18c914af1a41e2a585cf766af                                                         |
  | query                     |                                                                                          |
  | repeat_actions            | False                                                                                    |
  | severity                  | low                                                                                      |
  | state                     | insufficient data                                                                        |
  | state_reason              | Not evaluated yet                                                                        |
  | state_timestamp           | 2020-01-14T03:56:26.894416                                                               |
  | time_constraints          | []                                                                                       |
  | timestamp                 | 2020-01-14T03:56:26.894416                                                               |
  | type                      | event                                                                                    |
  | user_id                   | 88c40156af7445cc80580a1e7e3ba308                                                         |
  +---------------------------+------------------------------------------------------------------------------------------+

.. _alarm-creation: https://docs.openstack.org/aodh/latest/admin/telemetry-alarms.html#alarm-creation

Step 3: Trigger the alarm
~~~~~~~~~~~~~~~~~~~~~~~~~

In this example, you can create a new instance to trigger the alarm.
The alarm state will translate from ``insufficient data`` to ``alarm``.

.. code-block:: bash

  $ openstack alarm show b9e381fc-8e3e-4943-82ee-647e7a2ef644
  +---------------------------+-------------------------------------------------------------------------------------------------------------------+
  | Field                     | Value                                                                                                             |
  +---------------------------+-------------------------------------------------------------------------------------------------------------------+
  | alarm_actions             | [u'trust+http://localhost/infra-optim/v1/webhooks/a3326a6a-c18e-4e8e-adba-d0c61ad404c5']                          |
  | alarm_id                  | b9e381fc-8e3e-4943-82ee-647e7a2ef644                                                                              |
  | description               | Alarm when compute.instance.create.end event occurred.                                                            |
  | enabled                   | True                                                                                                              |
  | event_type                | compute.instance.create.end                                                                                       |
  | insufficient_data_actions | []                                                                                                                |
  | name                      | instance_create                                                                                                   |
  | ok_actions                | []                                                                                                                |
  | project_id                | 728d66e18c914af1a41e2a585cf766af                                                                                  |
  | query                     |                                                                                                                   |
  | repeat_actions            | False                                                                                                             |
  | severity                  | low                                                                                                               |
  | state                     | alarm                                                                                                             |
  | state_reason              | Event <id=67dd0afa-2082-45a4-8825-9573b2cc60e5,event_type=compute.instance.create.end> hits the query <query=[]>. |
  | state_timestamp           | 2020-01-14T03:56:26.894416                                                                                        |
  | time_constraints          | []                                                                                                                |
  | timestamp                 | 2020-01-14T06:17:40.350649                                                                                        |
  | type                      | event                                                                                                             |
  | user_id                   | 88c40156af7445cc80580a1e7e3ba308                                                                                  |
  +---------------------------+-------------------------------------------------------------------------------------------------------------------+

Step 4: Verify the audit
~~~~~~~~~~~~~~~~~~~~~~~~

This can be verified to check if the audit state was ``SUCCEEDED``:

.. code-block:: bash

  $ openstack optimize audit show a3326a6a-c18e-4e8e-adba-d0c61ad404c5
  +---------------+--------------------------------------+
  | Field         | Value                                |
  +---------------+--------------------------------------+
  | UUID          | a3326a6a-c18e-4e8e-adba-d0c61ad404c5 |
  | Name          | dummy-2020-01-14T03:21:19.168467     |
  | Created At    | 2020-01-14T03:21:19+00:00            |
  | Updated At    | 2020-01-14T06:26:40+00:00            |
  | Deleted At    | None                                 |
  | State         | SUCCEEDED                            |
  | Audit Type    | EVENT                                |
  | Parameters    | {u'para2': u'hello', u'para1': 3.2}  |
  | Interval      | None                                 |
  | Goal          | dummy                                |
  | Strategy      | dummy                                |
  | Audit Scope   | []                                   |
  | Auto Trigger  | False                                |
  | Next Run Time | None                                 |
  | Hostname      | ubuntudbs                            |
  | Start Time    | None                                 |
  | End Time      | None                                 |
  | Force         | False                                |
  +---------------+--------------------------------------+

and you can use the following command to check if the action plan
was created:

.. code-block:: bash

  $ openstack optimize actionplan list --audit a3326a6a-c18e-4e8e-adba-d0c61ad404c5
  +--------------------------------------+--------------------------------------+-------------+------------+-----------------+
  | UUID                                 | Audit                                | State       | Updated At | Global efficacy |
  +--------------------------------------+--------------------------------------+-------------+------------+-----------------+
  | 673b3fcb-8c16-4a41-9ee3-2956d9f6ca9e | a3326a6a-c18e-4e8e-adba-d0c61ad404c5 | RECOMMENDED | None       |                 |
  +--------------------------------------+--------------------------------------+-------------+------------+-----------------+
