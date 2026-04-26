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

Mailing list
    * Discussions on the mailing list are available in the `archive`_
      with the ``[watcher]`` subject prefix. When posting to the
      mailing list, use this prefix on your subject so the team can
      easily find your message.

    * You can register on the mailing list `here`_.

Weekly Meetings
    * `Meeting Information`_
    * `Meeting Agenda`_

.. _changelog: https://meetings.opendev.org/irclogs/%23openstack-watcher/
.. _archive: https://lists.openstack.org/archives/list/openstack-discuss@lists.openstack.org/
.. _here: https://lists.openstack.org/mailman3/lists/openstack-discuss.lists.openstack.org/
.. _Meeting Information: https://meetings.opendev.org/#Watcher_Team_Meeting
.. _Meeting Agenda: https://etherpad.opendev.org/p/openstack-watcher-irc-meeting

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

You found an issue and want to make sure we are aware of it? You can
use the respective project's Launchpad page:

    * `watcher`_
    * `watcher-tempest-plugin`_
    * `watcher-dashboard`_
    * `python-watcherclient`_

.. _watcher: https://bugs.launchpad.net/watcher
.. _watcher-tempest-plugin:
   https://bugs.launchpad.net/watcher-tempest-plugin
.. _watcher-dashboard:
   https://bugs.launchpad.net/watcher-dashboard
.. _python-watcherclient:
   https://bugs.launchpad.net/python-watcherclient

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

All common PTL duties are enumerated here in the `PTL guide
<https://docs.openstack.org/project-team-guide/ptl.html>`_, and in our
`Chronological Release Liaison Guide <https://docs.openstack.org/watcher/latest/contributor/release-guide.html>`_.
