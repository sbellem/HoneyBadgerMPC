Continuous integration
======================

.. epigraph::

	*Continuous Integration (CI) is a development practice that requires
 	developers to integrate code into a shared repository several times a day.
 	Each check-in is then verified by an automated build, allowing teams to
 	detect problems early.*

	*By integrating regularly, you can detect errors quickly, and locate them
 	more easily.*

	-- `ThoughtWorks <ThoughtWorks\: Continuous Integration>`_


``honeybadgermpc`` currently uses `Travis CI`_ to perform various checks when
one wishes to merge new code into a shared branch under the shared repository
`initc3/HoneyBadgerMPC`_. The file :file:`.travis.yml` under the root of the
project is used to instruct Travis CI on what to do whenever a build is
triggered.

.travis.yml
-----------
Whenever a build is triggered, three checks are currently performed:

1. tests
2. code quality via `flake8`_. and 
3. documentation generation.

Each of these checks corresponds to a row in the `build matrix`_:

.. code-block:: yaml

    matrix:
      include:
        - env: BUILD=tests
        - env: BUILD=flake8
        - env: BUILD=docs

Depending on the value of the ``BUILD`` variable the various steps (e.g.:
`install`_, `script`_) of the `build lifecycle`_ may differ.

.. rubric:: Using Python 3.7 on Travis CI

In order to use Python 3.7 the following workaround is used in
:file:`.travis.yml`:

.. code-block:: yaml
	
    os: linux
    dist: xenial
    language: python
    python: 3.7
    sudo: true

See currently opened issue on this matter:
https://github.com/travis-ci/travis-ci/issues/9815


.. rubric:: Using Docker on Travis CI

In order to use Docker the following settings are needed in
:file:`travis.yml`:

.. code-block:: yaml
	
    sudo: true

    services:
      - docker

See :ref:`docker-in-travis` below for more information on how we use
``docker`` and ``docker-compose`` on Travis CI to run the tests for
``honeybadgermpc``.


Shell scripts under .ci/
------------------------
In order to simplify the :file:`.travis.yml` file, `shell scripts are invoked
<implementing complex build steps>`_ for the ``install``, ``script`` and
``after_success`` steps. These scripts are located under the :file:`.ci`
directory and should be edited as needed but with care since it is important
that the results of the checks be reliable.


.. _docker-in-travis:

.travis.compose.yml
-------------------
For the ``tests`` build job (i.e.: ``BUILD=tests`` matrix row),
`docker-compose is used <using docker in builds>`_. The :file:`Dockerfile`
used is located under the :file:`.ci` directory whereas the ``docker-compose``
file is under the root of the project and is named :file:`travis.compose.yml`.
Both files are very similar to the ones used for development. One key
difference is that only test requirements are installed.

.. note:: Some work could perhaps be done to limit the duplication accross the
 	two Dockerfiles, by using a base Dockerfile for instance, but this may
 	also complicate things so for now some duplication is tolerated.


After success
-------------
If the ``tests`` build job succeeded then `codecov`_ is invoked in order to
perform the `code coverage <coverage.py>`_ check.

See the :ref:`code-coverage` section for more information on the `codecov`_ 
service.


.. There are various ways to customize how Travis CI builds the code and executes
.. tests. To learn more consult `Customizing the Build`_. 





Recommended readings
--------------------
* `Travis CI: Core Concepts for Beginners`_
* `ThoughtWorks: Continuous Integration`_


.. _travis ci: https://docs.travis-ci.com/
.. _initc3/HoneyBadgerMPC: https://github.com/initc3/HoneyBadgerMPC
.. _travis ci\: core concepts for beginners: https://docs.travis-ci.com/user/for-beginners
.. _thoughtworks\: continuous integration: https://www.thoughtworks.com/continuous-integration
.. _customizing the build: https://docs.travis-ci.com/user/customizing-the-build/
.. _build matrix: https://docs.travis-ci.com/user/customizing-the-build/#build-matrix
.. _install: https://docs.travis-ci.com/user/customizing-the-build/#customizing-the-installation-step
.. _script: https://docs.travis-ci.com/user/customizing-the-build/#customizing-the-build-step
.. _build lifecycle: https://docs.travis-ci.com/user/customizing-the-build/#the-build-lifecycle
.. _implementing complex build steps: https://docs.travis-ci.com/user/customizing-the-build/#implementing-complex-build-steps
.. _using docker in builds: :https://docs.travis-ci.com/user/docker/
.. _flake8: http://flake8.pycqa.org/en/latest/index.html
.. _codecov: https://codecov.io/gh/initc3/HoneyBadgerMPC
.. _coverage.py: https://coverage.readthedocs.io/
