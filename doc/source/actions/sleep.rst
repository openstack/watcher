=====
Sleep
=====

Synopsis
--------

**action name**: ``sleep``

Makes the executor of the action plan wait for a given duration

This action is **intended for testing purposes only**.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``duration``             number yes      Duration to sleep in seconds
                                         (minimum: 0)
======================== ====== ======== ===================================
