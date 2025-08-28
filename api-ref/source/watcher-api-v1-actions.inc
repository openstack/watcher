.. -*- rst -*-

=======
Actions
=======

An ``Action`` is what enables Watcher to transform the current state of a
``Cluster`` after an ``Audit``.

An ``Action`` is an atomic task which changes the current state of a target
Managed resource of the OpenStack ``Cluster`` such as:

-  Live migration of an instance from one compute node to another compute
   node with Nova
-  Changing the power level of a compute node (ACPI level, ...)
-  Changing the current state of a compute node (enable or disable) with Nova

In most cases, an ``Action`` triggers some concrete commands on an existing
OpenStack module (Nova, Neutron, Cinder, Ironic, etc.).

An ``Action`` has a life-cycle and its current state may be one of the
following:

-  **PENDING** : the ``Action`` has not been executed yet by the
   ``Watcher Applier``.
-  **SKIPPED** : the ``Action`` will not be executed because a predefined
   skipping condition is found by ``Watcher Applier`` or is explicitly
   skipped by the ``Administrator``.
-  **ONGOING** : the ``Action`` is currently being processed by the
   ``Watcher Applier``.
-  **SUCCEEDED** : the ``Action`` has been executed successfully
-  **FAILED** : an error occurred while trying to execute the ``Action``.
-  **DELETED** : the ``Action`` is still stored in the ``Watcher database``
   but is not returned any more through the Watcher APIs.
-  **CANCELLED** : the ``Action`` was in **PENDING** or **ONGOING** state and
   was cancelled by the ``Administrator``

``Actions`` are created by ``Watcher Planner`` as result of Audit's execution.
``Action`` can't be created, modified or deleted by user.

List Action
===========

.. rest_method::  GET /v1/actions

Returns a list of Action resources.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - action_plan_uuid: r_action_plan
   - audit_uuid: r_audit
   - limit: limit
   - marker: marker
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - action_type: action_type
    - state: action_state
    - action_plan_uuid: action_action_plan_uuid
    - parents: action_parents
    - links: links

**Example JSON representation of an Action:**

.. literalinclude:: samples/actions-list-response.json
   :language: javascript

List Action Detailed
====================

.. rest_method::  GET /v1/actions/detail

Returns a list of Action resources with complete details.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - action_plan_uuid: r_action_plan
   - audit_uuid: r_audit
   - limit: limit
   - marker: marker
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - action_type: action_type
    - state: action_state
    - action_plan_uuid: action_action_plan_uuid
    - parents: action_parents
    - description: action_description
    - input_parameters: action_input_parameters
    - links: links
    - status_message: action_status_message

**Example JSON representation of an Action:**

.. literalinclude:: samples/actions-list-detailed-response.json
   :language: javascript

Show Action
===========

.. rest_method::  GET /v1/actions/{action_ident}

Shows details for an Action.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - action_ident: action_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - action_type: action_type
    - state: action_state
    - action_plan_uuid: action_action_plan_uuid
    - parents: action_parents
    - description: action_description
    - input_parameters: action_input_parameters
    - links: links
    - status_message: action_status_message

**Example JSON representation of an Action:**

.. literalinclude:: samples/actions-show-response.json
   :language: javascript

Skip Action
===========

.. rest_method::  PATCH /v1/actions/{action_ident}

Skips an Action resource by changing its state to SKIPPED.

.. note::
    Only Actions in PENDING state can be skipped. The Action must belong to
    an Action Plan in RECOMMENDED or PENDING state. This operation requires
    API microversion 1.5 or later.

Normal response codes: 200

Error codes: 400,404,403,409

Request
-------

.. rest_parameters:: parameters.yaml

   - action_ident: action_ident

**Example Action skip request:**

.. literalinclude:: samples/action-skip-request.json
   :language: javascript

**Example Action skip request with custom status message:**

.. literalinclude:: samples/action-skip-request-with-message.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - action_type: action_type
    - state: action_state
    - action_plan_uuid: action_action_plan_uuid
    - parents: action_parents
    - description: action_description
    - input_parameters: action_input_parameters
    - links: links
    - status_message: action_status_message

**Example JSON representation of a skipped Action:**

.. literalinclude:: samples/action-skip-response.json
   :language: javascript

Update Action Status Message
============================

.. rest_method::  PATCH /v1/actions/{action_ident}

Updates the status_message of an Action that is already in SKIPPED state.

.. note::
    The status_message field can only be updated for Actions that are currently
    in SKIPPED state. This allows administrators to fix typos, provide more
    detailed explanations, or expand on reasons that were initially omitted.
    This operation requires API microversion 1.5 or later.

Normal response codes: 200

Error codes: 400,404,403,409

Request
-------

.. rest_parameters:: parameters.yaml

   - action_ident: action_ident

**Example status_message update request for a SKIPPED action:**

.. literalinclude:: samples/action-update-status-message-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - action_type: action_type
    - state: action_state
    - action_plan_uuid: action_action_plan_uuid
    - parents: action_parents
    - description: action_description
    - input_parameters: action_input_parameters
    - links: links
    - status_message: action_status_message

**Example JSON representation of an Action with updated status_message:**

.. literalinclude:: samples/action-update-status-message-response.json
   :language: javascript