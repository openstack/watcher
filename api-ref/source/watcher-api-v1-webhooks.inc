.. -*- rst -*-

========
Webhooks
========

.. versionadded:: 1.4

Triggers an event based Audit.


Trigger EVENT Audit
===================

.. rest_method::  POST /v1/webhooks/{audit_ident}

Normal response codes: 202

Error codes: 400,404

Request
-------

.. rest_parameters:: parameters.yaml

   - audit_ident: audit_ident
