.. -*- rst -*-

==========
Data Model
==========

.. versionadded:: 1.3

``Data Model`` is very important for Watcher to generate resource
optimization solutions. Users can easily view the data model by the
API.


List Data Model
===============

.. rest_method::  GET /v1/data_model

Returns the information about Data Model.

Normal response codes: 200

Error codes: 400,401,406

Request
-------

.. rest_parameters:: parameters.yaml

   - audit: r_audit
   - type: r_type

Response
--------

.. rest_parameters:: parameters.yaml

    - server_watcher_exclude: server_watcher_exclude
    - server_name: server_name
    - server_state: server_state
    - server_memory: server_memory
    - server_disk: server_disk
    - server_vcpus: server_vcpus
    - server_metadata: server_metadata
    - server_project_id: server_project_id
    - server_locked: server_locked
    - server_uuid: server_uuid
    - node_hostname: node_hostname
    - node_status: node_status
    - node_disabled_reason: node_disabled_reason
    - node_state: node_state
    - node_memory: node_memory
    - node_memory_mb_reserved: node_memory_mb_reserved
    - node_disk: node_disk
    - node_disk_gb_reserved: node_disk_gb_reserved
    - node_vcpus: node_vcpus
    - node_vcpu_reserved: node_vcpu_reserved
    - node_memory_ratio: node_memory_ratio
    - node_vcpu_ratio: node_vcpu_ratio
    - node_disk_ratio: node_disk_ratio
    - node_uuid: node_uuid

**Example JSON representation of a Data Model:**

.. literalinclude:: samples/datamodel-list-response.json
   :language: javascript
