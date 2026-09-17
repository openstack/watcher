..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/


Installing API behind mod_wsgi
==============================

``mod_wsgi`` requires a file on disk and cannot reference the
``watcher.wsgi.api:application`` module path directly. The steps below point
it at the installed ``watcher/wsgi/api.py`` module, which exposes the
``application`` object ``mod_wsgi`` looks for. See :doc:`wsgi` for the other
deployment options.

#. Install the Apache Service::

    Fedora/RHEL/CentOS:
      sudo dnf install httpd

    Debian/Ubuntu:
      apt-get install apache2

#. Copy ``etc/apache2/watcher`` under the apache sites::

    Fedora/RHEL/CentOS:
      sudo cp etc/apache2/watcher /etc/httpd/conf.d/watcher.conf

    Debian/Ubuntu:
      sudo cp etc/apache2/watcher /etc/apache2/sites-available/watcher.conf

#. Edit ``<apache-configuration-dir>/watcher.conf`` according to installation
   and environment.

   * Modify the ``WSGIDaemonProcess`` directive to set the ``user`` and
     ``group`` values to appropriate user on your server.
   * Modify the ``WSGIScriptAlias`` and ``Directory`` directives to match the
     location of the installed ``watcher/wsgi/api.py`` module on your system.
     Both must point at the same place: Apache only serves the script if the
     directory holding it is granted access.
   * Modify the ``ErrorLog and CustomLog`` to redirect the logs to the right
     directory.

#. Enable the apache watcher site and reload::

    Fedora/RHEL/CentOS:
      sudo systemctl reload httpd

    Debian/Ubuntu:
      sudo a2ensite watcher
      sudo service apache2 reload
