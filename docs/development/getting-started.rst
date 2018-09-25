Getting started
===============
To start developing and contributing to HoneyBadgerMPC:

1. Fork the repository and clone your fork. (See the Github Guide
   `Forking Projects`_ if needed.)

2. Install `Docker`_ (For Linux, see
   `Manage Docker as a non-root user <dockerrootless>`_) to run ``docker``
   without ``sudo``.)

3. Install `docker-compose`_.

4. Run the tests (the first time will take longer as the image will be built):

    .. code-block:: bash
   
        $ docker-compose run --rm honeybadgermpc

   The tests should pass, and you should also see a small code coverage report
   output to the terminal.

If the above went all well, you should be setup for developing
**HoneyBadgerMPC**!

.. tip:: You may find it useful when developing to have the following 3
    "windows" opened at all times:
    
    * your text editor or IDE
    * an ``ipython`` session for quickly trying things out
    * a shell session for running tests, debugging, and building the docs
    
    You can run the ``ipython`` and shell session in separate containers:
    
    IPython session:
    
    .. code-block:: bash
    
        $ docker-compose run --rm honeybadgermpc ipython
    
    Shell session:
    
    .. code-block:: bash
    
        $ docker-compose run --rm honeybadgermpc sh
    
    Once in the session (container) you can execute commands just as you would
    in a non-container session.

**Running a specific test in a container (shell session)**
As an example, to run the tests for ``passive.py``, which will generate and
open 1000 zero-sharings, :math:`N=3` :math:`t=2` (so no fault tolerance):

Run a shell session in a container:

.. code-block:: bash

    $ docker-compose run --rm honeybadgermpc sh

Run the test:

.. code-block:: bash

    $ pytest -v tests/test_passive.py -s

or

.. code-block:: bash

    $ python -m honeybadgermpc.passive

.. rubric:: About code changes and building the image

When developing, you should not need to rebuild the image nor exit running
containers, unless new dependencies were added via the `Dockerfile`. Hence you
can modify the code, add breakpoints, add new Python modules (files), and the
modifications will be readily available withing the running containers.


.. Development environment
.. -----------------------

Running the tests
-----------------
The tests for ``honeybadgermpc`` are located under the :file:`tests/`
directory and can be run with `pytest`_:

.. code-block:: bash

	$ pytest

Running in verbose mode:

.. code-block:: bash

	$ pytest -v

Running a specific test:

.. code-block:: bash

	$ pytest -v tests/test_passive.py::test_open_share

When debugging, i.e. if one has put breakpoints in the code, use the ``-s``
option (or its equivalent ``--capture=no``):

.. code-block:: bash
	
	$ pytest -v -s
	# or
	$ pytest -v --capture=no

To exit instantly on first error or failed test:

.. code-block:: bash
	
	$ pytest -x

To re-run only the tests that failed in the last run:

.. code-block:: bash
	
	$ pytest --lf

See ``pytest --help`` for more options or the `pytest`_ docs.

Code coverage
^^^^^^^^^^^^^
Measuring the code coverage:

.. code-block:: bash

	$ pytest --cov

Generating an html coverage report:

.. code-block:: bash

	$ pytest --cov --cov-report html

View the report:

.. code-block:: bash
	
	$ firefox htmlcov/index.html

Configuration
"""""""""""""
Configuration for code coverage is located under the file :file:`.coveragerc`.


.. rubric:: Code coverage tools

The code coverage is measured using the `pytest-cov`_ plugin which is based on
`coverage.py`_. The documentation of both projects is important when working
on code coverage related issues. As an example, documentation for
configuration can be first found in `pytest-cov
<https://pytest-cov.readthedocs.io/en/latest/config.html>`__ but details about
the coverage config file need to be looked up in `coverage.py
<https://coverage.readthedocs.io/en/latest/config.html>`__ docs.

Code quality
^^^^^^^^^^^^
In order to keep a minimal level of "code quality" `flake8`_ is used. To run
the check:

