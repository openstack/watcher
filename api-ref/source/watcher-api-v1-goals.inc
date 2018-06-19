.. -*- rst -*-

=====
Goals
=====

A ``Goal`` is a human readable, observable and measurable end result having
one objective to be achieved.

Here are some examples of ``Goals``:

-  minimize the energy consumption
-  minimize the number of compute nodes (consolidation)
-  balance the workload among compute nodes
-  minimize the license cost (some softwares have a licensing model which is
   based on the number of sockets or cores where the software is deployed)
-  find the most appropriate moment for a planned maintenance on a
   given group of host (which may be an entire availability zone):
   power supply replacement, cooling system replacement, hardware
   modification, ...

List Goal
=========

.. rest_method::  GET /v1/goals

Returns a list of Goal resources.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - limit: limit
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - efficacy_specification: goal_efficacy_specification
    - name: goal_name
    - display_name: goal_display_name
    - links: links

**Example JSON representation of a Goal:**

.. literalinclude:: samples/goal-list-response.json
   :language: javascript

List Goal Detailed
==================

.. rest_method::  GET /v1/goals/detail

Returns a list of Goal resources with complete details.

Normal response codes: 200

Error codes: 400,401

Request
-------

.. rest_parameters:: parameters.yaml

   - limit: limit
   - sort_dir: sort_dir
   - sort_key: sort_key

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - efficacy_specification: goal_efficacy_specification
    - name: goal_name
    - display_name: goal_display_name
    - links: links

**Example JSON representation of a Goal:**

.. literalinclude:: samples/goal-list-response.json
   :language: javascript

Show Goal
=========

.. rest_method::  GET /v1/goals/{goal_ident}

Shows details for an Goal.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - goal_ident: goal_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - efficacy_specification: goal_efficacy_specification
    - name: goal_name
    - display_name: goal_display_name
    - links: links

**Example JSON representation of a Goal:**

.. literalinclude:: samples/goal-show-response.json
   :language: javascript