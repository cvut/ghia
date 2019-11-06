ghia
====

GitHub Issue Assigner

Installation and usage
----------------------

::

   $ python setup.py install
   $ ghia --help

Or for the web app (GitHub webhook service): 

::

   $ python setup.py install
   $ export FLASK_APP=ghia
   $ flask run

Then visit the web application on displayed address.

Strategies
~~~~~~~~~~

-  ``append`` = add additional matching assignees
-  ``set`` = set matching assignees only if issue is not assigned yet
-  ``change`` = keep only matching assignees (remove existing
   non-matching assignees)

Configuration
~~~~~~~~~~~~~

Authentication
^^^^^^^^^^^^^^

You need a GitHub `personal access token`_ to run this application. It
has to be specified in the configuration file as follows:

.. code:: ini

   [github]
   token=<YOUR_PERSONAL_ACCESS_TOKEN>

Rules
^^^^^

Rules configuration consists of two parts:

-  **Patterns** which define what username will be matched against what
   regex pattern. Each pattern starts with information with what part of
   issue it will be matched (``title``, ``text``, ``label``, or
   ``any``).
-  (optional) **Fallback** part describes just a label to be set for
   issue that has no assignee after running the assigner.

.. code:: ini

   [patterns]
   MarekSuchanek=
       title:network
       text:protocol
       text:http[s]{0,1}://localhost:[0-9]{2,5}
       label:^(network|networking)$
   hroncok=any:Python

   [fallback]
   label=Need assignment

License
-------

This project is licensed under the MIT License - see the `LICENSE`_ file
for more details.

.. _personal access token: https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line
.. _LICENSE: LICENSE