.. code-block:: bash

	$ flake8

Configuration
"""""""""""""
`Configuration for flake8`_ is under the :file:`.flake8` file.



Building and viewing the documentation
--------------------------------------
Documentation for ``honeybadgermpc`` is located under the :file:`docs/`
directory. `Sphinx`_ is used to build the documentation, which is written
using the markup language `reStructuredText`_.

The :file:`docker-compose.yml` can be used to quickly build the docs and view
them. 

**To build the docs:**

.. # run `O=-W --keep-going make -C docs html` in a container, which will
.. # write the html docs locally under docs/_build/html
.. code-block:: bash

	$ docker-compose up builddocs

**To view the docs**:

.. # start nginx which is used to host the docs locally
.. code-block:: bash

	$ docker-compose up -d viewdocs

Visit http://localhost:58888/ in a web browser.


.. tip:: To view the port mapping you can use the command:

	.. code-block:: bash
	
		$ docker-compose port viewdocs 80
	
	or, alternatively
	
	.. code-block:: bash
	
	 	$ docker-compose ps viewdocs


.. tip:: One may get a ``403 Forbidden`` error when trying to view the docs
	at http://localhost:58888/. This may because the generated html docs were
	removed. Using the ``make clean`` command under the :file:`docs/`
	directory, e.g.:
 
	.. code-block:: bash
		
		docker-compose run --rm builddocs make -C docs clean

	wipes out the :file:`_build/` directory, and one has to restart the
	``viewdocs`` (``nginx``) service, i.e.:
	
	.. code-block:: bash

		$ docker-compose restart viewdocs

	and then re-build the docs:

	.. code-block:: bash

		$ docker-compose up builddocs

	Or vice-versa: build the docs and restart the server.

Alternative ways to build and view the docs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To build the documentation, one can use the :file:`Makefile` under the
:file:`docs/` directory:

.. code-block:: bash

	$ make -C docs html

or 

.. code-block:: bash

	$ cd docs
	$ make html

The :file:`Makefile` makes use of the `sphinx-build`_ command, which one can
also use directly:

.. code-block:: bash

    $ sphinx-build -M html docs docs/_build -c docs -W --keep-going

It is possible to set some Sphinx `environment variables`_ when using the
:file:`Makefile`, and more particularly ``SPHINXOPTS`` via the shortcut ``O``.
For instance, to `treat warnings as errors`_ and to `keep going`_ with
building the docs when a warning occurs:

.. code-block:: bash

	$ O='-W --keep-going' make html


By default the generated docs are under :file:`docs/_build/html/` and one
can view them using a browser, e.g.:

.. code-block:: bash

	$ firefox docs/_build/html/index.html



.. hyperlinks

.. _Forking Projects: https://guides.github.com/activities/forking/
.. _Docker: https://docs.docker.com/install/
.. _dockerrootless: https://docs.docker.com/install/linux/linux-postinstall/#manage-docker-as-a-non-root-user
.. _docker-compose: https://docs.docker.com/compose/install/
.. _pytest: https://docs.pytest.org/
.. _coverage.py: https://coverage.readthedocs.io/
.. _pytest-cov: https://pytest-cov.readthedocs.io/
.. _flake8: http://flake8.pycqa.org/en/latest/index.html
.. _Configuration for flake8: http://flake8.pycqa.org/en/latest/user/configuration.html
.. _reStructuredText: http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _Sphinx: http://www.sphinx-doc.org
.. _sphinx-build: http://www.sphinx-doc.org/en/master/man/sphinx-build.html
.. _environment variables: http://www.sphinx-doc.org/en/master/man/sphinx-build.html#environment-variables
.. _treat warnings as errors: http://www.sphinx-doc.org/en/master/man/sphinx-build.html#id6
.. _keep going: http://www.sphinx-doc.org/en/master/man/sphinx-build.html#cmdoption-sphinx-build-keep-going
