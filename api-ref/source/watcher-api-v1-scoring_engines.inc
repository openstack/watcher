.. -*- rst -*-

===============
Scoring Engines
===============

A ``Scoring Engine`` is an executable that has a well-defined input, a
well-defined output, and performs a purely mathematical task. That is,
the calculation does not depend on the environment in which it is running - it
would produce the same result anywhere.

Because there might be multiple algorithms used to build a particular data
model (and therefore a scoring engine), the usage of scoring engine might
vary. A metainfo field is supposed to contain any information which might
be needed by the user of a given scoring engine.

List Scoring Engine
===================

.. rest_method::  GET /v1/scoring_engines

Returns a list of Scoring Engine resources.

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
    - name: scoring_engine_name
    - description: scoring_engine_description
    - links: links

**Example JSON representation of a Scoring Engine:**

.. literalinclude:: samples/scoring_engine-list-response.json
   :language: javascript

List Scoring Engine Detailed
============================

.. rest_method::  GET /v1/scoring_engines/detail

Returns a list of Scoring Engine resources with complete details.

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
    - name: scoring_engine_name
    - description: scoring_engine_description
    - metainfo: scoring_engine_metainfo
    - links: links

**Example JSON representation of a Scoring Engine:**

.. literalinclude:: samples/scoring_engine-list-detailed-response.json
   :language: javascript

Show Scoring Engine
===================

.. rest_method::  GET /v1/scoring_engines/{scoring_engine_ident}

Shows details for a Scoring Engine resource.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - scoring_engine_ident: scoring_engine_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - uuid: uuid
    - name: scoring_engine_name
    - description: scoring_engine_description
    - metainfo: scoring_engine_metainfo
    - links: links

**Example JSON representation of a Scoring Engine:**

.. literalinclude:: samples/scoring_engine-show-response.json
   :language: javascript