import argparse
import asyncio
from pathlib import Path

import toml

from apps.masks.server import Server

from honeybadgermpc.config import NodeDetails
from honeybadgermpc.ipc import NodeCommunicator
from honeybadgermpc.preprocessing import PreProcessedElements

PARENT_DIR = Path(__file__).resolve().parent


class MPCNet:
    def __init__(self, servers, ncs=None):
        self.servers = servers
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

        servers = []
        ncs = []
        for i in range(n):
            server_config = {k: v for k, v in config["servers"][i].items()}
            server_config.update(base_config, session_id="sid")

            # NodeCommunicator / zeromq sockets
            nc = NodeCommunicator(node_details, i, 2)
            await nc._setup()
            ncs.append(nc)

            server = Server.from_dict_config(server_config, send=nc.send, recv=nc.recv)
            servers.append(server)
        return cls(servers, ncs=ncs)

    async def start(self):
        for i, server in enumerate(self.servers):
            await server.join()
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
