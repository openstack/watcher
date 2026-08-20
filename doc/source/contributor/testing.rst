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
  fixture. Nova and Placement are emulated in-process (see
  `Tests with cluster topology (Nova/Placement emulators)`_).
  When ``COMPUTE_TOPOLOGY`` is not set on the test class, collectors
  are disabled (``collector_plugins = []``) and a fake empty model is
  provided.

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

Tests with cluster topology (Nova/Placement emulators)
------------------------------------------------------

Many Watcher strategies (e.g. ``host_maintenance``, ``workload_balance``)
need a realistic cluster data model to produce meaningful action plans.
The functional test framework provides in-process Nova and Placement API
emulators that can be loaded with arbitrary topologies — no real OpenStack
services required.

How the emulators work
~~~~~~~~~~~~~~~~~~~~~~

The ``NovaAPIEmulator`` and ``PlacementAPIEmulator`` (in
``watcher/tests/local_fixtures/``) are lightweight Flask apps that serve the
subset of Nova v2.1 and Placement APIs that Watcher's collectors and
actions use. They are wired into the test process via ``wsgi-intercept``
so that all HTTP requests from openstacksdk and keystoneauth1 are routed
in-process.

The ``NovaPlacementFixture`` (in ``watcher/tests/local_fixtures/nova.py``)
handles the wiring: it creates both emulators, installs the WSGI
intercepts, and patches ``OpenStackClients`` so the decision engine's
collectors build a real cluster data model from the emulated APIs.

Defining topology with dataclasses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Topologies are defined using typed dataclass objects from
``watcher.tests.functional.topology``. Each dataclass has sensible defaults
matching the emulator defaults, so tests only need to specify the fields
that matter for their scenario:

.. code-block:: python

    from watcher.tests.functional import base
    from watcher.tests.functional import topology


    MY_TOPOLOGY = (
        topology.ComputeTopology()
        .add_computes(count=2)
        .add_instances(computes=['compute-1'], count=2, vcpus=2)
        .add_instances(computes=['compute-2'], count=1, vcpus=2)
    )


    class TestMyStrategy(base.WatcherFunctionalTestCase):
        COMPUTE_TOPOLOGY = topology.ComputeTopology()

        def test_something(self):
            self.load_topology(MY_TOPOLOGY)
            # ... create audit, wait for result, assert actions ...

Setting ``COMPUTE_TOPOLOGY = ComputeTopology()`` on the test class enables
the emulators with an empty initial topology. Each test method then
calls ``self.load_topology()`` to set its own cluster state. This means
different tests in the same class can use different topologies.

The ``ComputeTopology`` dataclass groups compute nodes, instances, and
aggregates into a single object, simplifying topology definition and
the ``load_topology()`` call.

Builder pattern
^^^^^^^^^^^^^^^

``ComputeTopology`` supports builder-pattern chaining via
``add_computes``, ``add_instances``, ``update_compute``, and
``update_instance`` methods.  Each method returns ``self``, so calls
can be chained:

.. code-block:: python

    from watcher.tests.functional import topology

    topo = (
        topology.ComputeTopology()
        .add_computes(count=2, vcpus=64, memory=131072, disk=2000)
        .add_instances(computes=['compute-1'], count=5, vcpus=2)
        .add_instances(computes=['compute-1'], count=3, vcpus=2,
                       state='stopped')
    )

``.add_computes(count, hostname_prefix='compute', **kwargs)``
    Appends *count* compute nodes.  Hostnames are
    ``{hostname_prefix}-{N}`` where N continues from existing nodes
    with the same prefix.  Extra ``**kwargs`` are forwarded to
    ``ComputeNode``.

``.add_instances(computes, count, name_prefix='vm', **kwargs)``
    Appends *count* instances **per compute node**.  *computes* is a
    list of hostnames or ``'all'`` to target every node.  Names are
    ``{name_prefix}-{M}`` with global sequential numbering.  Extra
    ``**kwargs`` are forwarded to ``Instance``.

``.update_compute(hostname, **kwargs)``
    Modify fields on an existing compute node by hostname.

``.update_instance(name, **kwargs)``
    Modify fields on an existing instance by name.

