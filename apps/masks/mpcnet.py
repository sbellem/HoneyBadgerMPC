import argparse
import asyncio
from pathlib import Path

import plyvel

import toml

from apps.masks.httpserver import HTTPServer
from apps.masks.preprocessor import PrePreprocessor
from apps.masks.server import Server
from apps.sharestore import LevelDB
from apps.utils import fetch_contract

from honeybadgermpc.config import NodeDetails
from honeybadgermpc.ipc import NodeCommunicator
from honeybadgermpc.preprocessing import PreProcessedElements

PARENT_DIR = Path(__file__).resolve().parent


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


class MPCNet:
    def __init__(
        self,
        servers,
        *,
        preprocessors=None,
        http_servers=None,
        ncs=None,
        sub_tasks=None,
    ):
        self.preprocessors = preprocessors
        self.http_servers = http_servers
        self.servers = servers
        self.sub_tasks = sub_tasks
        pp_elements = PreProcessedElements()
        pp_elements.clear_preprocessing()  # deletes sharedata/ if present

    @classmethod
    async def from_toml_config(cls, config_path):
        config = toml.load(config_path)

        # TODO extract resolving of relative path into utils
        context_path = Path(config_path).resolve().parent.joinpath(config["context"])
        config["eth"]["contract_path"] = context_path.joinpath(
            config["eth"]["contract_path"]
        )

        n = config["n"]
        base_config = {k: v for k, v in config.items() if k != "servers"}

        # For NodeCommunicator
        node_details = {
            i: NodeDetails(s["host"], s["dr_port"])
            for i, s in enumerate(config["servers"])
        }
        contract_context = _get_contract_context(config["eth"])
        w3 = _create_w3(config["eth"])
        contract = fetch_contract(w3, **contract_context)

        preprocessors = []
        http_servers = []
        servers = []
        ncs = []
        sub_tasks = []
        session_id = "sid"
        for i in range(n):
            server_config = {k: v for k, v in config["servers"][i].items()}
            server_config.update(base_config, session_id="sid")

            myid = server_config["id"]

            # NodeCommunicator / zeromq sockets
            nc = NodeCommunicator(node_details, i, 2)
            await nc._setup()
            ncs.append(nc)

            # NOTE: for testing purposes, we reset (destroy) the db before each run
            db_path = PARENT_DIR.joinpath(f"db{i}")
            plyvel.destroy_db(str(db_path))
            sharestore = LevelDB(db_path)  # use leveldb
            # sharestore = MemoryDB({}) # use a dict

            # from functools import partial
            from honeybadgermpc.utils.misc import _get_pubsub_channel

            # _subscribe_task, subscribe = subscribe_recv(nc.recv)
            # channel = partial(_get_send_recv, send=nc.send, subscribe=subscribe)
            sub_task, channel = _get_pubsub_channel(nc.send, nc.recv)
            sub_tasks.append(sub_task)
            # channel = None

            preprocessor = PrePreprocessor(
                session_id,
                myid,
                nc.send,
                nc.recv,
                w3,
                contract=contract,
                # contract_context=contract_context,
                sharestore=sharestore,
                channel=channel,
            )
            preprocessors.append(preprocessor)
            # preprocessors.append(None)
            http_server = HTTPServer(
                session_id,
                myid,
                http_host=server_config["host"],
                http_port=server_config["port"],
                sharestore=sharestore,
            )
            http_servers.append(http_server)
            server = Server(
                session_id,
                myid,
                nc.send,
                nc.recv,
                w3,
                contract=contract,
                # contract_context=contract_context,
                sharestore=sharestore,
                channel=channel,
            )
            servers.append(server)
            servers.append(None)
        return cls(
            servers,
            preprocessors=preprocessors,
            http_servers=http_servers,
            ncs=ncs,
            sub_tasks=sub_tasks,
        )

    async def start(self):
        for i, (preprocessor, http_server, server, sub_task) in enumerate(
            zip(self.preprocessors, self.http_servers, self.servers, self.sub_tasks)
        ):
            # for i, server in enumerate(self.servers):
            await preprocessor.start()
            await http_server.start()
            await server.join()
            await sub_task
            await self.ncs[i]._exit()


async def main(config_file):
    mpcnet = await MPCNet.from_toml_config(config_file)
    await mpcnet.start()


if __name__ == "__main__":
    # arg parsing
    default_config_path = PARENT_DIR.joinpath("mpcnet.toml")
    parser = argparse.ArgumentParser(description="MPC network.")
    parser.add_argument(
        "-c",
        "--config-file",
        default=str(default_config_path),
        help=f"Configuration file to use. Defaults to '{default_config_path}'.",
    )
    args = parser.parse_args()

    # Launch MPC network
    asyncio.run(main(args.config_file))
