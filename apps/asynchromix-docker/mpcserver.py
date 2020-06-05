"""MPC server code.

**Questions**
How are crash faults supposed to be handled? Currently, if a server comes
back it will be in an inconsistent state. For instance, its input masks list
will be empty, likely differing from the contract.

Also, the epoch count will be reset to 0 if a server restarts. Not clear
what this may cause, besides the server attempting to unmask messages that
have already been unmasked ...
"""
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


class RPCServer:
    """RPC server to handle requests from a client that is on the same host
    as the MPC player.

    Not sure if we need this ...
    """


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


async def main(
    session_id,
    myid,
    *,
    host,
    mpc_port,
    peers,
    # node_communicator,
    w3,
    contract_context,
    db,
    http_context,
    preprocessor_class,
    httpserver_class,
    mpcprogrunner_class,
    prog=None,
):
    from honeybadgermpc.ipc import NodeCommunicator2

    node_communicator = NodeCommunicator2(
        myid=myid, host=host, port=mpc_port, peers_config=peers, linger_timeout=2
    )
    # await node_communicator._setup()
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
            # prog=prog,
        )
        await mpcserver.start()
    # await nc._exit()


if __name__ == "__main__":
    import asyncio
    import argparse
    import logging
    from pathlib import Path
    import plyvel
    import toml
    from web3 import HTTPProvider, Web3

    # from honeybadgermpc.ipc import NodeCommunicator2
    from apps.masks.config import CONTRACT_ADDRESS_FILEPATH
    from apps.masks.httpserver import HTTPServer
    from apps.masks.mpcprogrunner import MPCProgRunner
    from apps.masks.preprocessor import PreProcessor
    from apps.db import LevelDB
    from apps.utils import get_contract_address

    PARENT_DIR = Path(__file__).resolve().parent
    # arg parsing
    default_hbmpc_home = Path.home().joinpath(".hbmpc")
    default_config_path = default_hbmpc_home.joinpath("config.toml")
    parser = argparse.ArgumentParser(description="MPC server configuration.")
    parser.add_argument(
        "-c",
        "--config-path",
        default=str(default_config_path),
        help=f"Configuration file to use. Defaults to '{default_config_path}'.",
    )
    parser.add_argument(
        "--hbmpc-home",
        type=str,
        help=(
            "Home directory to store configurations, public and private data. "
            "If not provided, will fall back on value specified in config file. "
            f"If absent from config file will default to {default_hbmpc_home}."
        ),
    )
    parser.add_argument(
        "--id",
        type=int,
        help=(
            "Unique identifier for that server within an MPC network. "
            "If not provided, will fall back on value specified in config file. "
            "Failure to provide the id as a command line argument or in the config "
            "file will result in an error."
        ),
    )
    parser.add_argument(
        "--host",
        type=str,
        help=(
            "Host or ip address of that MPC server. "
            "If not provided, will fall back on value specified in config file. "
            "Failure to provide the host as a command line argument or in the config "
            "file will result in an error."
        ),
    )
    default_mpc_port = 7000
    parser.add_argument(
        "--mpc-port",
        type=int,
        # default=default_mpc_port,
        help=(
            "Listening/router port for MPC communications. "
            f"Defaults to '{default_mpc_port}' or to what is provided in config file. "
            "Note that if that if a command line argument is provided it will "
            " overwrite what is given in the config file."
        ),
    )
    default_http_port = 8080
    parser.add_argument(
        "--http-port",
        type=int,
        # default=default_http_port,
        help=(
            "Listening port for HTTP client requests. "
            f"Defaults to '{default_http_port}' or to what is provided in config file. "
            "Note that if that if a command line argument is provided it will "
            " overwrite what is given in the config file."
        ),
    )
    parser.add_argument(
        "--eth-rpc-host",
        type=str,
        help=(
            "RPC host or ip address to connect to an ethereum node. "
            "If not provided, will fall back on value specified in config file. "
            "Failure to provide the ethereum rpc host as a command line argument "
            "or in the config file will result in an error."
        ),
    )
    default_eth_rpc_port = 8545
    parser.add_argument(
        "--eth-rpc-port",
        type=int,
        help=(
            "RPC port to connect to an ethereum node. Defaults to "
            f"'{default_eth_rpc_port}' or to what is provided in config file. "
            "Note that if that if a command line argument is provided it will "
            " overwrite what is given in the config file."
        ),
    )
    default_db_path = "~/.hbmpc/db"
    parser.add_argument(
        "--db-path",
        type=str,
        help=(
            "Path to the directory where the db is to be located. "
            f"Defaults to '{default_db_path}'."
        ),
    )
    parser.add_argument(
        "--reset-db", action="store_true", help="Resets the database. Be careful!",
    )
    parser.add_argument(
        "--contract-address",
        type=str,
        help=(
            "The ethereum address of the deployed coordinator contract. "
            "If it is not provided, the config file will be looked at. "
            "If absent from the config file, will fetch the address from "
            f"the file {CONTRACT_ADDRESS_FILEPATH}."
        ),
    )
    parser.add_argument(
        "--contract-path",
        type=str,
        help=(
            "The ethereum coordinator contract filepath. "
            "If it is not provided, the config file will be looked at. "
            "If absent from the config file, it will error."
            # TODO - review the above
        ),
    )
    default_contract_name = "MPCCoordinator"
    parser.add_argument(
        "--contract-name",
        type=str,
        help=(
            "The ethereum coordinator contract name. If it is not provided, "
            "the config file will be looked at. If absent from the config "
            f"file, it will be set as {default_contract_name}."
        ),
    )
    default_contract_lang = "vyper"
    parser.add_argument(
        "--contract-lang",
        type=str,
        help=(
            "The ethereum coordinator contract language. "
            "If it is not provided, the config file will be looked at. "
            "If absent from the config file, it will be set to "
            f"'{default_contract_lang}'."
        ),
    )
    args = parser.parse_args()
    config = toml.load(args.config_path)
    hbmpc_home = args.hbmpc_home or config.get("hbmpc_home", default_hbmpc_home)
    mpc_port = args.mpc_port or config.get("mpc_port", default_mpc_port)

    # eth node
    eth_rpc_hostname = args.eth_rpc_host or config["eth"]["rpc_host"]
    eth_rpc_port = args.eth_rpc_port or config["eth"].get(
        "rpc_port", default_eth_rpc_port
    )
    w3_endpoint_uri = f"http://{eth_rpc_hostname}:{eth_rpc_port}"
    w3 = Web3(HTTPProvider(w3_endpoint_uri))

    # For NodeCommunicator
    try:
        myid = args.id or config["id"]
    except KeyError:
        logging.error(
            "Missing server id! Must be provided as a command line "
            "argument or in the config file."
        )
        raise

    try:
        host = args.host or config["host"]
    except KeyError:
        logging.error(
            "Missing server hostname or ip! Must be provided as a "
            "command line argument or in the config file."
        )
        raise
    peers = tuple(
        {"id": peer["id"], "host": peer["host"], "port": peer["mpc_port"]}
        for peer in config["peers"]
    )

    # FIXME remove after what is the node below has been better understood
    # NOTE leaving this temporarily as I would like to understand better why
    # when the NodeCommunicator is instantiated here it stalls. More precisely,
    # it will stall on processing the messages. It appears to block on the call
    # to read the queue:
    #
    #       msg = await node_msg_queue.get()
    #
    # the above is in ipc.py, in the method _process_node_messages
    #
    # from honeybadgermpc.ipc import NodeCommunicator2
    #
    # node_communicator = NodeCommunicator2(
    #    myid=myid, host=host, port=mpc_port, peers_config=peers, linger_timeout=2
    # )

    # db
    db_path = Path(f"{args.db_path}").resolve()
    if args.reset_db:
        # NOTE: for testing purposes, we reset (destroy) the db before each run
        plyvel.destroy_db(str(db_path))
    db = LevelDB(db_path)  # use leveldb

    http_port = args.http_port or config["http_port"] or default_http_port

    # contract context
    contract_path = Path(args.contract_path or config["contract"]["path"]).expanduser()
    contract_name = args.contract_name or config["contract"]["name"]
    contract_address = args.contract_address or config["contract"].get("address")
    if not contract_address:
        contract_address = get_contract_address(
            Path(hbmpc_home).joinpath("public/contract_address")
        )
    contract_lang = args.contract_lang or config["contract"].get(
        "lang", default_contract_lang
    )
    contract_context = {
        "filepath": contract_path,
        "name": contract_name,
        "address": contract_address,
        "lang": contract_lang,
    }

    ##########################################################################
    #
    # MPC program
    #
    # IDEA: will come from hbmpc aka ratel contract.
    # async def _prog(ctx, *, field_element):
    #    logging.info(f"[{ctx.myid}] Running MPC network")
    #    msg_share = ctx.Share(field_element)
    #    opened_value = await msg_share.open()
    #    opened_value_bytes = opened_value.value.to_bytes(32, "big")
    #    logging.info(f"opened_value in bytes: {opened_value_bytes}")
    #    msg = opened_value_bytes.decode().strip("\x00")
    #    return msg

    ##########################################################################

    asyncio.run(
        main(
            "sid",
            myid,
            host=host,
            mpc_port=mpc_port,
            peers=peers,
            # node_communicator=node_communicator,
            w3=w3,
            contract_context=contract_context,
            db=db,
            http_context={"host": host, "port": http_port},
            preprocessor_class=PreProcessor,
            httpserver_class=HTTPServer,
            mpcprogrunner_class=MPCProgRunner,
            # prog=_prog,
        )
    )