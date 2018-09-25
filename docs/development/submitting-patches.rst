Contributing new code
=====================
Since `git`_  and `github`_ are used to version and host the code, one needs
to learn to work with both tools. 


Suggested Git/Github workflow
-----------------------------
A small example of a typical workflow is provided here. This is by no means a
complete guide on how to work with Git and Github, and if needed one may
consult the `Pro Git book`_ as a starting point.

Working with Git Remotes
^^^^^^^^^^^^^^^^^^^^^^^^
First make sure your `git remotes`_ are properly set, and if not consult the
`docs <git remotes>`_ to do so. The remote names are just conventions but in
order to simplify this documentation we'll adopt the conventions. So by
convention, ``upstream`` should point to the "shared" repository, whereas
``origin`` should point to your fork. Use ``git remote -v`` to perform the
check:

.. code-block:: bash

	$ git remote -v
	origin  git@github.com:<github_username>/HoneyBadgerMPC.git (fetch)
	origin  git@github.com:<github_username>/HoneyBadgerMPC.git (push)
	upstream        git@github.com:initc3/HoneyBadgerMPC.git (fetch)
	upstream        git@github.com:initc3/HoneyBadgerMPC.git (push)

Identify the shared remote branch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
What should be the base (remote) branch for your work? In many cases, if not
most, it'll be the default `dev`_ branch, but in other cases you may need to
base your work on some other branch, such as `jubjub`_.

It is convenient to have a local copy of the remote shared branch that you
need to work on. As an example, if you need to contribute work to the
`jubjub`_ branch:

.. code-block:: bash

	$ git fetch upstream
	$ git checkout -b jubjub upstream/jubjub

In order to keep your local copy up-to-date you should periodically sync it
with the remote. First switch to (checkout) the local branch:

.. code-block:: bash

	$ git fetch upstream
	$ git rebase upstream/jubjub jubjub

There are multiple ways to work with remote branches. See
https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches for more
information.

For a small discussion regarding the differences between rebasing and merging
see https://git-scm.com/book/en/v2/Git-Branching-Rebasing#_rebase_vs_merge.


Create a new branch
^^^^^^^^^^^^^^^^^^^
Create a new branch from the shared remote branch to which new code needs to
be added. As an example, say you would have to work on issue #23 (Implement
jubjub elliptic curve MPC programs), then you could do something similar to:

.. code-block:: bash
      
	$ git checkout -b issue-23-jujub-ec-mpc jubjub

You can name the branch whatever you like, but you may find it useful to
choose a meaningful name along with the issue number you are working on.

Do you work, backup, and stay in sync
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As you are adding new code, making changes etc you may want to push your work
to your remote on Github, as this will serve as a backup:

.. code-block:: bash

	$ git push origin jubjub


In addtion to backing up your work on Github you should stay in sync with
the shared remote branch. To do so, periodically ``fetch`` and ``rebase``:

.. code-block:: bash

	$ git fetch upstream
	$ git rebase upstream/jubjub jubjub

Git commit best practices
^^^^^^^^^^^^^^^^^^^^^^^^^
.. todo:: document some common best practices to write commit messages and
	also to organize one's work into relatively clean commits

Signing commits
^^^^^^^^^^^^^^^
.. todo:: document the option of signing commits
 	* https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work
	* https://help.github.com/articles/signing-commits/

Make a pull request
^^^^^^^^^^^^^^^^^^^
Once you are done with your work, you can `make a pull request`_ against the
shared remote branch that you have based your work on.

It is generally advisable to keep a pull request focused on one issue, and
relatively small in order to facilitate the review process.

Pull requests go through 4 checks:

* unit tests
* code quality via `flake8`_
* documentation building
* code coverage

These checks are performed using `Travis CI`_ and `Codecov`_. These checks are
there to help keeping the code in good shape and pull requests should ideally
pass these 4 checks before being merged.

Coding Guidelines
-----------------
The ``honeybadgermpc`` code follows the `PEP8`_ style guide. The maximum line
length is set at 89 characters. This setting can be found in the
:file:`.flake8` file.

Test driven work
----------------
Tests are heavily encouraged as they not only help the one developing the code
but also others to verify the work. Consequently, a pull request should be
accompanied by some tests. Code coverage is checked on travis and codecov and
teh pull request may be automatically marked as failing if the code coverage
drops too much. The coverage requirements are defined in the
:file:`.codecov.yaml` file.

.. todo:: link to relavant codecov docs (for setting coverage drops tolerance)

In addition to providing tests with one's work one is also encouraged to try
to develop the code and tests more or less concurrently. That is, one does not
need to wait at "the end" to start writing tests. Both the code and tests can
be developed in multiple iteration in such a way that one makes progress on
both fronts as time advances.

.. todo:: refine/review this section

Documentation
-------------
.. todo:: docstrings guidelines etc


Git & Github references
-----------------------
.. todo:: add links


FAQ
---

**Q.** Why some test functions import modules-under-test or related ones locally
instead of importing at the top?

**A.** See https://pylonsproject.org/community-unit-testing-guidelines.html

.. _git: https://git-scm.com/
.. _github: https://help.github.com/
.. _git remotes: https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes
.. _dev: https://github.com/initc3/HoneyBadgerMPC/tree/dev
.. _jubjub: https://github.com/initc3/HoneyBadgerMPC/tree/jubjub
.. _make a pull request: https://help.github.com/articles/creating-a-pull-request-from-a-fork/
.. _Pro Git Book: https://git-scm.com/book/en/v2
.. _Travis CI: https://docs.travis-ci.com/
.. _Codecov: https://codecov.io/
.. _PEP8: https://www.python.org/dev/peps/pep-0008/
.. _flake8: http://flake8.pycqa.org/en/latest/index.html
