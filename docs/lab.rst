Lab
===
The goal of the "Lab" is to bridge the paper (HoneyBadgerMPC and
AsynchroMix: Practical Asynchronous MPC and its Application to
Anonymous Communication) and the code (HoneyBadgerMPC), or said
differently: to bridge the theory and the implementation.

Shamir Secret Sharing and Reconstruction
----------------------------------------

Robust Interpolation of Polynomials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
key algorithms: Interpolate, RSDecode

+---------------+--------------------------------------+-----------------------------------------+
| Task          | :math:`\approx \mathcal{O}(n^{1+c})` | :math:`\approx \mathcal{O}(n \log^c n)` |
+===============+======================================+=========================================+
| Encode Shares | Matrix Multiplication                | FFT                                     |
+---------------+--------------------------------------+-----------------------------------------+
| Interpolate   | Matrix Multiplication                | Soro-Lacan                              |
+---------------+--------------------------------------+-----------------------------------------+
| RSDecode      | Berlekamp-Welch                      | Gao                                     |
+---------------+--------------------------------------+-----------------------------------------+


Gao's algorithm for Reed-Solomon decoding

Reed-Solomon error correcting
Berlekamp-Welch and Gao

Vandermond interpolation
""""""""""""""""""""""""

FFT-based interpolation
"""""""""""""""""""""""

Batch Reconstruction
^^^^^^^^^^^^^^^^^^^^

SSS-Based MPC
-------------

Offline Phase
^^^^^^^^^^^^^

Asynchronous Reliable Broadcast and Common Subset
-------------------------------------------------
