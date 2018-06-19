.. -*- rst -*-

========
Services
========

This resource represents Watcher services, their states and hosts they are
placed on.

List Service
============

.. rest_method::  GET /v1/services

Returns a list of Service resources.

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

    - id: service_id
    - name: service_name
    - host: service_host
    - status: service_status
    - links: links

**Example JSON representation of a Service:**

.. literalinclude:: samples/service-list-response.json
   :language: javascript

List Service Detailed
=====================

.. rest_method::  GET /v1/services/detail

Returns a list of Service resources with complete details.

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

    - id: service_id
    - name: service_name
    - host: service_host
    - status: service_status
    - last_seen_up: service_last_seen_up
    - links: links

**Example JSON representation of a Service:**

.. literalinclude:: samples/service-list-detailed-response.json
   :language: javascript

Show Service
============

.. rest_method::  GET /v1/services/{service_ident}

Shows details for a Service resource.

Normal response codes: 200

Error codes: 404

Request
-------

.. rest_parameters:: parameters.yaml

   - service_ident: service_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - id: service_id
    - name: service_name
    - host: service_host
    - status: service_status
    - last_seen_up: service_last_seen_up
    - links: links

**Example JSON representation of a Service:**

.. literalinclude:: samples/service-show-response.json
   :language: javascript