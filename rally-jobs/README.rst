Rally job
=========

We provide, with Watcher, a Rally plugin you can use to benchmark the optimization service.

To launch this task with configured Rally you just need to run:

::

  rally task start watcher/rally-jobs/watcher-watcher.yaml

Structure
---------

* plugins - directory where you can add rally plugins. Almost everything in
  Rally is a plugin. Benchmark context, Benchmark scenario, SLA checks, Generic
  cleanup resources, ....

* extra - all files from this directory will be copy pasted to gates, so you
  are able to use absolute paths in rally tasks.
  Files will be located in ~/.rally/extra/*

* watcher.yaml is a task that is run in gates against OpenStack
  deployed by DevStack


Useful links
------------

* How to install: http://docs.openstack.org/developer/rally/install.html

* How to set Rally up and launch your first scenario:  https://rally.readthedocs.io/en/latest/tutorial/step_1_setting_up_env_and_running_benchmark_from_samples.html

* More about Rally: https://rally.readthedocs.org/en/latest/

* Rally release notes: https://rally.readthedocs.org/en/latest/release_notes.html

* How to add rally-gates: https://rally.readthedocs.org/en/latest/gates.html

* About plugins:  https://rally.readthedocs.org/en/latest/plugins.html

* Plugin samples: https://github.com/openstack/rally/tree/master/samples/plugins
