"""MPC server code.

**Questions**
How are crash faults supposed to be handled? Currently, if a server comes
back it will be in an inconsistent state. For instance, its input masks list
will be empty, likely differing from the contract.

Also, the epoch count will be reset to 0 if a server restarts. Not clear
what this may cause, besides the server attempting to unmask messages that
have already been unmasked ...
"""
import logging  # noqa F401 - importing for contract

from apps.utils import compile_ratel_contract, fetch_contract

from honeybadgermpc.utils.misc import _get_pubsub_channel


def _get_contract_context(eth_config):
    from apps.masks.config import CONTRACT_ADDRESS_FILEPATH
    from apps.utils import get_contract_address

    context = {
        "address": get_contract_address(CONTRACT_ADDRESS_FILEPATH),
        "filepath": eth_config["contract_path"],
        "name": eth_config["contract_name"],
    }
    return context


def _create_w3(eth_config):
    from web3 import HTTPProvider, Web3

    eth_rpc_hostname = eth_config["rpc_host"]
    eth_rpc_port = eth_config["rpc_port"]
    w3_endpoint_uri = f"http://{eth_rpc_hostname}:{eth_rpc_port}"
    return Web3(HTTPProvider(w3_endpoint_uri))


class MPCServer:
    """MPC server class to ..."""

    def __init__(
        self,
        sid,
        myid,
        *,
        send,
        recv,
        w3,
        contract_context=None,
        db=None,
        preprocessor_class=None,
        httpserver_class=None,
        mpcprogrunner_class=None,
        http_context,
        # prog=None,
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
        output = compile_ratel_contract(
            contract_context["filepath"], vyper_output_formats=("abi",)
        )
        vyper_output, mpc_output = output["vyper"], output["mpc"]
        self.contract = fetch_contract(
            w3, address=contract_context["address"], abi=vyper_output["abi"]
        )
        self.w3 = w3
        self.subscribe_task, self.channel = _get_pubsub_channel(send, recv)
        self.get_send_recv = self.channel
        self.db = db
        self.preprocessor_class = preprocessor_class
        self.httpserver_class = httpserver_class
        self.http_context = http_context
        self.mpcprogrunner_class = mpcprogrunner_class

        # NOTE "Load" MPC prog
        exec(mpc_output["src_code"], globals())
        self.prog = prog  # noqa F821
        self._init_tasks()

    def _init_tasks(self):
        self.preprocessor = self.preprocessor_class(
            self.sid,
            self.myid,
            self.w3,
            contract=self.contract,
            db=self.db,
            channel=self.channel,
        )
        self.http_server = self.httpserver_class(
            self.sid,
            self.myid,
            host=self.http_context["host"],
            port=self.http_context["port"],
            db=self.db,
        )
        self.mpc_prog_runner = self.mpcprogrunner_class(
            self.sid,
            self.myid,
            self.w3,
            contract=self.contract,
            db=self.db,
            channel=self.channel,
            prog=self.prog,
        )

    async def start(self):
        await self.preprocessor.start()
        await self.http_server.start()
        await self.mpc_prog_runner.start()
        await self.subscribe_task


async def runner(
    session_id,
    myid,
    *,
    host,
    mpc_port,
    peers,
    w3,
    contract_context,
    db,
    http_context,
    preprocessor_class,
    httpserver_class,
    mpcprogrunner_class,
):
    from honeybadgermpc.ipc import NodeCommunicator2

    node_communicator = NodeCommunicator2(
        myid=myid, host=host, port=mpc_port, peers_config=peers, linger_timeout=2
    )
    async with node_communicator as nc:
        mpcserver = MPCServer(
            session_id,
            myid,
            send=nc.send,
            recv=nc.recv,
            w3=w3,
            contract_context=contract_context,
            db=db,
            http_context=http_context,
            preprocessor_class=preprocessor_class,
            httpserver_class=httpserver_class,
            mpcprogrunner_class=mpcprogrunner_class,
        )
        await mpcserver.start()


if __name__ == "__main__":
    import asyncio

    import toml

    from apps.httpserver import HTTPServer
    from apps.preprocessor import PreProcessor
    from apps.parsers import ServerArgumentParser
    from apps.masks.mpcprogrunner import MPCProgRunner

    # arg parsing
    parser = ServerArgumentParser()
    args = parser.parse_args()

    # read config and merge with cmdline args -- cmdline args have priority
    config = toml.load(args.config_path)
    _args = parser.post_process_args(args, config)

    asyncio.run(
        runner(
            "sid",
            _args["myid"],
            host=_args["host"],
            mpc_port=_args["mpc_port"],
            peers=_args["peers"],
            w3=_args["w3"],
            contract_context=_args["contract_context"],
            db=_args["db"],
            http_context={"host": _args["host"], "port": _args["http_port"]},
            preprocessor_class=PreProcessor,
            httpserver_class=HTTPServer,
            mpcprogrunner_class=MPCProgRunner,
        )
    )
