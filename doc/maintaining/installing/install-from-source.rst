.. include:: /_substitutions.rst

===========================
Installing CKAN from source
===========================

CKAN is a Python application that requires three main services: PostgreSQL, Solr and Redis.

This section describes how to install CKAN from source. Although
:doc:`install-from-package` is simpler, it requires Ubuntu 20.04 64-bit or
Ubuntu 22.04 64-bit. Installing CKAN from source works with other
versions of Ubuntu and with other operating systems (e.g. RedHat, Fedora, CentOS, OS X).
If you install CKAN from source on your own operating system, please share your
experiences on our `How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`_
wiki page.

**The minimum Python version required is 3.10**

From source is also the right installation method for developers who want to
work on CKAN.

--------------------------------
1. Install the required packages
--------------------------------

If you're using a Debian-based operating system (such as Ubuntu) install the
required packages with this command::

    sudo apt-get install python3-dev libpq-dev python3-pip python3-venv git-core redis-server libmagic1

If you're not using a Debian-based operating system, find the best way to
install the following packages on your operating system (see
our `How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`_
wiki page for help):

=====================  ===============================================
Package                Description
=====================  ===============================================
Python                 `The Python programming language, v3.10 or newer <https://www.python.org/getit/>`_
|postgres|             `The PostgreSQL database system, v12 or newer <https://www.postgresql.org/docs/10/libpq.html>`_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
pip                    `A tool for installing and managing Python packages <https://pip.pypa.io/en/stable/>`_
python3-venv           `The Python3 virtual environment builder (or for Python 2 use 'virtualenv' instead) <https://virtualenv.pypa.io/en/latest/>`_
Git                    `A distributed version control system <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_
Apache Solr            `A search platform <https://lucene.apache.org/solr/>`_
Redis                  `An in-memory data structure store <https://redis.io/>`_
=====================  ===============================================


.. _install-ckan-in-virtualenv:

-------------------------------------------------
2. Install CKAN into a Python virtual environment
-------------------------------------------------

.. tip::

   If you're installing CKAN for development and want it to be installed in
   your home directory, you can symlink the directories used in this
   documentation to your home directory. This way, you can copy-paste the
   example commands from this documentation without having to modify them, and
   still have CKAN installed in your home directory:

   .. parsed-literal::

     mkdir -p ~/ckan/lib
     sudo ln -s ~/ckan/lib |virtualenv_parent_dir|
     mkdir -p ~/ckan/etc
     sudo ln -s ~/ckan/etc |config_parent_dir|

