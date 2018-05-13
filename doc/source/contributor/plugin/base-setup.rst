..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _plugin-base_setup:

=======================================
Create a third-party plugin for Watcher
=======================================

Watcher provides a plugin architecture which allows anyone to extend the
existing functionalities by implementing third-party plugins. This process can
be cumbersome so this documentation is there to help you get going as quickly
as possible.


Pre-requisites
==============

We assume that you have set up a working Watcher development environment. So if
this not already the case, you can check out our documentation which explains
how to set up a :ref:`development environment
<watcher_development_environment>`.

.. _development environment:

Third party project scaffolding
===============================

First off, we need to create the project structure. To do so, we can use
`cookiecutter`_ and the `OpenStack cookiecutter`_ project scaffolder to
generate the skeleton of our project::

    $ virtualenv thirdparty
    $ . thirdparty/bin/activate
    $ pip install cookiecutter
    $ cookiecutter https://github.com/openstack-dev/cookiecutter

The last command will ask you for many information, and If you set
``module_name`` and ``repo_name`` as ``thirdparty``, you should end up with a
structure that looks like this::

    $ cd thirdparty
    $ tree .
    .
    ├── babel.cfg
    ├── CONTRIBUTING.rst
    ├── doc
    │   └── source
    │       ├── conf.py
    │       ├── contributing.rst
    │       ├── index.rst
    │       ├── installation.rst
    │       ├── readme.rst
    │       └── usage.rst
    ├── HACKING.rst
    ├── LICENSE
    ├── MANIFEST.in
    ├── README.rst
    ├── requirements.txt
    ├── setup.cfg
    ├── setup.py
    ├── test-requirements.txt
    ├── thirdparty
    │   ├── __init__.py
    │   └── tests
    │       ├── base.py
    │       ├── __init__.py
    │       └── test_thirdparty.py
    └── tox.ini

**Note:** You should add `python-watcher`_ as a dependency in the
requirements.txt file::

    # Watcher-specific requirements
    python-watcher

.. _cookiecutter: https://github.com/audreyr/cookiecutter
.. _OpenStack cookiecutter: https://github.com/openstack-dev/cookiecutter
.. _python-watcher: https://pypi.org/project/python-watcher

Implementing a plugin for Watcher
=================================

Now that the project skeleton has been created, you can start the
implementation of your plugin. As of now, you can implement the following
plugins for Watcher:

- A :ref:`goal plugin <implement_goal_plugin>`
- A :ref:`strategy plugin <implement_strategy_plugin>`
- An :ref:`action plugin <implement_action_plugin>`
- A :ref:`planner plugin <implement_planner_plugin>`
- A workflow engine plugin
- A :ref:`cluster data model collector plugin
  <implement_cluster_data_model_collector_plugin>`

If you want to learn more on how to implement them, you can refer to their
dedicated documentation.
