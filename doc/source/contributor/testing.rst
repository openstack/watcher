..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

=================
Developer Testing
=================

Watcher has three levels of testing, each serving a different purpose:

- **Unit tests** validate individual components in isolation with extensive
  mocking.
- **Functional tests** run the real Watcher services (API, decision engine,
  applier) together in a single process, exercising the full internal pipeline
  without requiring any external infrastructure.
- **Tempest tests** run against a live OpenStack deployment and validate
  end-to-end behavior across all OpenStack services.

.. _unit_tests:

Unit tests
==========

All unit tests should be run using `tox`_. Before running the unit tests, you
should download the latest `watcher`_ from the github. To run the same unit
tests that are executing onto `Gerrit`_ which includes ``py36``, ``py37`` and
``pep8``, you can issue the following command::

    $ git clone https://opendev.org/openstack/watcher
    $ cd watcher
    $ pip install tox
    $ tox

If you only want to run one of the aforementioned, you can then issue one of
the following::

    $ tox -e py36
    $ tox -e py37
    $ tox -e pep8

.. _tox: https://tox.readthedocs.org/
.. _watcher: https://opendev.org/openstack/watcher
.. _Gerrit: https://review.opendev.org/

If you only want to run specific unit test code and don't like to waste time
waiting for all unit tests to execute, you can add parameters ``--`` followed
by a regex string::

    $ tox -e py37 -- watcher.tests.api

.. _functional_tests:

Functional tests
================

Goals
-----

Functional tests fill the gap between unit tests and Tempest:

- **Unit tests** mock almost everything, so they cannot catch integration bugs
  such as incorrect RPC message formats, database schema mismatches, or broken
  inter-service workflows.
- **Tempest tests** require a full OpenStack deployment, making them slow to
  set up and hard to run during development.

Functional tests give fast, reliable feedback on the real Watcher code paths
without any external infrastructure. They are designed to:

- Validate the full audit lifecycle: audit creation, decision engine strategy
  execution, action plan generation, and applier execution.
- Exercise real database operations (SQLAlchemy + SQLite), real RPC messaging
  (oslo.messaging ``fake:/`` driver), and the real Pecan WSGI application.
- Run entirely in a single process with no network access, completing in
  seconds rather than minutes.

How they differ from unit tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Unit tests
     - Functional tests
   * - Services
     - Mocked
     - Real API, decision engine, and applier running in-process
   * - Database
     - File-backed SQLite with WAL journaling
     - File-backed SQLite with WAL journaling
   * - RPC
     - Mocked
     - Real oslo.messaging with ``fake:/`` transport
   * - API calls
     - Direct method calls with mocked context
     - HTTP requests via ``wsgi-intercept`` with real Pecan app
   * - External services
     - Mocked at various levels
     - Mocked at the client boundary (Nova, Keystone, etc.)
   * - Speed
     - Very fast (milliseconds per test)
     - Fast (seconds per test)

How they differ from Tempest tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Functional tests
     - Tempest tests
   * - Infrastructure
     - None required
     - Full OpenStack deployment
   * - External services
     - Mocked (Nova, Keystone, Gnocchi)
     - Real (Nova, Keystone, Gnocchi, etc.)
   * - Process model
     - Single process, threading mode
     - Multiple processes, real service topology
   * - Typical run time
     - Seconds
     - Minutes

Running functional tests
------------------------

Run all functional tests::

    $ tox -e functional

Run a specific test module::

    $ tox -e functional -- test_basic

Run only gabbi (YAML-driven) tests::

    $ tox -e functional -- test_gabbi

Debugging with log files
~~~~~~~~~~~~~~~~~~~~~~~~

By default, logs are captured in memory and only displayed when a test fails.
To write full DEBUG logs to disk for every test, set the
``WATCHER_FUNC_TEST_LOG_DIR`` environment variable::

    $ WATCHER_FUNC_TEST_LOG_DIR=/tmp/watcher-func-logs tox -e functional

This creates one log file per test in the specified directory (e.g.
``TestAuditLifecycle.test_dummy_audit_end_to_end.log``), containing
interleaved output from all three services — useful for tracing a request
across the API, decision engine, and applier.

You can also enable DEBUG-level output to stderr (shown inline by stestr) with
``OS_DEBUG``::

    $ OS_DEBUG=1 tox -e functional -- test_basic

Architecture
------------

Both Python tests (``WatcherFunctionalTestCase``) and gabbi YAML tests
share the same ``WatcherEnvironment`` fixture
(``watcher/tests/functional/base.py``), which sets up a complete Watcher
environment in a single process:

