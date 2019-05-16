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
