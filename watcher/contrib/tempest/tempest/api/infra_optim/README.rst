..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

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