a. Create a Python `virtual environment <https://virtualenv.pypa.io/en/latest/>`_
   (virtualenv) to install CKAN into, and activate it:

   .. parsed-literal::

       sudo mkdir -p |virtualenv|
       sudo chown \`whoami\` |virtualenv|
       python3 -m venv |virtualenv|
       |activate|

.. important::

   The final command above activates your virtualenv. The virtualenv has to
   remain active for the rest of the installation and deployment process,
   or commands will fail. You can tell when the virtualenv is active because
   its name appears in front of your shell prompt, something like this::

     (default) $ _

   For example, if you logout and login again, or if you close your terminal
   window and open it again, your virtualenv will no longer be activated. You
   can always reactivate the virtualenv with this command:

   .. parsed-literal::

       |activate|


b. Install an up-to-date pip:

   .. parsed-literal::

       pip install --upgrade pip

c. Install the CKAN source code into your virtualenv.

   To install the latest stable release of CKAN (CKAN |current_release_version|),
   run:

   .. parsed-literal::

      pip install -e 'git+\ |git_url|\@\ |current_release_tag|\#egg=ckan[requirements]'


   If you're installing CKAN for development, you may want to install the
   latest development version (the most recent commit on the master branch of
   the CKAN git repository). In that case, run this command instead:

   .. parsed-literal::

       pip install -e 'git+\ |git_url|\#egg=ckan[requirements,dev]'

   .. warning::

      The development version may contain bugs and should not be used for
      production websites! Only install this version if you're doing CKAN
      development.

d. Deactivate and reactivate your virtualenv, to make sure you're using the
   virtualenv's copies of commands like ``ckan`` rather than any system-wide
   installed copies:

   .. parsed-literal::

        deactivate
        |activate|

.. _postgres-setup:

------------------------------
3. Setup a PostgreSQL database
------------------------------

.. include:: postgres.rst

----------------------------
4. Create a CKAN config file
----------------------------

Create a directory to contain the site's config files:

.. parsed-literal::

    sudo mkdir -p |config_dir|
    sudo chown -R \`whoami\` |config_parent_dir|/

Create the CKAN config file:

.. parsed-literal::

    ckan generate config |ckan.ini|

Edit the ``ckan.ini`` file in a text editor, changing the following
options:

sqlalchemy.url
  This should refer to the database we created in `3. Setup a PostgreSQL
  database`_ above:

  .. parsed-literal::

    sqlalchemy.url = postgresql://|database_user|:pass@localhost/|database|

  Replace ``pass`` with the password that you created in `3. Setup a
  PostgreSQL database`_ above.

  .. tip ::

    If you're using a remote host with password authentication rather than SSL
    authentication, use:

    .. parsed-literal::

      sqlalchemy.url = postgresql://|database_user|:pass@<remotehost>/|database|?sslmode=disable

site_id
  Each CKAN site should have a unique ``site_id``, for example::

   ckan.site_id = default

site_url
  Provide the site's URL (used when putting links to the site into the
  FileStore, notification emails etc). For example::

    ckan.site_url = http://demo.ckan.org

  Do not add a trailing slash to the URL.

.. _setting up solr:

-------------
5. Setup Solr
-------------

.. include:: solr.rst


.. _postgres-init:

---------------
6. Setup Redis
---------------

If you installed it locally on the first step, make sure you have a Redis
instance running in the `6379` port.

If you have Docker installed, you can setup a default Redis instance by
running::

    docker run --name ckan-redis -p 6379:6379 -d redis

-------------------------
7. Create database tables
-------------------------

Now that you have a configuration file that has the correct settings for your
database, you can :ref:`create the database tables <db init>`:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    ckan -c |ckan.ini| db init

You should see ``Initialising DB: SUCCESS``.

.. tip::

    If the command prompts for a password it is likely you haven't set up the
    ``sqlalchemy.url`` option in your CKAN configuration file properly.
    See `4. Create a CKAN config file`_.

-----------------------
8. Set up the DataStore
-----------------------

.. note ::
  Setting up the DataStore is optional. However, if you do skip this step,
  the :doc:`DataStore features </maintaining/datastore>` will not be available
  and the DataStore tests will fail.

Follow the instructions in :doc:`/maintaining/datastore` to create the required
databases and users, set the right permissions and set the appropriate values
in your CKAN config file.

Once you have set up the DataStore, you may then wish to configure either the DataPusher or XLoader
extensions to add data to the DataStore. To install DataPusher refer to this link:
https://github.com/ckan/datapusher and to install XLoader refer to this link:
https://github.com/ckan/ckanext-xloader

-------------------
9. Create CKAN user
-------------------

To create, remove, list and manage users, you can follow the steps at `Create and Manage Users
<https://docs.ckan.org/en/latest/maintaining/cli.html#user-create-and-manage-users>`__.

----------------
10. You're done!
----------------

You can now run CKAN from the command-line.  This is a simple and lightweight way to serve CKAN that is
useful for development and testing:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    ckan -c |ckan.ini| run

Open http://127.0.0.1:5000/ in a web browser, and you should see the CKAN front
page.

Now that you've installed CKAN, you should:

* Run CKAN's tests to make sure that everything's working, see :doc:`/contributing/test`.

* If you want to use your CKAN site as a production site, not just for testing
  or development purposes, then deploy CKAN using a production web server such
  as uWSGI or Nginx. See :doc:`deployment`.

* Begin using and customizing your site, see :doc:`/maintaining/getting-started`.

.. note:: The default authorization settings on a new install are deliberately
    restrictive. Regular users won't be able to create datasets or organizations.
    You should check the :doc:`/maintaining/authorization` documentation, configure CKAN accordingly
    and grant other users the relevant permissions using the :ref:`sysadmin account <create-admin-user>`.

------------------------------
Source install troubleshooting
------------------------------

.. _solr troubleshooting:

Solr setup troubleshooting
==========================

Solr requests and errors are logged in the web server log files.

* For Jetty servers, the log files are::

    /var/log/jetty/<date>.stderrout.log

* For Tomcat servers, they're::

    /var/log/tomcat6/catalina.<date>.log

AttributeError: 'module' object has no attribute 'css/main.debug.css'
---------------------------------------------------------------------

This error is likely to show up when `debug` is set to `True`. To fix this
error, install frontend dependencies. See :doc:`/contributing/frontend/index`.

After installing the dependencies, run ``npm run build`` and then start ckan
server again.

If you do not want to compile CSS, you can also copy the main.css to
main.debug.css to get CKAN running::

    cp /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.css \
    /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.debug.css

ImportError: No module named 'flask_debugtoolbar'
-------------------------------------------------

This may show up if you have enabled debug mode in the config file. Simply
install the development requirements::

    pip install -r /usr/lib/ckan/default/src/ckan/dev-requirements.txt
