REST API Version History
========================

This documents the changes made to the REST API with every
microversion change. The description for each version should be a
verbose one which has enough information to be suitable for use in
user documentation.

1.0 (Initial version)
-----------------------
This is the initial version of the Watcher API which supports
microversions.

A user can specify a header in the API request::

  OpenStack-API-Version: infra-optim <version>

where ``<version>`` is any valid api version for this API.

If no version is specified then the API will behave as if version 1.0
was requested.

1.1
---
Added the parameters ``start_time`` and ``end_time`` to
create audit request. Supported for start and end time of continuous
audits.

1.2
---
Added ``force`` into create audit request. If ``force`` is true,
audit will be executed despite of ongoing actionplan.

1.3
---
Added list data model API.

1.4
---
Added Watcher webhook API. It can be used to trigger audit
with ``event`` type.

1.5
---
Added support for SKIPPED actions status via PATCH support for Actions API.
This feature also introduces the ``status_message`` field to audits, actions
and action plans. The ``status_message`` field can be set when transitioning
an action to SKIPPED state, and can also be updated for actions that are
already in SKIPPED state, allowing administrators to fix typos, provide more
detailed explanations, or expand on reasons that were initially omitted.

1.6 (Maximum in 2025.2 Flamingo)
---
Added new server attributes, ``server_flavor_extra_specs`` and
``server_pinned_az``, to the response of ``GET /v1/data_model`` API when
selecting ``compute`` as the ``data_model_type`` parameter. The collection of
these extended attributes is controlled by
``[compute_model] enable_extended_attributes`` configuration option.
