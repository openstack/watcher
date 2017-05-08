.. _verify:

Verify operation
~~~~~~~~~~~~~~~~

Verify operation of the Infrastructure Optimization service.

.. note::

   Perform these commands on the controller node.

1. Source the ``admin`` project credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

2. List service components to verify successful launch and registration
   of each process:

   .. code-block:: console

      $ openstack optimize service list
        +----+-------------------------+------------+--------+
        | ID | Name                    | Host       | Status |
        +----+-------------------------+------------+--------+
        |  1 | watcher-decision-engine | controller | ACTIVE |
        |  2 | watcher-applier         | controller | ACTIVE |
        +----+-------------------------+------------+--------+

3. List goals and strategies:

   .. code-block:: console

      $ openstack optimize goal list
        +--------------------------------------+----------------------+----------------------+
        | UUID                                 | Name                 | Display name         |
        +--------------------------------------+----------------------+----------------------+
        | a8cd6d1a-008b-4ff0-8dbc-b30493fcc5b9 | dummy                | Dummy goal           |
        | 03953f2f-02d0-42b5-9a12-7ba500a54395 | workload_balancing   | Workload Balancing   |
        | de0f8714-984b-4d6b-add1-9cad8120fbce | server_consolidation | Server Consolidation |
        | f056bc80-c6d1-40dc-b002-938ccade9385 | thermal_optimization | Thermal Optimization |
        | e7062856-892e-4f0f-b84d-b828464b3fd0 | airflow_optimization | Airflow Optimization |
        | 1f038da9-b36c-449f-9f04-c225bf3eb478 | unclassified         | Unclassified         |
        +--------------------------------------+----------------------+----------------------+

      $ openstack optimize strategy list
      +--------------------------------------+---------------------------+---------------------------------------------+----------------------+
      | UUID                                 | Name                      | Display name                                | Goal                 |
      +--------------------------------------+---------------------------+---------------------------------------------+----------------------+
      | 98ae84c8-7c9b-4cbd-8d9c-4bd7c6b106eb | dummy                     | Dummy strategy                              | dummy                |
      | 02a170b6-c72e-479d-95c0-8a4fdd4cc1ef | dummy_with_scorer         | Dummy Strategy using sample Scoring Engines | dummy                |
      | 8bf591b8-57e5-4a9e-8c7d-c37bda735a45 | outlet_temperature        | Outlet temperature based strategy           | thermal_optimization |
      | 8a0810fb-9d9a-47b9-ab25-e442878abc54 | vm_workload_consolidation | VM Workload Consolidation Strategy          | server_consolidation |
      | 1718859c-3eb5-45cb-9220-9cb79fe42fa5 | basic                     | Basic offline consolidation                 | server_consolidation |
      | b5e7f5f1-4824-42c7-bb52-cf50724f67bf | workload_stabilization    | Workload stabilization                      | workload_balancing   |
      | f853d71e-9286-4df3-9d3e-8eaf0f598e07 | workload_balance          | Workload Balance Migration Strategy         | workload_balancing   |
      | 58bdfa89-95b5-4630-adf6-fd3af5ff1f75 | uniform_airflow           | Uniform airflow migration strategy          | airflow_optimization |
      | 66fde55d-a612-4be9-8cb0-ea63472b420b | dummy_with_resize         | Dummy strategy with resize                  | dummy                |
      +--------------------------------------+---------------------------+---------------------------------------------+----------------------+

4. Run an action plan by creating an audit with dummy goal:

   .. code-block:: console

      $ openstack optimize audit create --goal dummy
        +--------------+--------------------------------------+
        | Field        | Value                                |
        +--------------+--------------------------------------+
        | UUID         | e94d4826-ad4e-44df-ad93-dff489fde457 |
        | Created At   | 2017-05-23T11:46:58.763394+00:00     |
        | Updated At   | None                                 |
        | Deleted At   | None                                 |
        | State        | PENDING                              |
        | Audit Type   | ONESHOT                              |
        | Parameters   | {}                                   |
        | Interval     | None                                 |
        | Goal         | dummy                                |
        | Strategy     | auto                                 |
        | Audit Scope  | []                                   |
        | Auto Trigger | False                                |
        +--------------+--------------------------------------+

      $ openstack optimize audit list
        +--------------------------------------+------------+-----------+-------+----------+--------------+
        | UUID                                 | Audit Type | State     | Goal  | Strategy | Auto Trigger |
        +--------------------------------------+------------+-----------+-------+----------+--------------+
        | e94d4826-ad4e-44df-ad93-dff489fde457 | ONESHOT    | SUCCEEDED | dummy | auto     | False        |
        +--------------------------------------+------------+-----------+-------+----------+--------------+

      $ openstack optimize actionplan list
        +--------------------------------------+--------------------------------------+-------------+------------+-----------------+
        | UUID                                 | Audit                                | State       | Updated At | Global efficacy |
        +--------------------------------------+--------------------------------------+-------------+------------+-----------------+
        | ba9ce6b3-969c-4b8e-bb61-ae24e8630f81 | e94d4826-ad4e-44df-ad93-dff489fde457 | RECOMMENDED | None       | None            |
        +--------------------------------------+--------------------------------------+-------------+------------+-----------------+

     $ openstack optimize actionplan start ba9ce6b3-969c-4b8e-bb61-ae24e8630f81
       +---------------------+--------------------------------------+
       | Field               | Value                                |
       +---------------------+--------------------------------------+
       | UUID                | ba9ce6b3-969c-4b8e-bb61-ae24e8630f81 |
       | Created At          | 2017-05-23T11:46:58+00:00            |
       | Updated At          | 2017-05-23T11:53:12+00:00            |
       | Deleted At          | None                                 |
       | Audit               | e94d4826-ad4e-44df-ad93-dff489fde457 |
       | Strategy            | dummy                                |
       | State               | ONGOING                              |
       | Efficacy indicators | []                                   |
       | Global efficacy     | {}                                   |
       +---------------------+--------------------------------------+

     $ openstack optimize actionplan list
     +--------------------------------------+--------------------------------------+-----------+---------------------------+-----------------+
     | UUID                                 | Audit                                | State     | Updated At                | Global efficacy |
     +--------------------------------------+--------------------------------------+-----------+---------------------------+-----------------+
     | ba9ce6b3-969c-4b8e-bb61-ae24e8630f81 | e94d4826-ad4e-44df-ad93-dff489fde457 | SUCCEEDED | 2017-05-23T11:53:16+00:00 | None            |
     +--------------------------------------+--------------------------------------+-----------+---------------------------+-----------------+
