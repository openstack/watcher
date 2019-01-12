.. -*- rst -*-

============
API versions
============

In order to bring new features to users over time, the Watcher API
supports versioning. There are two kinds of versions in Watcher.

- ''major versions'', which have dedicated URLs.
- ''microversions'', which can be requested using the
  ``OpenStack-API-Version`` header.

.. note:: The maximum microversion depends on release.
  Please reference:
  `API Microversion History
  <https://docs.openstack.org/watcher/latest/contributor/api_microversion_history.html>`__
  for API microversion history details.

The Version API resource works differently from other API resources as they *do not*
require authentication.

If Watcher receives a request with unsupported version, it responds with a 406 Not Acceptable,
along with the -Min- and -Max- headers that it can support.

List API versions
=================

.. rest_method::  GET /

This fetches all the information about all known major API versions in the
deployment. Links to more specific information will be provided for each major
API version, as well as information about supported min and max microversions.

Normal response codes: 200

Request
-------

Response Example
----------------

.. rest_parameters::  parameters.yaml

    - description: version_description
    - versions: versions
    - version: version
    - id: version_id
    - links: links
    - min_version: openstack-api-min-version
    - max_version: openstack-api-max-version

.. literalinclude:: samples/api-root-response.json
   :language: javascript


Show v1 API
===========

.. rest_method::  GET /v1/

Show all the resources within the Watcher v1 API.

Normal response codes: 200

Request
-------

Response Example
----------------

.. rest_parameters::  parameters.yaml

    - id: version_id
    - links: links
    - OpenStack-API-Version: header_version
    - OpenStack-API-Minimum-Version: openstack-api-min-version
    - OpenStack-API-Maximum-Version: openstack-api-max-version

.. literalinclude:: samples/api-v1-root-response.json
   :language: javascript
