import asyncio
import logging
import pickle
import time
from functools import partial

from aiohttp import web

from web3.contract import ConciseContract

from apps.utils import fetch_contract, wait_for_receipt

from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
from honeybadgermpc.offline_randousha import randousha
from honeybadgermpc.utils.misc import (
    _get_send_recv,
    print_exception_callback,
    subscribe_recv,
)

field = GF(Subgroup.BLS12_381)


class PrePreprocessor:
    """Class to generate preprocessing elements.


    Notes
    -----
    From the paper [0]_:

        The offline phase [9]_, [11]_ runs continuously to replenish a
        buffer of preprocessing elements used by the online phase.

    References
    ----------
    .. [0] Donghang Lu, Thomas Yurek, Samarth Kulshreshtha, Rahul Govind,
        Aniket Kate, and Andrew Miller. 2019. HoneyBadgerMPC and
        AsynchroMix: Practical Asynchronous MPC and its Application to
        Anonymous Communication. In Proceedings of the 2019 ACM SIGSAC
        Conference on Computer and Communications Security (CCS ’19).
        Association for Computing Machinery, New York, NY, USA, 887–903.
        DOI:https://doi.org/10.1145/3319535.3354238
    .. [9] Assi Barak, Martin Hirt, Lior Koskas, and Yehuda Lindell.
        2018. An End-to-EndSystem for Large Scale P2P MPC-as-a-Service
        and Low-Bandwidth MPC for Weak Participants. In Proceedings of
        the 2018 ACM SIGSAC Conference on Computer and Communications
        Security. ACM, 695–712.
    .. [11] Zuzana Beerliová-Trubíniová and Martin Hirt. 2008.
        Perfectly-secure MPC with linear communication complexity. In
        Theory of Cryptography Conference. Springer, 213–230.
    """

    def __init__(
        self,
        sid,
        myid,
        send,
        recv,
        w3,
        *,
        contract_context,
        http_host="0.0.0.0",
        http_port=8080,
        sharestore,
    ):
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
        self.contract = fetch_contract(w3, **contract_context)
        self.w3 = w3
        self._init_tasks()
        self._http_host = http_host
        self._http_port = http_port
        self.sharestore = sharestore
        self._subscribe_task, subscribe = subscribe_recv(recv)
        self.get_send_recv = partial(_get_send_recv, send=send, subscribe=subscribe)

    # TODO put in utils
    def _create_task(self, coro, *, name=None):
        task = asyncio.ensure_future(coro)
        task.add_done_callback(print_exception_callback)
        return task

    def _init_tasks(self):
        self._preprocessing = self._create_task(self._offline_inputmasks_loop())
        self._http_server = self._create_task(self._client_request_loop())

    async def start(self):
        await self._preprocessing
        await self._http_server
        await self._subscribe_task

    async def _preprocess_report(self, *, number_of_inputmasks):
        # Submit the preprocessing report
        tx_hash = self.contract.functions.preprocess_report(
            [number_of_inputmasks]
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

                logging.info(f"available input masks: {inputmasks_available}")
                logging.info(f"total input masks: {totalmasks}")
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
            try:
                _inputmasks = self.sharestore[b"inputmasks"]
            except KeyError:
                inputmasks = []
            else:
                inputmasks = pickle.loads(_inputmasks)
            inputmasks += rs_t
            self.sharestore[b"inputmasks"] = pickle.dumps(inputmasks)

            # Step 1. III) Submit an updated report
            await self._preprocess_report(number_of_inputmasks=len(inputmasks))

            # Increment the preprocessing round and continue
            preproc_round += 1

    ##################################
    # Web server for input mask shares
    ##################################

    async def _client_request_loop(self):
        """ Task 2. Handling client input

        .. todo:: if a client requests a share, check if it is
            authorized and if so send it along

        """
        routes = web.RouteTableDef()

        @routes.get("/inputmasks/{idx}")
        async def _handler(request):
            idx = int(request.match_info.get("idx"))
            try:
                _inputmasks = self.sharestore[b"inputmasks"]
            except KeyError:
                inputmasks = []
            else:
                inputmasks = pickle.loads(_inputmasks)
            try:
                inputmask = inputmasks[idx]
            except IndexError:
                logging.error(f"No input mask at index {idx}")
                raise

            data = {
                "inputmask": inputmask,
                "server_id": self.myid,
                "server_port": self._http_port,
            }
            return web.json_response(data)

        app = web.Application()
        app.add_routes(routes)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self._http_host, port=self._http_port)
        await site.start()
        print(f"======= Serving on http://{self._http_host}:{self._http_port}/ ======")
        # pause here for very long time by serving HTTP requests and
        # waiting for keyboard interruption
        await asyncio.sleep(100 * 3600)
