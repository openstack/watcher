.. -*- rst -*-

===============
Audit Templates
===============

There are creating, listing, updating and deleting methods of Watcher Audit
Template resources which are implemented via the ``/v1/audit_templates``
resource.

An Audit may be launched several times with the same settings
(Goal, thresholds, ...). Therefore it makes sense to save those settings in
some sort of Audit preset object, which is known as an Audit Template.

An Audit Template contains at least the Goal of the Audit.

Create Audit Template
=====================

.. rest_method::  POST /v1/audit_templates

Creates a new Audit Template resource.

It requires ``name`` and ``goal`` attributes to be supplied in the request
body.

Normal response codes: 201

Error codes: 400,404,409

Request
-------

.. rest_parameters:: parameters.yaml

   - name: audittemplate_name
   - goal: audittemplate_goal
   - strategy: audittemplate_strategy
   - description: audittemplate_description
   - scope: audittemplate_scope

**Example Audit Template creation request without a specified strategy:**

.. literalinclude:: samples/audittemplate-create-request-minimal.json
   :language: javascript

**Example Audit Template creation request with a specified strategy:**

.. literalinclude:: samples/audittemplate-create-request-full.json
   :language: javascript

Response
--------

The list and example below are representative of the response as of API
version 1:

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audittemplate_name
    - description: audittemplate_description
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - scope: audittemplate_scope
    - links: links

**Example JSON representation of an Audit Template:**

.. literalinclude:: samples/audittemplate-create-response.json
   :language: javascript

List Audit Template
===================

.. rest_method::  GET /v1/audit_templates

Returns a list of Audit Template resources.

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
    - name: audittemplate_name
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - scope: audittemplate_scope
    - links: links

**Example JSON representation of an Audit Template:**

.. literalinclude:: samples/audittemplate-list-response.json
   :language: javascript

List Audit Template Detailed
============================

.. rest_method::  GET /v1/audit_templates/detail

Returns a list of Audit Template resources with complete details.

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
    - name: audittemplate_name
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - scope: audittemplate_scope
    - links: links
    - description: audittemplate_description

**Example JSON representation of an Audit Template:**

.. literalinclude:: samples/audittemplate-list-detailed-response.json
   :language: javascript

Show Audit Template
===================

.. rest_method::  GET /v1/audit_templates/{audittemplate_ident}

Shows details for an Audit Template.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - audittemplate_ident: audittemplate_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audittemplate_name
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - scope: audittemplate_scope
    - links: links
    - description: audittemplate_description

**Example JSON representation of an Audit Template:**

.. literalinclude:: samples/audittemplate-show-response.json
   :language: javascript

Update Audit Template
=====================

.. rest_method::  PATCH /v1/audit_templates/{audittemplate_ident}

Updates an Audit Template with the given information.

Normal response codes: 200

Error codes: 400,404

Request
-------

.. rest_parameters:: parameters.yaml

   - audittemplate_ident: audittemplate_ident

**Example PATCH document updating Audit Template:**

.. literalinclude:: samples/audittemplate-update-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: audittemplate_name
    - strategy_uuid: strategy_uuid
    - strategy_name: strategy_name
    - goal_uuid: goal_uuid
    - goal_name: goal_name
    - scope: audittemplate_scope
    - links: links
    - description: audittemplate_description

**Example JSON representation of an Audit Template:**

.. literalinclude:: samples/audittemplate-update-response.json
   :language: javascript

Delete Audit Template
=====================

.. rest_method::  DELETE /v1/audit_templates/{audittemplate_ident}

Deletes an Audit Template.

Normal response codes: 204

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - audittemplate_ident: audittemplate_ident