Reed-Solomon Codes
==================

.. automodule:: honeybadgermpc.reed_solomon
   :no-members:
   :no-undoc-members:
   :no-private-members:
   :no-inherited-members:
   :no-show-inheritance:

Encoders
--------

Abstract Encoder
^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.Encoder

Matrix Multiplication based Encoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.VandermondeEncoder

Fast Fourier Transforms based Encoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.FFTEncoder

Automatic Selection of Encoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.OptimalEncoder

.. autoclass:: honeybadgermpc.reed_solomon.EncoderSelector


Encoder Factory
^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.EncoderFactory

Decoders
--------
.. todo:: Present briefly the decoders and the concept of "robust" decoder.

Abstract Decoders
^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.Decoder
.. autoclass:: honeybadgermpc.reed_solomon.RobustDecoder

Matrix Multiplication based Decoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.VandermondeDecoder

Fast Fourier Transforms based Decoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.FFTDecoder

Incremental Decoder
^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.IncrementalDecoder
   :no-show-inheritance:

Robust Decoder: Gao
^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.GaoRobustDecoder

Robust Decoder: Berlekamp-Welch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.WelchBerlekampRobustDecoder


Automatic Selection of Decoder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.OptimalDecoder

.. autoclass:: honeybadgermpc.reed_solomon.DecoderSelector


Decoder Factories
^^^^^^^^^^^^^^^^^
.. autoclass:: honeybadgermpc.reed_solomon.DecoderFactory

.. autoclass:: honeybadgermpc.reed_solomon.RobustDecoderFactory


Berlekamp-Welch Decoder
-----------------------

.. automodule:: honeybadgermpc.reed_solomon_wb
