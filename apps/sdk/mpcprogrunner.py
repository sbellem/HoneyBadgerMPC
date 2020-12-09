import asyncio
import logging
import pickle

from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
from honeybadgermpc.mpc import Mpc
from honeybadgermpc.utils.misc import _create_task

field = GF(Subgroup.BLS12_381)


class MPCProgRunner:
    """MPC participant responsible to take part into a multi-party
    computation.

    """

    def __init__(
        self,
        sid,
        myid,
        w3,
        *,
        contract=None,
        db=None,
        channel=None,
        prog=None,
        mpc_config=None,
    ):
        """
        Parameters
        ----------
        sid: int
            Session id.
        myid: int
            Client id.
        w3:
            Connection instance to an Ethereum node.
        contract_context: dict
            Contract attributes needed to interact with the contract
            using web3. Should contain the address, name and source code
            file path.
        """
        self.sid = sid
        self.myid = myid
        self.contract = contract
        self.w3 = w3
        self._create_tasks()
        self.get_send_recv = channel
        self.db = db
        self.prog = prog
        self.mpc_config = mpc_config or {}
        self.elements = {}  # cache of elements (inputmasks, triples, bits, etc)
        self._init_elements("inputmasks")

    def _init_elements(self, *element_names):
        for element_name in element_names:
            try:
                _element_set = self.db[element_name.encode()]
            except KeyError:
                element_set = []
            else:
                element_set = pickle.loads(_element_set)
            self.elements[element_name] = element_set

    def _create_tasks(self):
        self._mpc = _create_task(self._mpc_loop())
        self._mpc_init = _create_task(self._mpc_initiate_loop())

    async def start(self):
        await self._mpc
        await self._mpc_init

    async def _mpc_loop(self):
        logging.info("MPC loop started ...")
        # Task 3. Participating in MPC epochs
        n = self.contract.caller.n()
        t = self.contract.caller.t()
        K = self.contract.caller.K()  # noqa: N806

        epoch = 0
        while True:
            logging.info(f"starting new loop at epoch: {epoch}")
            # 3.a. Wait for the next MPC to be initiated
            while True:
                logging.info(f"waiting for epoch {epoch} to be initiated ...")
                epochs_initiated = self.contract.caller.epochs_initiated()
                logging.info(
                    f"result of querying contract for epochs initiated: {epochs_initiated}"
                )
                if epochs_initiated > epoch:
                    break
                await asyncio.sleep(5)

            # 3.b. Collect the inputs
            inputs = []
            for idx in range(epoch * K, (epoch + 1) * K):
                # Get the public input (masked message)
                masked_message_bytes, inputmask_idx = self.contract.caller.input_queue(
                    idx
                )
                logging.info(f"masked_message_bytes: {masked_message_bytes}")
                logging.info(f"inputmask_idx: {inputmask_idx}")
                masked_message = field(int.from_bytes(masked_message_bytes, "big"))
                logging.info(f"masked_message: {masked_message}")
                if inputmask_idx not in self.elements["inputmasks"]:
                    self.elements["inputmasks"] = pickle.loads(self.db[b"inputmasks"])
                try:
                    inputmask = self.elements["inputmasks"][inputmask_idx]
                except IndexError as err:
                    logging.error(
                        f"inputmasks id: {inputmask_idx} not in {self.elements['inputmasks']}"
                    )
                    raise err

                msg_field_elem = masked_message - inputmask
                inputs.append(msg_field_elem)

            send, recv = self.get_send_recv(f"mpc:{epoch}")
            logging.info(f"[{self.myid}] MPC initiated:{epoch}")

            prog_kwargs = {"field_elements": inputs}
            ctx = Mpc(
                f"mpc:{epoch}",
                n,
                t,
                self.myid,
                send,
                recv,
                self.prog,
                self.mpc_config,
                **prog_kwargs,
            )
            result = await ctx._run()
            logging.info(f"[{self.myid}] MPC complete {result}")

            # 3.e. Output the published messages to contract
            result = ",".join(result)
            tx_hash = self.contract.functions.propose_output(epoch, result).transact(
                {"from": self.w3.eth.accounts[self.myid]}
            )
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            rich_logs = self.contract.events.MpcOutput().processReceipt(tx_receipt)
            if rich_logs:
                epoch = rich_logs[0]["args"]["epoch"]
                output = rich_logs[0]["args"]["output"]
                logging.info(40 * "*")
                logging.info(f"[{self.myid}] MPC OUTPUT[{epoch}] {output}")
                logging.info(40 * "*")

            epoch += 1

    async def _mpc_initiate_loop(self):
        logging.info("MPC initiator loop started ...")
        # Task 4. Initiate MPC epochs
        K = self.contract.caller.K()  # noqa: N806
        epoch = None
        while True:
            logging.info(f"looping to initiate MPC for epoch {epoch} ...")
            # Step 4.a. Wait until there are k values then call initiate_mpc
            while True:
                logging.info("waiting loop for enough inputs ready ...")
                logging.info("querying contract for inputs_ready()")
                inputs_ready = self.contract.caller.inputs_ready()
                logging.info(f"number of inputs ready: {inputs_ready}")
                if inputs_ready >= K:
                    break
                await asyncio.sleep(5)

            # Step 4.b. Call initiate_mpc
            logging.info("call contract function initiate_mpc() ...")
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
            tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
            rich_logs = self.contract.events.MpcEpochInitiated().processReceipt(
                tx_receipt
            )
            if rich_logs:
                epoch = rich_logs[0]["args"]["epoch"]
                logging.info(f"[{self.myid}] MPC epoch initiated: {epoch}")
            else:
                logging.info(f"[{self.myid}] initiate_mpc failed (redundant?)")
            await asyncio.sleep(10)
