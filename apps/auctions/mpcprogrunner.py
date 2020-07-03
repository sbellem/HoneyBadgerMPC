import asyncio
import logging
import pickle

from web3.contract import ConciseContract

from apps.toolkit.utils import wait_for_receipt

from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
from honeybadgermpc.mpc import Mpc
from honeybadgermpc.utils.misc import _create_task

# imports needed for asynchromix
from apps.asynchromix.butterfly_network import iterated_butterfly_network
from honeybadgermpc.preprocessing import PreProcessedElements

field = GF(Subgroup.BLS12_381)

# TODO if possible, avoid the need for such a map. One way to do so would be to
# simply adopt the same naming convention for the db and the PreProcessingElements
# methods.
PP_ELEMENTS_MIXIN_MAP = {"triples": "_triples", "bits": "_one_minus_ones"}


def _load_pp_elements(node_id, n, t, epoch, db, cache, elements_metadata):
    cache._init_data_dir()
    elements = {}
    for element_name, slice_size in elements_metadata.items():
        _elements = pickle.loads(db[element_name.encode()])
        elements[element_name] = _elements[
            epoch * slice_size : (epoch + 1) * slice_size
        ]

    mixins = tuple(
        getattr(cache, PP_ELEMENTS_MIXIN_MAP[element_name]) for element_name in elements
    )
    # Hack explanation... the relevant mixins are in triples
    key = (node_id, n, t)
    for mixin in mixins:
        if key in mixin.cache:
            del mixin.cache[key]
            del mixin.count[key]

    for mixin, (kind, elems) in zip(mixins, elements.items()):
        if kind == "triples":
            elems = [e for sublist in elems for e in sublist]
        elems = [e.value for e in elems]
        mixin_filename = mixin.build_filename(n, t, node_id)
        logging.info(f"writing preprocessed {kind} to file {mixin_filename}")
        logging.info(f"number of elements is: {len(elems)}")
        mixin._write_preprocessing_file(mixin_filename, t, node_id, elems, append=False)

    for mixin in mixins:
        mixin._refresh_cache()


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
        # self._init_elements("inputmasks", "triples", "bits")
        self._init_elements("inputmasks")

    @property
    def eth_account(self):
        return self.w3.eth.accounts[self.myid]

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
        contract_concise = ConciseContract(self.contract)
        n = contract_concise.n()
        t = contract_concise.t()
        K = contract_concise.K()  # noqa: N806

        # XXX asynchromix
        PER_MIX_TRIPLES = contract_concise.PER_MIX_TRIPLES()  # noqa: N806
        PER_MIX_BITS = contract_concise.PER_MIX_BITS()  # noqa: N806
        pp_elements = PreProcessedElements()
        # deletes sharedata/ if present
        pp_elements.clear_preprocessing()
        # XXX asynchromix

        epoch = 0
        while True:
            logging.info(f"starting new loop at epoch: {epoch}")
            # 3.a. Wait for the next MPC to be initiated
            while True:
                logging.info(f"waiting for epoch {epoch} to be initiated ...")
                epochs_initiated = contract_concise.epochs_initiated()
                logging.info(
                    f"result of querying contract for epochs initiated: {epochs_initiated}"
                )
                if epochs_initiated > epoch:
                    break
                await asyncio.sleep(5)

            # 3.b. Collect the input
            # Get the public input (masked message)
            inputs = []
            for idx in range(epoch * K, (epoch + 1) * K):
                masked_message_bytes, inputmask_idx = contract_concise.input_queue(idx)
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

            _load_pp_elements(
                self.myid,
                n,
                t,
                epoch,
                self.db,
                pp_elements,
                {"triples": PER_MIX_TRIPLES, "bits": PER_MIX_BITS},
            )
            send, recv = self.get_send_recv(f"mpc:{epoch}")
            logging.info(f"[{self.myid}] MPC initiated:{epoch}")

            prog_kwargs = {
                "field_elements": inputs,
                "mixer": iterated_butterfly_network,
            }
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
            result = ",".join(str(i) for i in result)
            tx_hash = self.contract.functions.propose_output(epoch, result).transact(
                # {"from": self.w3.eth.accounts[self.myid]}
                {"from": self.eth_account}
            )
            tx_receipt = await wait_for_receipt(self.w3, tx_hash)
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
        contract_concise = ConciseContract(self.contract)
        K = contract_concise.K()  # noqa: N806
        epoch = None
        while True:
            logging.info(f"looping to initiate MPC for epoch {epoch} ...")
            # Step 4.a. Wait until there are k values then call initiate_mpc
            while True:
                logging.info("waiting loop for enough inputs and mixes ready ...")
                logging.info("querying contract for inputs_ready()")
                inputs_ready = contract_concise.inputs_ready()
                logging.info(f"number of inputs ready: {inputs_ready}")

                logging.info("querying contract for mixes_available()")
                mixes_avail = contract_concise.mixes_available()
                logging.info(f"number of mixes available: {mixes_avail}")
                if inputs_ready >= K and mixes_avail >= 1:
                    break
                await asyncio.sleep(5)

            # Step 4.b. Call initiate_mpc
            logging.info("call contract function initiate_mpc() ...")
            try:
                tx_hash = self.contract.functions.initiate_mpc().transact(
                    # {"from": self.w3.eth.accounts[0]}
                    # {"from": self.w3.eth.accounts[self.myid]}
                    {"from": self.eth_account}
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
