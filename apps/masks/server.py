import asyncio
import logging
import time

from web3.contract import ConciseContract

from apps.utils import get_contract_abi, wait_for_receipt

from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
from honeybadgermpc.mpc import Mpc
from honeybadgermpc.offline_randousha import randousha
from honeybadgermpc.utils.misc import (
    print_exception_callback,
    subscribe_recv,
    wrap_send,
)

field = GF(Subgroup.BLS12_381)


class Server:
    """MPC server class to ..."""

    def __init__(self, sid, myid, send, recv, w3, *, contract_context):
        """
        Parameters
        ----------
        sid: int
            Session id.
        myid: int
            Client id.
        send:
            Function used to send messages.
        recv:
            Function used to receive messages.
        w3:
            Connection instance to an Ethereum node.
        contract_context: dict
            Contract attributes needed to interact with the contract
            using web3. Should contain the address, name and source code
            file path.
        """
        self.sid = sid
        self.myid = myid
        self._contract_context = contract_context
        self.contract = self._fetch_contract(w3, **contract_context)
        self.w3 = w3
        self._init_tasks()
        self._subscribe_task, subscribe = subscribe_recv(recv)

        def _get_send_recv(tag):
            return wrap_send(tag, send), subscribe(tag)

        self.get_send_recv = _get_send_recv
        self._inputmasks = []

    def _fetch_contract(self, w3, *, address, name, filepath):
        abi = get_contract_abi(contract_name=name, contract_filepath=filepath)
        contract = w3.eth.contract(address=address, abi=abi)
        contract_concise = ConciseContract(contract)
        # Call read only methods to check
        contract_concise.n()
        # TODO check n?
        return contract

    def _init_tasks(self):
        self._task1 = asyncio.ensure_future(self._offline_inputmasks_loop())
        self._task1.add_done_callback(print_exception_callback)
        self._task2 = asyncio.ensure_future(self._client_request_loop())
        self._task2.add_done_callback(print_exception_callback)
        self._task3 = asyncio.ensure_future(self._mpc_loop())
        self._task3.add_done_callback(print_exception_callback)
        self._task4 = asyncio.ensure_future(self._mpc_initiate_loop())
        self._task4.add_done_callback(print_exception_callback)

    async def join(self):
        await self._task1
        await self._task2
        await self._task3
        await self._task4
        await self._subscribe_task

    #######################
    # Step 1. Offline Phase
    #######################
    """
    1a. offline inputmasks
    """

    async def _preprocess_report(self):
        # Submit the preprocessing report
        tx_hash = self.contract.functions.preprocess_report(
            [len(self._inputmasks)]
        ).transact({"from": self.w3.eth.accounts[self.myid]})

        # Wait for the tx receipt
        tx_receipt = await wait_for_receipt(self.w3, tx_hash)
        return tx_receipt

    async def _offline_inputmasks_loop(self):
        contract_concise = ConciseContract(self.contract)
        n = contract_concise.n()
        t = contract_concise.t()
        preproc_round = 0
        k = 1
        while True:
            # Step 1. I) Wait until needed
            while True:
                inputmasks_available = contract_concise.inputmasks_available()
                totalmasks = contract_concise.preprocess()
                # Policy: try to maintain a buffer of 10 input masks
                target = 10
                if inputmasks_available < target:
                    break
                # already have enough input masks, sleep
                await asyncio.sleep(5)

            # Step 1. II) Run Randousha
            logging.info(
                f"[{self.myid}] totalmasks: {totalmasks} \
                inputmasks available: {inputmasks_available} \
                target: {target} Initiating Randousha {k * (n - 2*t)}"
            )
            send, recv = self.get_send_recv(f"preproc:inputmasks:{preproc_round}")
            start_time = time.time()
            rs_t, rs_2t = zip(*await randousha(n, t, k, self.myid, send, recv, field))
            assert len(rs_t) == len(rs_2t) == k * (n - 2 * t)

            # Note: here we just discard the rs_2t
            # In principle both sides of randousha could be used with
            # a small modification to randousha
            end_time = time.time()
            logging.debug(f"[{self.myid}] Randousha finished in {end_time-start_time}")
            logging.debug(f"len(rs_t): {len(rs_t)}")
            logging.debug(f"rs_t: {rs_t}")
            self._inputmasks += rs_t

            # Step 1. III) Submit an updated report
            await self._preprocess_report()

            # Increment the preprocessing round and continue
            preproc_round += 1

    async def _client_request_loop(self):
        # Task 2. Handling client input
        # TODO: if a client requests a share,
        # check if it is authorized and if so send it along
        pass

    async def _mpc_loop(self):
        # Task 3. Participating in MPC epochs
        contract_concise = ConciseContract(self.contract)
        n = contract_concise.n()
        t = contract_concise.t()

        epoch = 0
        while True:
            # 3.a. Wait for the next MPC to be initiated
            while True:
                epochs_initiated = contract_concise.epochs_initiated()
                if epochs_initiated > epoch:
                    break
                await asyncio.sleep(5)

            # 3.b. Collect the input
            # Get the public input (masked message)
            masked_message_bytes, inputmask_idx = contract_concise.input_queue(epoch)
            masked_message = field(int.from_bytes(masked_message_bytes, "big"))
            inputmask = self._inputmasks[inputmask_idx]  # Get the input mask
            msg_field_elem = masked_message - inputmask

            # 3.d. Call the MPC program
            async def prog(ctx):
                logging.info(f"[{ctx.myid}] Running MPC network")
                msg_share = ctx.Share(msg_field_elem)
                opened_value = await msg_share.open()
                msg = opened_value.value.to_bytes(32, "big").decode().strip("\x00")
                return msg

            send, recv = self.get_send_recv(f"mpc:{epoch}")
            logging.info(f"[{self.myid}] MPC initiated:{epoch}")

            config = {}
            ctx = Mpc(f"mpc:{epoch}", n, t, self.myid, send, recv, prog, config)
            result = await ctx._run()
            logging.info(f"[{self.myid}] MPC complete {result}")

            # 3.e. Output the published messages to contract
            tx_hash = self.contract.functions.propose_output(epoch, result).transact(
                {"from": self.w3.eth.accounts[self.myid]}
            )
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)
            rich_logs = self.contract.events.MpcOutput().processReceipt(tx_receipt)
            if rich_logs:
                epoch = rich_logs[0]["args"]["epoch"]
                output = rich_logs[0]["args"]["output"]
                logging.info(f"[{self.myid}] MPC OUTPUT[{epoch}] {output}")

            epoch += 1

    async def _mpc_initiate_loop(self):
        # Task 4. Initiate MPC epochs
        contract_concise = ConciseContract(self.contract)
        K = contract_concise.K()  # noqa: N806
        while True:
            # Step 4.a. Wait until there are k values then call initiate_mpc
            while True:
                inputs_ready = contract_concise.inputs_ready()
                if inputs_ready >= K:
                    break
                await asyncio.sleep(5)

            # Step 4.b. Call initiate_mpc
            try:
                tx_hash = self.contract.functions.initiate_mpc().transact(
                    {"from": self.w3.eth.accounts[0]}
                )
            except ValueError as err:
                # Since only one server is needed to initiate the MPC, once
                # intiated, a ValueError will occur due to the race condition
                # between the servers.
                logging.debug(err)
                continue
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)
            rich_logs = self.contract.events.MpcEpochInitiated().processReceipt(
                tx_receipt
            )
            if rich_logs:
                epoch = rich_logs[0]["args"]["epoch"]
                logging.info(f"[{self.myid}] MPC epoch initiated: {epoch}")
            else:
                logging.info(f"[{self.myid}] initiate_mpc failed (redundant?)")
            await asyncio.sleep(10)
