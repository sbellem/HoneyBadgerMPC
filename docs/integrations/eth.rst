Ethereum as an MPC Coordinator
==============================
A blockchain can be used as a coordinating mechanism to run an MPC
program. This document covers the AsynchroMix application.

AsynchroMix Protocol
--------------------
In the paper, Reliable Broadcast and Common Subset are used to
"coordinate" the MPC operations. Below is the protocol as it is in the
paper and after that the AsynchroMix protocol is revisited such that
an Ethereum smaert contract is used for coordination instead.

**AsynchroMix as presented in the paper:**

* Input: Each client :math:`C_j` receives an input :math:`m_j`
* Output: In each epoch a subset of client inputs
  :math:`m_1, \ldots, m_k` are selected, and a permutation
  :math:`\pi (m_1, \ldots, m_k)` is published where :math:`\pi` does
  not depend on the input permutation
* Preprocessing:

   * For each :math:`m_j`, a random :math:`[\![r_j]\!]`, where each
     client has received :math:`r_j`
   * Preprocessing for PowerMix and/or Switching-Network

* Protocol (for client :math:`C_j`):

  1. Set :math:`\overline m_j := m_j + r_j`
  2. :math:`\textsf{ReliableBroadcast} \; \overline m_j`
  3. Wait until :math:`m_j` appears in the output of a mixing epoch

