=======================
Using WSGI with Watcher
=======================

.. versionchanged:: 2027.1

    Removed support for the eventlet server script, ``watcher-api``. It was
    built on ``oslo_service.wsgi.Server``, which cannot run under the
    threading service backend. Only WSGI-based deployments are supported
    going forward.

The Watcher API is implemented as a generic Python HTTP server that
implements WSGI_ and is expected to be deployed using a server with WSGI
support.

To facilitate this, Watcher provides a WSGI module that exposes the
``application`` object that most WSGI servers require. It can be found at
``watcher.wsgi.api``. The ``application`` object is automatically configured
from ``watcher.conf``.

Deployment tooling should reference this Python module path,
``watcher.wsgi.api:application``, if the chosen WSGI server supports it
(gunicorn, uWSGI). For servers that require a script on disk instead, such as
Apache ``mod_wsgi``, use the generated ``watcher-api-wsgi`` script or
implement an equivalent ``.wsgi`` script. See :doc:`apache-mod-wsgi` for a
worked ``mod_wsgi`` example.

DevStack deploys the API behind Apache using uwsgi_ via mod_proxy_uwsgi_.
Inspecting the configuration created there can provide some guidance on one
option for managing the WSGI application. It is important to remember,
however, that one of the major features of using WSGI is that there are many
different ways to host a WSGI application. Different servers make different
choices about performance and configurability. It is up to you, as a
deployer, to choose an appropriate server for your deployment.

.. note::

    The ``[api] host``, ``[api] port``, ``[api] workers`` and
    ``[api] enable_ssl_api`` configuration options have been removed. The
    listen address, listen port, worker count and TLS termination are
    configured in the WSGI server instead.

.. _WSGI: https://www.python.org/dev/peps/pep-3333/
.. _uwsgi: https://uwsgi-docs.readthedocs.io/
.. _mod_proxy_uwsgi: http://uwsgi-docs.readthedocs.io/en/latest/Apache.html#mod-proxy-uwsgi
