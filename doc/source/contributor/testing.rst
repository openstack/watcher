..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

=================
Developer Testing
=================

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

.. _tempest_tests:

Tempest tests
=============

Tempest tests for Watcher has been migrated to the external repo
`watcher-tempest-plugin`_.

.. _watcher-tempest-plugin: https://opendev.org/openstack/watcher-tempest-plugin