.. code-block:: text

    ┌─────────────────────────────────────────────────────┐
    │                  Test process                       │
    │                                                     │
    │  ┌──────────────────┐   HTTP (wsgi-intercept)       │
    │  │  Test method      │──────────────────────┐       │
    │  │  (WatcherTest     │                      ▼       │
    │  │   Client)         │            ┌─────────────┐   │
    │  └──────────────────┘            │  Pecan WSGI  │   │
    │                                   │  (watcher-   │   │
    │                                   │   api)       │   │
    │                                   └──────┬──────┘   │
    │                            RPC (fake:/)  │          │
    │                    ┌─────────────────────┘          │
    │                    ▼                                 │
    │  ┌─────────────────────────┐  ┌──────────────────┐  │
    │  │  Decision Engine        │  │  Applier         │  │
    │  │  (strategy execution,   │  │  (action plan    │  │
    │  │   action plan creation) │  │   execution)     │  │
    │  └────────────┬────────────┘  └────────┬─────────┘  │
    │               │                        │            │
    │               ▼                        ▼            │
    │        ┌──────────────────────────────────┐         │
    │        │  SQLite database (file, WAL)     │         │
    │        └──────────────────────────────────┘         │
    └─────────────────────────────────────────────────────┘

Key components:

- **Database**: A per-test file-backed SQLite database with WAL journaling for
  thread-safe concurrent access. The full Watcher schema is created from
  migrations.
- **RPC**: oslo.messaging with the ``fake:/`` in-memory transport driver. The
  ``CastAsCallFixture`` makes RPC ``cast()`` calls synchronous (behave like
  ``call()``) so tests are deterministic.
- **API**: The real Pecan WSGI application served via ``wsgi-intercept``, which
  intercepts HTTP requests from the ``requests`` library without opening real
  sockets. Authentication is disabled; the ``ContextHook`` creates a
  ``RequestContext`` from ``X-User-Id``, ``X-Project-Id``, and ``X-Roles``
  headers sent by the test client.
- **Services**: The decision engine and applier run as in-process RPC servers
  using oslo.service in threading mode. They use the real manager classes
  (``DecisionEngineManager``, ``ApplierManager``) but mock
  ``ServiceHeartbeat`` to avoid unnecessary database writes.
- **External services**: Keystone is mocked via the ``KeystoneClient``
  fixture. Fixtures for Nova, Placement, Cinder and Prometheus APIs will be
  provided. Until the fixutres are provided, the Cluster data model collectors
  are disabled (``collector_plugins = []``) and a fake empty model is provided.

Fixture setup order
~~~~~~~~~~~~~~~~~~~

The order in which fixtures are installed in ``WatcherFunctionalTestCase``
is critical. In particular:

1. The oslo.messaging ``ConfFixture`` (setting ``transport_url = 'fake:/'``)
   **must** be installed before ``ConfReloadFixture``, because the latter
   calls ``config.parse_args()`` which triggers ``rpc.init(CONF)`` and needs
   the fake transport already configured.
2. The database must be provisioned before the ``Syncer`` runs (it populates
   goals and strategies from stevedore plugins into the database).
3. Collectors must be disabled before starting the decision engine service
   (otherwise the ``notification_endpoints`` property attempts to load
   collectors that contact real OpenStack services).

Writing new functional tests
-----------------------------

Basic structure
~~~~~~~~~~~~~~~

Create a new test module in ``watcher/tests/functional/`` and subclass
``WatcherFunctionalTestCase``:

.. code-block:: python

    from watcher.tests.functional import base


    class TestMyFeature(base.WatcherFunctionalTestCase):
        # Control which services start for this test class.
        # Set to False if your test only needs the API.
        START_DECISION_ENGINE = True
        START_APPLIER = True

        def test_something(self):
            # Use self.api (WatcherTestClient) to make HTTP requests.
            resp = self.api.get('/audits')
            self.assertEqual(200, resp.status_code)

            # Use self.api.post() to create resources.
            resp = self.api.post('/audits', {
                'audit_type': 'ONESHOT',
                'goal': 'dummy',
                'strategy': 'dummy',
                'parameters': {'para1': 3.2, 'para2': 'hello'},
            })
            self.assertEqual(201, resp.status_code)

Controlling services
~~~~~~~~~~~~~~~~~~~~

Not every test needs all three services. If your test only validates API
behavior (e.g. input validation, listing resources), disable the decision
engine and applier to speed up setup:

.. code-block:: python

    class TestAPIValidation(base.WatcherFunctionalTestCase):
        START_DECISION_ENGINE = False
        START_APPLIER = False

        def test_invalid_audit_type(self):
            resp = self.api.post('/audits', {
                'audit_type': 'INVALID',
                'goal': 'dummy',
            })
            self.assertEqual(400, resp.status_code)

