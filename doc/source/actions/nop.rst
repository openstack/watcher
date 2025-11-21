===
Nop
===

Synopsis
--------

**action name**: ``nop``

Logs a message

This action logs a message and is **intended for testing only**.

Configuration
-------------

Action parameters:

======================== ======= ======== ===================================
parameter                type    required description
======================== ======= ======== ===================================
``message``              string  yes      The actual message that will be
                                          logged
``skip_pre_condition``   boolean no       Skip pre-condition check
                                          (default: false)
``fail_pre_condition``   boolean no       Force pre-condition to fail
                                          (default: false)
``fail_execute``         boolean no       Force execute to fail
                                          (default: false)
``fail_post_condition``  boolean no       Force post-condition to fail
                                          (default: false)
======================== ======= ======== ===================================
