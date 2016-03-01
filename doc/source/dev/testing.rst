..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

=======
Testing
=======

.. _unit_tests:

Unit tests
==========

All unit tests should be run using `tox`_. To run the same unit tests that are
executing onto `Gerrit`_ which includes ``py34``, ``py27`` and ``pep8``, you
can issue the following command::

    $ workon watcher
    (watcher) $ pip install tox
    (watcher) $ cd watcher
    (watcher) $ tox

If you want to only run one of the aforementioned, you can then issue one of
the following::

    $ workon watcher
    (watcher) $ tox -e py34
    (watcher) $ tox -e py27
    (watcher) $ tox -e pep8

.. _tox: https://tox.readthedocs.org/
.. _Gerrit: http://review.openstack.org/

You may pass options to the test programs using positional arguments. To run a
specific unit test, you can pass extra options to `os-testr`_ after putting
the ``--`` separator. So using the ``-r`` option followed by a regex string,
you can run the desired test::

    $ workon watcher
    (watcher) $ tox -e py27 -- -r watcher.tests.api

.. _os-testr: http://docs.openstack.org/developer/os-testr/

When you're done, deactivate the virtualenv::

    $ deactivate

.. include:: ../../../watcher_tempest_plugin/README.rst