These methods cover the common case.  For topologies with per-instance
variation (BFV, ephemeral/swap, multiple projects), construct
``ComputeNode`` and ``Instance`` objects directly.

ComputeNode fields
^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 50

   * - Field
     - Default
     - Description
   * - ``hostname``
     - *(required)*
     - Compute node hostname
   * - ``uuid``
     - auto-generated
     - Resource provider UUID
   * - ``vcpus``
     - 16
     - Total VCPUs
   * - ``memory``
     - 32768
     - Total memory in MB
   * - ``disk``
     - 500
     - Total disk in GB
   * - ``state``
     - ``'up'``
     - Service state (``up`` or ``down``)
   * - ``status``
     - ``'enabled'``
     - Service status (``enabled`` or ``disabled``)
   * - ``disabled_reason``
     - ``None``
     - Reason string when service status is ``disabled``
   * - ``availability_zone``
     - ``'nova'``
     - Service availability zone
   * - ``vcpu_ratio``
     - 1.0
     - Placement allocation ratio for VCPU
   * - ``memory_ratio``
     - 1.0
     - Placement allocation ratio for MEMORY_MB
   * - ``disk_ratio``
     - 1.0
     - Placement allocation ratio for DISK_GB
   * - ``vcpu_reserved``
     - 0
     - Reserved VCPUs in Placement inventory
   * - ``memory_mb_reserved``
     - 0
     - Reserved memory (MB) in Placement inventory
   * - ``disk_gb_reserved``
     - 0
     - Reserved disk (GB) in Placement inventory

Instance fields
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 50

   * - Field
     - Default
     - Description
   * - ``uuid``
     - auto-generated
     - Instance UUID
   * - ``name``
     - ``''``
     - Instance display name (defaults to ``instance-<uuid[:8]>`` in emulator)
   * - ``host``
     - ``''``
     - Hostname of the compute node running this instance
   * - ``vcpus``
     - 4
     - VCPUs consumed
   * - ``memory``
     - 4096
     - Memory consumed (MB)
   * - ``disk``
     - 20
     - Disk consumed (GB)
   * - ``state``
     - ``'active'``
     - VM state (``active``, ``stopped``, etc.)
   * - ``project_id``
     - ``'test-project'``
     - Tenant/project ID
   * - ``hypervisor_hostname``
     - ``None`` (defaults to ``host``)
     - Hypervisor hostname (``OS-EXT-SRV-ATTR:hypervisor_hostname``)
   * - ``locked``
     - ``False``
     - Whether the instance is locked
   * - ``metadata``
     - ``{}``
     - Instance metadata dict (used by scope ``instance_metadata`` filter)
   * - ``ephemeral``
     - 0
     - Ephemeral disk (GB), added to flavor
   * - ``swap``
     - 0
     - Swap disk (MB), added to flavor
   * - ``created``
     - ``'2025-01-01T00:00:00Z'``
     - Server creation timestamp
   * - ``bfv``
     - ``False``
     - Boot from volume. See `Boot from volume (BFV) instances`_ below.
   * - ``availability_zone``
     - ``'nova'``
     - Availability zone (``OS-EXT-AZ:availability_zone``)
   * - ``volumes_attached``
     - ``[]``
     - List of attached volume dicts

Aggregate fields
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 50

   * - Field
     - Default
     - Description
   * - ``id``
     - *(required)*
     - Aggregate ID
   * - ``name``
     - *(required)*
     - Aggregate name
   * - ``hosts``
     - ``[]``
     - List of compute node hostnames in this aggregate
   * - ``metadata``
     - ``{}``
     - Aggregate metadata dict

ComputeTopology fields
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 50

   * - Field
     - Default
     - Description
   * - ``compute_nodes``
     - ``[]``
     - List of ``ComputeNode`` objects
   * - ``instances``
     - ``[]``
     - List of ``Instance`` objects
   * - ``aggregates``
     - ``[]``
     - List of ``Aggregate`` objects

Boot from volume (BFV) instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``bfv`` is ``True``, the emulators reproduce the behavior of a
real Nova/Placement deployment for boot-from-volume instances:

