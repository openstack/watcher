..
      Copyright 2016 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Policies
========

Watcher's public API calls may be restricted to certain sets of users using a
policy configuration file. This document explains exactly how policies are
configured and what they apply to.

A policy is composed of a set of rules that are used in determining if a
particular action may be performed by the authorized tenant.

Constructing a Policy Configuration File
----------------------------------------

A policy configuration file is a simply JSON object that contain sets of
rules. Each top-level key is the name of a rule. Each rule
is a string that describes an action that may be performed in the Watcher API.

The actions that may have a rule enforced on them are:

* ``strategy:get_all``, ``strategy:detail`` - List available strategies

  * ``GET /v1/strategies``
  * ``GET /v1/strategies/detail``

* ``strategy:get`` - Retrieve a specific strategy entity

  * ``GET /v1/strategies/<STRATEGY_UUID>``
  * ``GET /v1/strategies/<STRATEGY_NAME>``


* ``goal:get_all``, ``goal:detail`` - List available goals

  * ``GET /v1/goals``
  * ``GET /v1/goals/detail``

* ``goal:get`` - Retrieve a specific goal entity

  * ``GET /v1/goals/<GOAL_UUID>``
  * ``GET /v1/goals/<GOAL_NAME>``


* ``audit_template:get_all``, ``audit_template:detail`` - List available
  audit_templates

  * ``GET /v1/audit_templates``
  * ``GET /v1/audit_templates/detail``

* ``audit_template:get`` - Retrieve a specific audit template entity

  * ``GET /v1/audit_templates/<AUDIT_TEMPLATE_UUID>``
  * ``GET /v1/audit_templates/<AUDIT_TEMPLATE_NAME>``

* ``audit_template:create`` - Create an audit template entity

  * ``POST /v1/audit_templates``

* ``audit_template:delete`` - Delete an audit template entity

  * ``DELETE /v1/audit_templates/<AUDIT_TEMPLATE_UUID>``
  * ``DELETE /v1/audit_templates/<AUDIT_TEMPLATE_NAME>``

* ``audit_template:update`` - Update an audit template entity

  * ``PATCH /v1/audit_templates/<AUDIT_TEMPLATE_UUID>``
  * ``PATCH /v1/audit_templates/<AUDIT_TEMPLATE_NAME>``


* ``audit:get_all``, ``audit:detail`` - List available audits

  * ``GET /v1/audits``
  * ``GET /v1/audits/detail``

* ``audit:get`` - Retrieve a specific audit entity

  * ``GET /v1/audits/<AUDIT_UUID>``

* ``audit:create`` - Create an audit entity

  * ``POST /v1/audits``

* ``audit:delete`` - Delete an audit entity

  * ``DELETE /v1/audits/<AUDIT_UUID>``

* ``audit:update`` - Update an audit entity

  * ``PATCH /v1/audits/<AUDIT_UUID>``


* ``action_plan:get_all``, ``action_plan:detail`` - List available action plans

  * ``GET /v1/action_plans``
  * ``GET /v1/action_plans/detail``

* ``action_plan:get`` - Retrieve a specific action plan entity

  * ``GET /v1/action_plans/<ACTION_PLAN_UUID>``

* ``action_plan:delete`` - Delete an action plan entity

  * ``DELETE /v1/action_plans/<ACTION_PLAN_UUID>``

* ``action_plan:update`` - Update an action plan entity

  * ``PATCH /v1/audits/<ACTION_PLAN_UUID>``


* ``action:get_all``, ``action:detail`` - List available action

  * ``GET /v1/actions``
  * ``GET /v1/actions/detail``

* ``action:get`` - Retrieve a specific action plan entity

  * ``GET /v1/actions/<ACTION_UUID>``


* ``service:get_all``, ``service:detail`` - List available Watcher services

  * ``GET /v1/services``
  * ``GET /v1/services/detail``

* ``service:get`` - Retrieve a specific Watcher service entity

  * ``GET /v1/services/<SERVICE_ID>``



To limit an action to a particular role or roles, you list the roles like so ::

  {
    "audit:create": ["role:admin", "role:superuser"]
  }

The above would add a rule that only allowed users that had roles of either
"admin" or "superuser" to launch an audit.
