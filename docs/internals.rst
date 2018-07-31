*********
Internals
*********

.. automodule:: honeybadgermpc

field
=====
.. automodule:: honeybadgermpc.field

polynomial
==========
.. automodule:: honeybadgermpc.polynomial

passive
=======
.. automodule:: honeybadgermpc.passive

commonsubset
============
.. automodule:: honeybadgermpc.commonsubset_functionality

rand
====
.. automodule:: honeybadgermpc.rand_functionality
.. automodule:: honeybadgermpc.rand_protocol
.. automodule:: honeybadgermpc.rand_batch


beaver
======
Perform multiple shared-secret multiplications at once

Input
    :math:`n` :math:`t`-shared pairs of secrets that one wishes to multiply and
    :math:`n` sets of beaver triples. :math:`2n \geq t+1`

Output
    :math:`n` :math:`t`-shared secret pairs that have been successfully multiplied

.. automodule:: honeybadgermpc.beaver_functionality
.. automodule:: honeybadgermpc.beaver
.. automodule:: tests.test_beaver


secretshare
===========
.. automodule:: honeybadgermpc.secretshare_functionality

router
======
.. automodule:: honeybadgermpc.router