* Protocol (for server :math:`P_i`)

  - Initialize for each client :math:`C_j`

    .. math::
      :nowrap:
  
      \begin{align*}
        \textsf{input}_j & := 0 \quad \textit{ // No. of inputs received from } C_j \\
        \textsf{done}_j & := 0 \quad \textit{ // No. of messages mixed for } C_j
      \end{align*}
  
  - On receiving :math:`\overline m_j` output from
    :math:`\textsf{ReliableBroadcast}` client :math:`C_j` at any time,
    set :math:`\textsf{input}_j := \textsf{input}_{j + 1}`
  - Proceed in consecutive mixing epochs :math:`e`:
  
    **Input Collection Phase**
  
    * Let :math:`b_i` be a :math:`\lvert \mathcal{C} \rvert`-bit vector
      where :math:`b_{i,j} = 1` if :math:`\textsf{input}_j \gt
      \textsf{done}_j`.
    * Pass :math:`b_i` as input to an instance of
      :math:`\textsf{CommonSubset}`.
    * Wait to receive :math:`b` from :math:`\textsf{CommonSubset}`, where
      :math:`b` is an :math:`n \times \lvert \mathcal{C} \rvert` matrix, each row of
      :math:`b` corresponds to the input from one server, and at least
      :math:`n − t` of the rows are non-default.
    * Let :math:`b_{\cdot,, j}` denote the column corresponding to client
      :math:`C_j`.
    * For each :math:`C_j`,
  
      .. math::
        :nowrap:
        
        \begin{equation}
           [\![m_j]\!] := 
           \begin{cases}
              \overline m_j - [\![r_j]\!] & \sum b_{\cdot,j} \geq t+1 \\
              0 & \text{otherwise}
           \end{cases}
        \end{equation}
  
    **Online Phase**
     
        Switch Network Option
          
           Run the MPC Program switching-network on
           :math:`\{[\![m_{j,k_j}]\!]\}`, resulting in
           :math:`\pi (m_1, \ldots, m_k)`
           Requires :math:`k` rounds,
  
        Powermix Option
        
           Run the MPC Program power-mix on
           :math:`\{[\![m_{j,k_j}]\!]\}`, resulting in
           :math:`\pi (m_1, \ldots, m_k)`
        
        Set :math:`\textsf{done}_j := \textsf{done}_{j+1}` for each
        client :math:`C_j` whose input was mixed this epoch

Input
^^^^^
Each client :math:`C_j` receives an input :math:`m_j`.

Currently, only one client is used, and the client itself sends a
series of "dummy" messages. In
:func:`~apps.asynchromix.asynchromix.AsynchromixClient._run()`:

.. code-block:: python
   
   class AsynchromixClient:
      
      async def _run(self):
   
         # ...
         for epoch in range(1000):
             receipts = []
             for i in range(32):
                 m = f"message:{epoch}:{i}"
                 task = asyncio.ensure_future(self.send_message(m))
                 receipts.append(task)
             receipts = await asyncio.gather(*receipts)
         # ...

Output
^^^^^^
In each epoch a subset of client inputs :math:`m_1, \ldots, m_k` are
selected, and a permutation :math:`\pi (m_1, \ldots, m_k)` is published
where :math:`\pi` does not depend on the input permutation

Preprocessing
^^^^^^^^^^^^^
* For each :math:`m_j`, a random :math:`[\![r_j]\!]`, where each client
  has received :math:`r_j`
* Preprocessing for PowerMix and/or Switching-Network

In the :mod:`~apps.asynchromix.asynchromix` example the client (
:class:`~apps.asynchromix.asynchromix.AsynchromixClient`)

1. waits for an input mask to be ready via the smart contract function
   :sol:func:`inputmasks_available`;
2. reserves an input mask via :sol:func:`reserve_inputmask`;
3. fetches the input mask from the servers (the client reconstructs the
   input mask, given sufficient shares from the servers)

Below are some code snippets that perform the above 3 steps. *Some
details of the implementation are ommitted in order to ease the
presentation.*

.. code-block:: python
   
    class AsynchromixClient:
      
        async def send_message(self, m):
            contract_concise = ConciseContract(self.contract)

            # Step 1. Wait until there is input available, and enough triples
            while True:
                inputmasks_available = contract_concise.inputmasks_available()
                if inputmasks_available >= 1:
                    break
                await asyncio.sleep(5)

            # Step 2. Reserve the input mask
            tx_hash = self.contract.functions.reserve_inputmask().transact(
                {"from": self.w3.eth.accounts[0]}
            )
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)
            rich_logs = self.contract.events.InputMaskClaimed().processReceipt(tx_receipt)
            inputmask_idx = rich_logs[0]["args"]["inputmask_idx"]

            # Step 3. Fetch the input mask from the servers
            inputmask = await self._get_inputmask(inputmask_idx)

        async def _get_inputmask(self, idx):
            contract_concise = ConciseContract(self.contract)
            n = contract_concise.n()
            poly = polynomials_over(field)
            eval_point = EvalPoint(field, n, use_omega_powers=False)
            shares = []
            for i in range(n):
                share = self.req_mask(i, idx)
                shares.append(share)
            shares = await asyncio.gather(*shares)
            shares = [(eval_point(i), share) for i, share in enumerate(shares)]
            mask = poly.interpolate_at(shares, 0)
            return mask


AsynchromixClient Protocol (for client :math:`C_j`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
1. Set :math:`\overline m_j := m_j + r_j`
2. :math:`\textsf{ReliableBroadcast} \; \overline m_j`
3. Wait until :math:`m_j` appears in the output of a mixing epoch

In the :mod:`~apps.asynchromix.asynchromix` example the client (
:class:`~apps.asynchromix.asynchromix.AsynchromixClient`) uses the
smart contract function :sol:func:`submit_message` to publish the
masked message :math:`\overline m_j`.

.. code-block:: python
   
    class AsynchromixClient:
      
        async def send_message(self, m):
            # ...
            masked_message = message + inputmask
            masked_message_bytes = self.w3.toBytes(hexstr=hex(masked_message.value))
            masked_message_bytes = masked_message_bytes.rjust(32, b"\x00")

            # Step 4. Publish the masked input
            tx_hash = self.contract.functions.submit_message(
                inputmask_idx, masked_message_bytes
            ).transact({"from": self.w3.eth.accounts[0]})
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)


AsynchromixServer Protocol (for server :math:`P_i`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Initialize for each client :math:`C_j`

  .. math::

      \textsf{input}_j := 0 \textit{ // No. of inputs received from } C_j \\
      \textsf{done_j} := 0 \textit{ // No. of messages mixed for } C_j

- On receiving :math:`\overline m_j` output from
  :math:`\textsf{ReliableBroadcast}` client :math:`C_j` at any time,
  set :math:`\textsf{input}_j := \textsf{input}_{j + 1}`

This step is handled by the smart contract function
:sol:func:`submit_message`. When the client submits a masked message,
the masked input (message) is stored in the contract's state variable
:sol:svar:`input_queue` and the length of the input queue (
:math:`\textsf{input}_j`) is incremented by one.

.. code-block:: solidity

    struct Input {
        bytes32 masked_input; // (m+r)
        uint inputmask;       // index in inputmask of mask [r]
    }

    Input[] public input_queue; // All inputs sent so far

    event MessageSubmitted(uint idx, uint inputmask_idx, bytes32 masked_input);

    function submit_message(uint inputmask_idx, bytes32 masked_input) public {
        // Must be authorized to use this input mask
        require(inputmasks_claimed[inputmask_idx] == msg.sender);

        uint idx = input_queue.length;
        input_queue.length += 1;

        input_queue[idx].masked_input = masked_input;
        input_queue[idx].inputmask = inputmask_idx;

        emit MessageSubmitted(idx, inputmask_idx, masked_input);

        // The input masks are deactivated after first use
        inputmasks_claimed[inputmask_idx] = address(0);
    }

- Proceed in consecutive mixing epochs :math:`e`:

  **Input Collection Phase**

  * Let :math:`b_i` be a :math:`|\mathcal{C}|`-bit vector where
    :math:`b_{i,j} = 1` if :math:`\textsf{input}_j \gt
    \textsf{done}_j`.
  * Pass :math:`b_i` as input to an instance of
    :math:`\textsf{CommonSubset}`.
  * Wait to receive :math:`b` from :math:`\textsf{CommonSubset}`, where
    :math:`b` is an :math:`n \times |\mathcal{C}|` matrix, each row of
    :math:`b` corresponds to the input from one server, and at least
    :math:`n − t` of the rows are non-default.
  * Let :math:`b_{\cdot,, j}` denote the column corresponding to client
    :math:`C_j`.
  * For each :math:`C_j`,

    .. math::
      :nowrap:
      
      \begin{equation}
         [\![m_j]\!] := 
         \begin{cases}
            \overline m_j - [\![r_j]\!] & \sum b_{\cdot,j} \geq t+1 \\
            0 & \text{otherwise}
         \end{cases}
      \end{equation}

  **Online Phase**
   
      Switch Network Option
        
         Run the MPC Program switching-network on
         :math:`\{[\![m_{j,k_j}]\!]\}`, resulting in
         :math:`\pi (m_1, \ldots, m_k)`
         Requires :math:`k` rounds,

      Powermix Option
      
         Run the MPC Program power-mix on
         :math:`\{[\![m_{j,k_j}]\!]\}`, resulting in
         :math:`\pi (m_1, \ldots, m_k)`
      
      Set :math:`\textsf{done}_j := \textsf{done}_{j+1}` for each
      client :math:`C_j` whose input was mixed this epoch

  

Main components:

* coordinator: blockchain
* asynchromix servers
* asynchromix client

Walkthrough
-----------
This section presents a step-by-step walkthrough of the code involved
to run the asynchromix example.

To run the example:

.. code-block:: shell

   $ python apps/asynchromix/asynchromix.py


So what happens when the above command is run?

1. :py:func:`~apps.asynchromix.asynchromix.test_asynchromix` is run.
2. :py:func:`~apps.asynchromix.asynchromix.test_asynchromix` takes care
   of running a local test Ethereum blockchain using `Ganache`_ and of
   starting the main loop via
   :py:func:`~apps.asynchromix.asynchromix.run_eth()`. More precisely,
   :py:func:`~apps.asynchromix.asynchromix.test_asynchromix` runs the
   command:

   .. code-block:: shell
   
      ganache-cli -p 8545 -a 50 -b 1 > acctKeys.json 2>&1

   in a subprocess, in a :py:func:`contextmanager` (
   :py:func:`~apps.asynchromix.asynchromix.run_and_terminate_process`)
   and within this context, in which Ethereum is running, the function
   :py:func:`~apps.asynchromix.asynchromix.run_eth()` is invoked.
3. :py:func:`~apps.asynchromix.asynchromix.run_eth()` takes care of
   instantiating a connection to the local Ethereum node:

   .. code-block:: python
   
      w3 = Web3(HTTPProvider())

   and of starting the main loop which needs a connection to Ethereum:

   .. code-block:: python
        
      loop.run_until_complete(asyncio.gather(main_loop(w3)))
4. The :py:func:`~apps.asynchromix.asynchromix.main_loop` takes care of
   four main things:

   1. creating a coordinator contract (and web3 interface to it);
   2. instantiating the asynchromix servers;
   3. instantiating an asynchromix client;
   4. starting the servers and client and waiting for the completion of
      their tasks.

Initialization Phase
^^^^^^^^^^^^^^^^^^^^
* Setup an Ethereum account for each server.
* Load the contract on chain.



Coordinator Contract
^^^^^^^^^^^^^^^^^^^^

.. .. sol:contract:: AsynchromixCoordinator
.. 
..    .. sol:function:: inputmasks_available () public view returns (uint)
.. 
..    Returns the number of input masks that are available.

.. autosolcontract:: AsynchromixCoordinator

      

Asynchromix Servers
^^^^^^^^^^^^^^^^^^^
.. autoclass:: apps.asynchromix.asynchromix.AsynchromixServer

Asynchromix Client
^^^^^^^^^^^^^^^^^^
.. autoclass:: apps.asynchromix.asynchromix.AsynchromixClient




.. .. automodule:: apps.asynchromix.asynchromix


Questions
---------
When submitting a message to Ethereum, via the contract, is the
identity of the client public? Can it be kept hidden?



.. _Ganache: https://github.com/trufflesuite/ganache
