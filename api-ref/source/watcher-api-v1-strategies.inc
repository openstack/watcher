.. -*- rst -*-

==========
Strategies
==========

A ``Strategy`` is an algorithm implementation which is able to find a
``Solution`` for a given ``Goal``. To get more information about strategies
that are shipped along with Watcher, visit `strategies page`_.

There may be several potential strategies which are able to achieve the same
``Goal``. This is why it is possible to configure which specific ``Strategy``
should be used for each goal.

Some strategies may provide better optimization results but may take more time
to find an optimal ``Solution``.

.. _`strategies page`: https://docs.openstack.org/watcher/latest/strategies/index.html

List Strategy
=============

.. rest_method::  GET /v1/strategies

Returns a list of Strategy resources.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - goal: r_goal
   - limit: limit
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: strategy_name
    - display_name: strategy_display_name
    - goal_name: goal_name
    - goal_uuid: goal_uuid
    - links: links

**Example JSON representation of a Strategy:**

.. literalinclude:: samples/strategy-list-response.json
   :language: javascript

List Strategy Detailed
======================

.. rest_method::  GET /v1/strategies/detail

Returns a list of Strategy resources with complete details.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - goal: r_goal
   - limit: limit
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: strategy_name
    - display_name: strategy_display_name
    - parameters_spec: strategy_parameters_spec
    - goal_name: goal_name
    - goal_uuid: goal_uuid
    - links: links

**Example JSON representation of a Strategy:**

.. literalinclude:: samples/strategy-list-detailed-response.json
   :language: javascript

Show Strategy
=============

.. rest_method::  GET /v1/strategies/{strategy_ident}

Shows details for a Strategy resource.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - strategy_ident: strategy_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: strategy_name
    - display_name: strategy_display_name
    - parameters_spec: strategy_parameters_spec
    - goal_name: goal_name
    - goal_uuid: goal_uuid
    - links: links

**Example JSON representation of a Strategy:**

.. literalinclude:: samples/strategy-show-response.json
   :language: javascript

Show Strategy State
===================

.. rest_method::  GET /v1/strategies/{strategy_ident}/state

Retrieve an information about strategy requirements.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - strategy_ident: strategy_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - state: strategy_check_state
    - comment: strategy_check_comment
    - mandatory: strategy_check_mandatory
    - type: strategy_check_type

**Example JSON representation of a Strategy:**

.. literalinclude:: samples/strategy-state-response.json
   :language: javascript