- **Nova API**: The server's ``image`` field is ``""`` (empty string).
  openstacksdk converts this to ``image=None``, which makes
  ``Server.is_boot_from_volume`` return ``True``.
- **Placement API**: The root disk is excluded from the ``DISK_GB``
  allocation. Only ``ephemeral`` and ``swap`` (converted to GB with
  ``math.ceil``) contribute to ``DISK_GB`` usage and allocations.
- **Cluster data model**: The model builder sets
  ``instance.disk = ephemeral + ceil(swap_mb / 1024)`` (no root disk),
  matching the Placement allocation.

When ``bfv`` is ``False`` (the default), the server has a fake image UUID
and the full ``disk`` value is included in the ``DISK_GB`` allocation.

The ``disk`` field in the instance dict always represents the flavor's
root disk size, regardless of ``bfv``. This is the same value that
appears in the Nova flavor response. For BFV instances the root disk is
stored on a Cinder volume, so it does not consume local disk on the
compute node — the emulators handle this automatically.

Example with mixed BFV and image-backed instances:

.. code-block:: python

    from watcher.tests.functional import topology

    INSTANCES = [
        # Image-backed: DISK_GB = 20 + 0 + 0 = 20
        topology.Instance(
            uuid='11111111-1111-1111-1111-111111111111',
            name='vm-image', host='compute-1',
            vcpus=2, disk=20,
        ),
        # BFV, no ephemeral/swap: DISK_GB = 0
        topology.Instance(
            uuid='22222222-2222-2222-2222-222222222222',
            name='vm-bfv', host='compute-1',
            vcpus=2, disk=80,
            bfv=True,
        ),
        # BFV with ephemeral and swap:
        # DISK_GB = 0 + 10 + ceil(512/1024) = 11
        topology.Instance(
            uuid='33333333-3333-3333-3333-333333333333',
            name='vm-bfv-eph', host='compute-1',
            vcpus=4, memory=8192, disk=80,
            ephemeral=10, swap=512,
            bfv=True,
        ),
    ]

In XML model files, use the ``bfv="True"`` attribute on ``<Instance>``
elements:

.. code-block:: xml

    <Instance uuid="INST_1" name="vm-bfv" vcpus="2" memory="4096"
              disk="80" state="active" bfv="True" />

Loading topology from XML or JSON files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both emulators can also load topology from XML model files (the same
format used by Watcher's unit test scenarios in
``watcher/tests/unit/decision_engine/model/data/``) or from JSON files.
This is mainly intended for running the emulators in standalone mode
(see `Running the emulators standalone`_), where topology is provided
via command-line flags rather than constructed in Python.

In functional tests, prefer defining topologies using the builder helpers
or dataclass objects described above — they are type-checked, support
IDE autocompletion, and produce more readable test code.

The XML format uses ``<ComputeNode>`` elements with nested ``<Instance>``
elements:

.. code-block:: xml

    <ModelRoot>
      <ComputeNode uuid="Node_0" hostname="hostname_0"
                   vcpus="40" memory="132" disk="250"
                   vcpu_ratio="1" memory_ratio="1" disk_ratio="1"
                   vcpu_reserved="0" memory_mb_reserved="0" disk_gb_reserved="0"
                   status="enabled" state="up">
        <Instance uuid="INSTANCE_0" name="vm-0"
                  vcpus="10" memory="2" disk="20"
                  state="active" project_id="project-1" />
      </ComputeNode>
    </ModelRoot>

The Placement emulator extracts the allocation ratios and reserved values
from the XML, while the Nova emulator extracts hypervisor and server state.

The JSON format uses a flat structure with ``compute_nodes``, ``instances``,
and ``aggregates`` lists:

.. code-block:: json

    {
        "compute_nodes": [
            {"uuid": "...", "hostname": "compute-1", "vcpus": 16,
             "memory": 32768, "disk": 500}
        ],
        "instances": [
            {"uuid": "...", "name": "vm-1", "host": "compute-1",
             "vcpus": 2, "memory": 4096, "disk": 20, "state": "active",
             "project_id": "..."}
        ],
        "aggregates": [
            {"id": 1, "name": "rack-a", "hosts": ["compute-1"]}
        ]
    }

