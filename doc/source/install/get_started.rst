============================================
Infrastructure Optimization service overview
============================================
The Infrastructure Optimization service provides flexible and scalable
optimization service for multi-tenant OpenStack based clouds.

The Infrastructure Optimization service consists of the following components:

``watcher`` command-line client
  A CLI to communicate with ``watcher-api`` to optimize the cloud.

``watcher-api`` service
  An OpenStack-native REST API that accepts and responds to end-user calls
  by processing them and forwarding to appropriate underlying watcher
  services via AMQP.

``watcher-decision-engine`` service
  It runs audit and return an action plan to achieve optimization goal
  specified by the end-user in audit.

``watcher-applier`` service
  It executes action plan built by watcher-decision-engine. It interacts with
  other OpenStack components like nova to execute the given action
  plan.

``watcher-dashboard``
  Watcher UI implemented as a plugin for the OpenStack Dashboard.
