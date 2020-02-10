============================
So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects:
the accounts you need, the basics of interacting with our Gerrit review system,
how we communicate as a community, etc.

Below will cover the more project specific information you need to get started
with Watcher.

Communication
~~~~~~~~~~~~~~
.. This would be a good place to put the channel you chat in as a project; when/
   where your meeting is, the tags you prepend to your ML threads, etc.

IRC Channel
    ``#openstack-watcher`` (changelog_)

Mailing list(prefix subjects with ``[watcher]``)
    http://lists.openstack.org/pipermail/openstack-discuss/

Weekly Meetings
    Bi-weekly, on Wednesdays at 08:00 UTC on odd weeks in the
    ``#openstack-meeting-alt`` IRC channel (`meetings logs`_)

Meeting Agenda
    https://wiki.openstack.org/wiki/Watcher_Meeting_Agenda

.. _changelog: http://eavesdrop.openstack.org/irclogs/%23openstack-watcher/
.. _meetings logs:  http://eavesdrop.openstack.org/meetings/watcher/

Contacting the Core Team
~~~~~~~~~~~~~~~~~~~~~~~~~
.. This section should list the core team, their irc nicks, emails, timezones etc.
   If all this info is maintained elsewhere (i.e. a wiki), you can link to that
   instead of enumerating everyone here.

+--------------------+---------------+------------------------------------+
| Name               | IRC           | Email                              |
+====================+===============+====================================+
| `Li Canwei`_       | licanwei      | li.canwei2@zte.com.cn              |
+--------------------+---------------+------------------------------------+
| `chen ke`_         | chenke        | chen.ke14@zte.com.cn               |
+--------------------+---------------+------------------------------------+
| `Corne Lukken`_    | dantalion     | info@dantalion.nl                  |
+--------------------+---------------+------------------------------------+
| `su zhengwei`_     | suzhengwei    | sugar-2008@163.com                 |
+--------------------+---------------+------------------------------------+
| `Yumeng Bao`_      | Yumeng        | yumeng_bao@yahoo.com               |
+--------------------+---------------+------------------------------------+

.. _Corne Lukken: https://launchpad.net/~dantalion
.. _Li Canwei: https://launchpad.net/~li-canwei2
.. _su zhengwei: https://launchpad.net/~sue.sam
.. _Yumeng Bao: https://launchpad.net/~yumeng-bao
.. _chen ke: https://launchpad.net/~chenker

New Feature Planning
~~~~~~~~~~~~~~~~~~~~
.. This section is for talking about the process to get a new feature in. Some
   projects use blueprints, some want specs, some want both! Some projects
   stick to a strict schedule when selecting what new features will be reviewed
   for a release.

New feature will be discussed via IRC or ML (with [Watcher] prefix).
Watcher team uses blueprints in `Launchpad`_ to manage the new features.

.. _Launchpad: https://launchpad.net/watcher

Task Tracking
~~~~~~~~~~~~~~
.. This section is about where you track tasks- launchpad? storyboard?
   is there more than one launchpad project? what's the name of the project
   group in storyboard?

We track our tasks in Launchpad.
If you're looking for some smaller, easier work item to pick up and get started
on, search for the 'low-hanging-fruit' tag.

.. NOTE: If your tag is not 'low-hanging-fruit' please change the text above.

Reporting a Bug
~~~~~~~~~~~~~~~
.. Pretty self explanatory section, link directly to where people should report bugs for
   your project.

You found an issue and want to make sure we are aware of it? You can do so
`HERE`_.

.. _HERE: https://bugs.launchpad.net/watcher

Getting Your Patch Merged
~~~~~~~~~~~~~~~~~~~~~~~~~
.. This section should have info about what it takes to get something merged.
   Do you require one or two +2's before +W? Do some of your repos require
   unit test changes with all patches? etc.

Due to the small number of core reviewers of the Watcher project,
we only need one +2 before +W (merge). All patches excepting for documentation
or typos fixes must have unit test.

Project Team Lead Duties
------------------------
.. this section is where you can put PTL specific duties not already listed in
   the common PTL guide (linked below)  or if you already have them written
   up elsewhere, you can link to that doc here.

All common PTL duties are enumerated here in the `PTL guide <https://docs.openstack.org/project-team-guide/ptl.html>`_.
