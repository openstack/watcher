Tempest Field Guide to Infrastructure Optimization API tests
============================================================


What are these tests?
---------------------

These tests stress the OpenStack Infrastructure Optimization API provided by
Watcher.


Why are these tests in tempest?
------------------------------

The purpose of these tests is to exercise the various APIs provided by Watcher
for optimizing the infrastructure.


Scope of these tests
--------------------

The Infrastructure Optimization API test perform basic CRUD operations on the Watcher node
inventory.  They do not actually perform placement or migration of virtual resources. It is important
to note that all Watcher API actions are admin operations meant to be used
either by cloud operators.
