"""Implementation of a simple MPC Coordinator using an EVM blockchain."""
import asyncio
import logging
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from ethereum.tools._solidity import compile_code as compile_source

from web3 import HTTPProvider, Web3
from web3.contract import ConciseContract
from web3.exceptions import TransactionNotFound

from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
from honeybadgermpc.mpc import Mpc
from honeybadgermpc.offline_randousha import randousha
from honeybadgermpc.polynomial import EvalPoint, polynomials_over
from honeybadgermpc.preprocessing import PreProcessedElements
from honeybadgermpc.router import SimpleRouter
from honeybadgermpc.utils.misc import (
    print_exception_callback,
    subscribe_recv,
    wrap_send,
)

field = GF(Subgroup.BLS12_381)


async def wait_for_receipt(w3, tx_hash):
    while True:
        try:
            tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        except TransactionNotFound:
            tx_receipt = None
        if tx_receipt is not None:
            break
        await asyncio.sleep(5)
    return tx_receipt


class Client:
    """An MPC client that sends "masked" messages to an Ethereum contract."""

    def __init__(self, sid, myid, send, recv, w3, contract, req_mask):
        """
        Parameters
        ----------
        sid: int
            Session id.
        myid: int
            Client id.
        send:
            Function used to send messages. Not used?
        recv:
            Function used to receive messages. Not used?
        w3:
            Connection instance to an Ethereum node.
        contract:
            Contract instance on the Ethereum blockchain.
        req_mask:
            Function used to request an input mask from a server.
        """
        self.sid = sid
        self.myid = myid
        self.contract = contract
        self.w3 = w3
        self.req_mask = req_mask
        self._task = asyncio.ensure_future(self._run())
        self._task.add_done_callback(print_exception_callback)
        self._k = 2  # number of messages to send per epoch

    async def _run(self):
        contract_concise = ConciseContract(self.contract)
        await asyncio.sleep(60)  # give the servers a head start
        # Client sends several batches of messages then quits
        # for epoch in range(1000):
        for epoch in range(3):
            logging.info(f"[Client] Starting Epoch {epoch}")
            receipts = []
            for i in range(self._k):
                m = f"Hello Shard! (Epoch: {epoch}) :{i}"
                task = asyncio.ensure_future(self.send_message(m))
                task.add_done_callback(print_exception_callback)
                receipts.append(task)
            receipts = await asyncio.gather(*receipts)

            while True:  # wait before sending next
                if contract_concise.outputs_ready() > epoch:
                    break
                await asyncio.sleep(5)

    async def _get_inputmask(self, idx):
        # Private reconstruct
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

    async def join(self):
        await self._task

    async def send_message(self, m):
        # Submit a message to be unmasked
        contract_concise = ConciseContract(self.contract)

        # Step 1. Wait until there is input available, and enough triples
        while True:
            inputmasks_available = contract_concise.inputmasks_available()
            # logging.infof'inputmasks_available: {inputmasks_available}')
            if inputmasks_available >= 1:
                break
            await asyncio.sleep(5)

        # Step 2. Reserve the input mask
        tx_hash = self.contract.functions.reserve_inputmask().transact(
            {"from": self.w3.eth.accounts[0]}
        )
        tx_receipt = await wait_for_receipt(self.w3, tx_hash)
        rich_logs = self.contract.events.InputMaskClaimed().processReceipt(tx_receipt)
        if rich_logs:
            inputmask_idx = rich_logs[0]["args"]["inputmask_idx"]
        else:
            raise ValueError

        # Step 3. Fetch the input mask from the servers
        inputmask = await self._get_inputmask(inputmask_idx)
        message = int.from_bytes(m.encode(), "big")
        masked_message = message + inputmask
        masked_message_bytes = self.w3.toBytes(hexstr=hex(masked_message.value))
        masked_message_bytes = masked_message_bytes.rjust(32, b"\x00")

        # Step 4. Publish the masked input
        tx_hash = self.contract.functions.submit_message(
            inputmask_idx, masked_message_bytes
        ).transact({"from": self.w3.eth.accounts[0]})
        tx_receipt = await wait_for_receipt(self.w3, tx_hash)


