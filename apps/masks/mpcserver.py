"""MPC server code.

**Questions**
How are crash faults supposed to be handled? Currently, if a server comes
back it will be in an inconsistent state. For instance, its input masks list
will be empty, likely differing from the contract.

Also, the epoch count will be reset to 0 if a server restarts. Not clear
what this may cause, besides the server attempting to unmask messages that
have already been unmasked ...
"""
from apps.utils import fetch_contract

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
        sharestore=None,
        preprocessor_class=None,
        httpserver_class=None,
        mpcprogrunner_class=None,
        http_context,
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
        self.subscribe_task, self.channel = _get_pubsub_channel(send, recv)
        self.get_send_recv = self.channel
        self.sharestore = sharestore
        self.preprocessor_class = preprocessor_class
        self.httpserver_class = httpserver_class
        self.http_context = http_context
        self.mpcprogrunner_class = mpcprogrunner_class
        self._init_tasks()

    def _init_tasks(self):
        self.preprocessor = self.preprocessor_class(
            self.sid,
            self.myid,
            self.w3,
            contract=self.contract,
            sharestore=self.sharestore,
            channel=self.channel,
        )
        self.http_server = self.httpserver_class(
            self.sid,
            self.myid,
            http_host=self.http_context["host"],
            http_port=self.http_context["port"],
            sharestore=self.sharestore,
        )
        self.mpc_prog_runner = self.mpcprogrunner_class(
            self.sid,
            self.myid,
            self.w3,
            contract=self.contract,
            sharestore=self.sharestore,
            channel=self.channel,
        )

    async def start(self):
        await self.preprocessor.start()
        await self.http_server.start()
        await self.mpc_prog_runner.start()
        await self.subscribe_task


if __name__ == "__main__":
    # import asyncio
    import argparse
    from pathlib import Path

    PARENT_DIR = Path(__file__).resolve().parent
    # arg parsing
    default_config_path = PARENT_DIR.joinpath("mpcserver.toml")
    parser = argparse.ArgumentParser(description="MPC server configuration.")
    parser.add_argument(
        "-c",
        "--config-file",
        default=str(default_config_path),
        help=f"Configuration file to use. Defaults to '{default_config_path}'.",
    )
    args = parser.parse_args()

    # Launch MPC server
    # asyncio.run(main(args.config_file))
