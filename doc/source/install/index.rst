=============
Install Guide
=============

.. toctree::
   :maxdepth: 2

   get_started.rst
   install.rst
   verify.rst
   next-steps.rst

The Infrastructure Optimization service (Watcher) provides
flexible and scalable resource optimization service for
multi-tenant OpenStack-based clouds.

Watcher provides a complete optimization loop including
everything from a metrics receiver, complex event processor
and profiler, optimization processor and an action plan
applier. This provides a robust framework to realize a wide
range of cloud optimization goals, including the reduction
of data center operating costs, increased system performance
via intelligent virtual machine migration, increased energy
efficiency and more!

Watcher also supports a pluggable architecture by which custom
optimization algorithms, data metrics and data profilers can be
developed and inserted into the Watcher framework.

Check the documentation for watcher optimization strategies at
`Strategies <https://docs.openstack.org/watcher/latest/strategies/index.html>`_.

Check watcher glossary at `Glossary
<https://docs.openstack.org/watcher/latest/glossary.html>`_.


This chapter assumes a working setup of OpenStack following the
`OpenStack Installation Tutorial
<https://docs.openstack.org/queens/install/>`_.