class Server(object):
    """MPC server class to ..."""

    def __init__(self, sid, myid, send, recv, w3, contract):
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
        contract:
            Contract instance on the Ethereum blockchain.
        """
        self.sid = sid
        self.myid = myid
        self.contract = contract
        self.w3 = w3
        self._init_tasks()
        self._subscribe_task, subscribe = subscribe_recv(recv)

        def _get_send_recv(tag):
            return wrap_send(tag, send), subscribe(tag)

        self.get_send_recv = _get_send_recv
        self._inputmasks = []

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
        K = contract_concise.K()  # noqa: N806
        preproc_round = 0
        k = K // (n - 2 * t)  # batch size
        while True:
            # Step 1. I) Wait until needed
            while True:
                inputmasks_available = contract_concise.inputmasks_available()
                totalmasks = contract_concise.preprocess()
                # Policy: try to maintain a buffer of 10 * K input masks
                target = 10 * K
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
        K = contract_concise.K()  # noqa: N806

        epoch = 0
        while True:
            # 3.a. Wait for the next MPC to be initiated
            while True:
                epochs_initiated = contract_concise.epochs_initiated()
                if epochs_initiated > epoch:
                    break
                await asyncio.sleep(5)

            # 3.b. Collect the inputs
            inputs = []
            for idx in range(epoch * K, (epoch + 1) * K):
                # Get the public input (masked message)
                masked_message_bytes, inputmask_idx = contract_concise.input_queue(idx)
                masked_message = field(int.from_bytes(masked_message_bytes, "big"))
                # Get the input mask
                inputmask = self._inputmasks[inputmask_idx]

                m_share = masked_message - inputmask
                inputs.append(m_share)

            # 3.d. Call the MPC program
            async def prog(ctx):
                logging.info(f"[{ctx.myid}] Running MPC network")
                inps = list(map(ctx.Share, inputs))
                assert len(inps) == K
                _shares = ctx.ShareArray(inputs)
                opened_values = await _shares.open()
                msgs = [
                    m.value.to_bytes(32, "big").decode().strip("\x00")
                    for m in opened_values
                ]
                return msgs

            send, recv = self.get_send_recv(f"mpc:{epoch}")
            logging.info(f"[{self.myid}] MPC initiated:{epoch}")

            config = {}
            ctx = Mpc(f"mpc:{epoch}", n, t, self.myid, send, recv, prog, config)
            result = await ctx._run()
            logging.info(f"[{self.myid}] MPC complete {result}")

            # 3.e. Output the published messages to contract
            result = ",".join(result)
            tx_hash = self.contract.functions.propose_output(epoch, result).transact(
                {"from": self.w3.eth.accounts[self.myid]}
            )
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)
            rich_logs = self.contract.events.MpcOutput().processReceipt(tx_receipt)
            if rich_logs:
                epoch = rich_logs[0]["args"]["epoch"]
                output = rich_logs[0]["args"]["output"]
                logging.info(f"[{self.myid}] MPC OUTPUT[{epoch}] {output}")
            else:
                pass

            epoch += 1

        pass

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


###############
# Ganache test
###############
async def main_loop(w3, *, contract_name, contract_filepath):
    pp_elements = PreProcessedElements()
    # deletes sharedata/ if present
    pp_elements.clear_preprocessing()

    # Step 1.
    # Create the coordinator contract and web3 interface to it
    compiled_sol = compile_source(
        open(contract_filepath).read()
    )  # Compiled source code
    contract_interface = compiled_sol[f"<stdin>:{contract_name}"]
    contract_class = w3.eth.contract(
        abi=contract_interface["abi"], bytecode=contract_interface["bin"]
    )

    # 2 shards: n=4, t=1 for each shard
    shard_1_accounts = w3.eth.accounts[:4]
    shard_2_accounts = w3.eth.accounts[4:8]
    tx_hash = contract_class.constructor(
        shard_1_accounts, shard_2_accounts, 1
    ).transact({"from": w3.eth.accounts[0]})

    # Get tx receipt to get contract address
    tx_receipt = await wait_for_receipt(w3, tx_hash)
    contract_address = tx_receipt["contractAddress"]

    if w3.eth.getCode(contract_address) == b"":
        logging.critical("code was empty 0x, constructor may have run out of gas")
        raise ValueError

    # Contract instance in concise mode
    abi = contract_interface["abi"]
    contract = w3.eth.contract(address=contract_address, abi=abi)
    contract_concise = ConciseContract(contract)

    # Call read only methods to check
    n = contract_concise.n()

    # Step 2: Create the servers
    router = SimpleRouter(2 * n)
    sends, recvs = router.sends, router.recvs
    servers = [Server("sid", i, sends[i], recvs[i], w3, contract) for i in range(2 * n)]

    # Step 3. Create the client
    # TODO communicate with server instead of fetching from list of servers
    async def req_mask(i, idx):
        # client requests input mask {idx} from server {i}
        return servers[i]._inputmasks[idx]

    client = Client("sid", "client", None, None, w3, contract, req_mask)

    # Step 4. Wait for conclusion
    for i, server in enumerate(servers):
        await server.join()
    await client.join()


@contextmanager
def run_and_terminate_process(*args, **kwargs):
    try:
        p = subprocess.Popen(*args, **kwargs)
        yield p
    finally:
        logging.info(f"Killing ganache-cli {p.pid}")
        p.terminate()  # send sigterm, or ...
        p.kill()  # send sigkill
        p.wait()
        logging.info("done")


def run_eth(*, contract_name, contract_filepath):
    w3 = Web3(HTTPProvider())  # Connect to localhost:8545
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    try:
        logging.info("entering loop")
        loop.run_until_complete(
            asyncio.gather(
                main_loop(
                    w3, contract_name=contract_name, contract_filepath=contract_filepath
                )
            )
        )
    finally:
        logging.info("closing")
        loop.close()


def test_asynchromix(contract_name=None, contract_filepath=None):
    import time

    # cmd = 'testrpc -a 50 2>&1 | tee -a acctKeys.json'
    # with run_and_terminate_process(cmd, shell=True,
    # stdout=sys.stdout, stderr=sys.stderr) as proc:
    cmd = "ganache-cli -p 8545 -a 50 -b 1 > acctKeys.json 2>&1"
    logging.info(f"Running {cmd}")
    with run_and_terminate_process(cmd, shell=True):
        time.sleep(5)
        run_eth(contract_name=contract_name, contract_filepath=contract_filepath)


if __name__ == "__main__":
    # Launch an ethereum test chain
    contract_name = "MpcCoordinator"
    contract_filename = "helloshard.sol"
    contract_dir = Path(__file__).resolve().parents[1].joinpath("contracts")
    contract_filepath = contract_dir.joinpath(contract_filename)
    test_asynchromix(contract_name=contract_name, contract_filepath=contract_filepath)