Per-test topology loading
~~~~~~~~~~~~~~~~~~~~~~~~~

When ``COMPUTE_TOPOLOGY = ComputeTopology()`` is set on the test class,
each test method can call ``self.load_topology()`` with a different
``ComputeTopology``. This resets both the Nova and Placement emulators
and loads the new data:

.. code-block:: python

    from watcher.tests.functional import topology

    SMALL_TOPOLOGY = (
        topology.ComputeTopology()
        .add_computes(count=1, hostname_prefix='node')
        .add_instances(computes='all', count=1)
    )

    LARGE_TOPOLOGY = (
        topology.ComputeTopology()
        .add_computes(count=3, hostname_prefix='node')
        .add_instances(computes=['node-1', 'node-2'], count=1)
    )


    class TestScaling(base.WatcherFunctionalTestCase):
        COMPUTE_TOPOLOGY = topology.ComputeTopology()

        def test_small_cluster(self):
            self.load_topology(SMALL_TOPOLOGY)
            # ...

        def test_large_cluster(self):
            self.load_topology(LARGE_TOPOLOGY)
            # ...

This is preferred over defining a full topology at the class level,
because it allows different test methods to exercise different scenarios
without needing separate test classes.

Gabbi tests with topology
~~~~~~~~~~~~~~~~~~~~~~~~~

For gabbi YAML tests that need a cluster topology, use a fixture that
subclasses ``_GabbiTopologyFixtureBase`` instead of ``WatcherGabbiFixture``.
Each subclass defines a ``COMPUTE_TOPOLOGY`` class attribute and can be
referenced by name in the YAML ``fixtures:`` list.

For example, the ``WatcherGabbiWithTopologyFixture`` provides a 3-node cluster
(two instances on compute-1, one on compute-2, none on compute-3):

.. code-block:: yaml

    fixtures:
      - WatcherGabbiWithTopologyFixture

To add a different topology for a new gabbi test file, define a new
subclass in ``gabbi_fixture.py``:

.. code-block:: python

    class MyTopologyFixture(_GabbiTopologyFixtureBase):
        COMPUTE_TOPOLOGY = (
            topology.ComputeTopology()
            .add_computes(count=2, vcpus=8)
            .add_instances(computes='all', count=3, vcpus=2)
        )

Then reference it in the YAML file:

.. code-block:: yaml

    fixtures:
      - MyTopologyFixture

Gabbi resolves fixture class names from the ``gabbi_fixture`` module, so
any class defined there is automatically available to YAML files.

Running the emulators standalone
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both emulators can also run as standalone Flask servers for manual testing
or debugging outside the test framework.  Use ``tox -e venv`` to run them
in an environment with all dependencies installed.  The ``--model`` flag
accepts both XML and JSON files — the format is auto-detected from file
content::

    $ tox -e venv -- python -m watcher.tests.local_fixtures.nova_api_emulator \
        --model watcher/tests/unit/decision_engine/model/data/scenario_1.xml \
        --port 8774 --debug

    $ tox -e venv -- python -m watcher.tests.local_fixtures.placement_api_emulator \
        --model watcher/tests/unit/decision_engine/model/data/scenario_1.xml \
        --port 8778 --debug

JSON topology files work the same way::

    $ tox -e venv -- python -m watcher.tests.local_fixtures.nova_api_emulator \
        --model path/to/topology.json --port 8774

    $ tox -e venv -- python -m watcher.tests.local_fixtures.placement_api_emulator \
        --model path/to/topology.json --port 8778

To serve over HTTPS, provide both ``--cert`` and ``--key``::

    $ tox -e venv -- python -m watcher.tests.local_fixtures.nova_api_emulator \
        --model scenario_1.xml --port 8774 \
        --cert /path/to/server.crt --key /path/to/server.key

    $ tox -e venv -- python -m watcher.tests.local_fixtures.placement_api_emulator \
        --model scenario_1.xml --port 8778 \
        --cert /path/to/server.crt --key /path/to/server.key

Both TLS flags must be provided together; passing only one is an error.
This is useful when testing Watcher against emulators configured with TLS
endpoints (e.g. ``https://localhost:8774/v2.1``).

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
