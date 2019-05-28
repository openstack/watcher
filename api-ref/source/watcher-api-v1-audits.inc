.. -*- rst -*-

======
Audits
======

There are creating, listing, updating and deleting methods of Watcher Audit
resources which are implemented via the ``/v1/audits`` resource.

In the Watcher system, an ``Audit`` is a request for optimizing a ``Cluster``.

The optimization is done in order to satisfy one ``Goal`` on a given
``Cluster``.

For each ``Audit``, the Watcher system generates an ``Action Plan``.

Create Audit
============

.. rest_method::  POST /v1/audits

Creates a new Audit resource.

Mandatory attribute to be supplied: ``audit_type``.

``Audit`` can be created either based on existed ``Audit Template`` or by
itself. In the first case, there also should be supplied
``audit_template_uuid``. If ``Audit`` is created without ``Audit Template``,
``goal`` should be provided.

Normal response codes: 201

Error codes: 400,404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_template_uuid: audittemplate_uuid
   - audit_type: audit_type
   - name: audit_name
   - goal: audit_goal
   - strategy: audit_strategy
   - parameters: audit_parameters
   - interval: audit_interval
   - auto_trigger: audit_autotrigger
   - start_time: audit_starttime_req
   - end_time: audit_endtime_req
   - force: audit_force

**Example ONESHOT Audit creation request:**

.. literalinclude:: samples/audit-create-request-oneshot.json
   :language: javascript

**Example CONTINUOUS Audit creation request with a specified strategy:**

.. literalinclude:: samples/audit-create-request-continuous.json
   :language: javascript

Response
--------

The list and example below are representative of the response as of API
version 1:

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - parameters: audit_parameters
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links
    - hostname: audit_hostname
    - start_time: audit_starttime_resp
    - end_time: audit_endtime_resp
    - force: audit_force

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-create-response.json
   :language: javascript

List Audit
==========

.. rest_method::  GET /v1/audits

Returns a list of Audit resources.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - goal: r_goal
   - strategy: r_strategy
   - limit: limit
   - marker: marker
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-list-response.json
   :language: javascript

List Audit Detailed
===================

.. rest_method::  GET /v1/audits/detail

Returns a list of Audit resources with complete details.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - goal: r_goal
   - strategy: r_strategy
   - limit: limit
   - marker: marker
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - parameters: audit_parameters
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links
    - hostname: audit_hostname
    - start_time: audit_starttime_resp
    - end_time: audit_endtime_resp
    - force: audit_force

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-list-detailed-response.json
   :language: javascript

Show Audit
==========

.. rest_method::  GET /v1/audits/{audit_ident}

Shows details for an Audit.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_ident: audit_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - parameters: audit_parameters
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links
    - hostname: audit_hostname
    - start_time: audit_starttime_resp
    - end_time: audit_endtime_resp
    - force: audit_force

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-show-response.json
   :language: javascript

Cancel Audit
============

.. rest_method::  PATCH /v1/audits/{audit_ident}

Cancels an ONGOING Audit resource.

Normal response codes: 200

Error codes: 400,404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_ident: audit_ident

**Example Audit cancelling request:**

.. literalinclude:: samples/audit-cancel-request.json
   :language: javascript

Response
--------

The list and example below are representative of the response as of API
version 1:

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - parameters: audit_parameters
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links
    - hostname: audit_hostname
    - start_time: audit_starttime_resp
    - end_time: audit_endtime_resp
    - force: audit_force

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-cancel-response.json
   :language: javascript

Update Audit
============

.. rest_method::  PATCH /v1/audits/{audit_ident}

Updates an Audit with the given information.

.. note:
    ``audit_type`` shouldn't be changed by PATCH method.

Normal response codes: 200

Error codes: 400,404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_ident: audit_ident

**Example PATCH document updating Audit:**

.. literalinclude:: samples/audit-update-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audit_name
    - audit_type: audit_type
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - interval: audit_interval
    - next_run_time: audit_next_run_time
    - parameters: audit_parameters
    - auto_trigger: audit_autotrigger
    - state: audit_state
    - scope: audittemplate_scope
    - links: links
    - hostname: audit_hostname
    - start_time: audit_starttime_resp
    - end_time: audit_endtime_resp
    - force: audit_force

**Example JSON representation of an Audit:**

.. literalinclude:: samples/audit-update-response.json
   :language: javascript

Delete Audit
============

.. rest_method::  DELETE /v1/audits/{audit_ident}

Deletes an Audit. Audit can be deleted only from FAILED, SUCCEEDED, CANCELLED,
SUSPENDED states.

Normal response codes: 204

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_ident: audit_ident