Disabling synchronous RPC
~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the ``CastAsCallFixture`` makes RPC ``cast()`` calls behave like
synchronous ``call()`` so that tests are deterministic. If your test needs to
exercise asynchronous RPC behavior or disable this feature by any reason, set
``CAST_AS_CALL = False``:

.. code-block:: python

    class TestAsyncBehavior(base.WatcherFunctionalTestCase):
        CAST_AS_CALL = False

        def test_race_condition(self):
            # RPC casts are truly asynchronous here
            ...

Using the test client
~~~~~~~~~~~~~~~~~~~~~

``self.api`` is a ``WatcherTestClient`` instance that provides ``get()``,
``post()``, ``patch()``, and ``delete()`` methods. All requests are
automatically authenticated with fake admin credentials.

A second client, ``self.admin_api``, is also available with explicit admin
role for tests that need to verify role-based access control.

Overriding configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``flags()`` helper to override oslo.config options for the duration
of a single test. The original values are restored automatically on cleanup:

.. code-block:: python

    def test_with_custom_config(self):
        self.flags(weights={'change_nova_service_state': 8},
                   group='watcher_planners.weight')
        # ... test code that depends on the custom config ...

YAML-driven tests with gabbi
-----------------------------

For API workflow tests — request chains that exercise a sequence of HTTP calls
and assert on status codes and JSON response bodies — Watcher uses `gabbi`_,
a declarative YAML-driven HTTP testing framework.

.. _gabbi: https://gabbi.readthedocs.io/

Gabbi tests are ideal when the test is primarily a sequence of API requests
with assertions on the responses. The YAML format makes the request flow
immediately readable and doubles as API contract documentation.

Use Python tests (``WatcherFunctionalTestCase``) when you need complex
assertions, direct database access, or logic that doesn't map well to YAML.

How gabbi tests work
~~~~~~~~~~~~~~~~~~~~

YAML test files live in ``watcher/tests/functional/gabbits/``. The
``test_gabbi.py`` module discovers them via the ``load_tests`` protocol and
builds unittest-compatible test suites that stestr can run.

Each YAML file declares a ``fixtures`` list (referencing ``GabbiFixture``
subclasses) that sets up and tears down the Watcher environment. The
``WatcherGabbiFixture`` in ``gabbi_fixture.py`` starts the same shared
environment (DB, RPC, services) used by Python tests.

Key gabbi features used:

- **``$RESPONSE``** — references a JSONPath value from the previous test's
  response. For example, ``$RESPONSE['$.uuid']`` extracts the UUID returned
  by a POST request.
- **``$HISTORY``** — references a named earlier test's response when
  ``$RESPONSE`` has been overwritten. Syntax:
  ``$HISTORY['test name'].$RESPONSE['$.jsonpath']``.
- **``poll``** — retries a request until assertions pass, with configurable
  ``count`` and ``delay``. Replaces hand-rolled polling loops.
- **``response_json_paths``** — asserts JSONPath expressions against the
  response body. Supports exact values, regex patterns, and length checks.

Adding a new gabbi test
~~~~~~~~~~~~~~~~~~~~~~~

1. Create a new YAML file in ``watcher/tests/functional/gabbits/``
   (e.g. ``api-validation.yaml``).

2. Reference the fixture and set default headers:

   .. code-block:: yaml

       fixtures:
         - WatcherGabbiFixture

       defaults:
         request_headers:
           x-auth-token: fake-token
           x-user-id: fake_user
           x-project-id: fake_project
           x-roles: admin
           content-type: application/json
           accept: application/json

3. Add test steps. Each step is a named HTTP request with assertions:

   .. code-block:: yaml

       tests:
         - name: create an audit
           POST: /audits
           data:
             audit_type: ONESHOT
             goal: dummy
             strategy: dummy
           status: 201
           response_json_paths:
             $.uuid: /^[a-f0-9-]+$/

         - name: wait for audit to finish
           GET: /audits/$RESPONSE['$.uuid']
           poll:
             count: 300
             delay: 0.1
           status: 200
           response_json_paths:
             $.state: SUCCEEDED

4. The new file is automatically discovered — no code changes needed. Run it
   with::

       $ tox -e functional -- test_gabbi

Test ordering and parallelism
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests within a single YAML file run sequentially (required for
``$RESPONSE`` / ``$HISTORY`` chaining). The ``--group-regex`` option in
``tox.ini`` ensures stestr keeps all tests from one YAML file in the same
worker, while allowing different YAML files and Python tests to run in
parallel across workers.

.. _tempest_tests:

Tempest tests
=============

Tempest tests for Watcher has been migrated to the external repo
`watcher-tempest-plugin`_.

.. _watcher-tempest-plugin: https://opendev.org/openstack/watcher-tempest-plugin
