import asyncio
import logging
from pathlib import Path

from web3 import HTTPProvider, Web3
from web3.contract import ConciseContract

from apps.masks.client import Client
from apps.masks.config import CONTRACT_ADDRESS_FILEPATH
from apps.masks.server import Server
from apps.utils import get_contract_abi, get_contract_address

from honeybadgermpc.preprocessing import PreProcessedElements
from honeybadgermpc.router import SimpleRouter


async def main_loop(w3, *, n, contract_context):
    pp_elements = PreProcessedElements()
    # deletes sharedata/ if present
    pp_elements.clear_preprocessing()

    # Contract instance in concise mode
    abi = get_contract_abi(
        contract_name=contract_context["name"],
        contract_filepath=contract_context["filepath"],
    )
    contract = w3.eth.contract(address=contract_context["address"], abi=abi)
    contract_concise = ConciseContract(contract)  # Call read only methods to check
    n = contract_concise.n()  # Call read only methods to check

    # Step 2: Create the servers
    router = SimpleRouter(n)
    sends, recvs = router.sends, router.recvs
    servers = [
        Server("sid", i, sends[i], recvs[i], w3, contract_context=contract_context)
        for i in range(n)
    ]

    # Step 3. Create the client
    # TODO communicate with server instead of fetching from list of servers
    async def req_mask(i, idx):
        # client requests input mask {idx} from server {i}
        return servers[i]._inputmasks[idx]

    client = Client("sid", "client", w3, req_mask, contract_context=contract_context)

    # Step 4. Wait for conclusion
    for i, server in enumerate(servers):
        await server.join()
    await client.join()


def run_eth(
    *, contract_context, n=4, t=1, eth_rpc_hostname, eth_rpc_port,
):
    w3_endpoint_uri = f"http://{eth_rpc_hostname}:{eth_rpc_port}"
    w3 = Web3(HTTPProvider(w3_endpoint_uri))
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    try:
        logging.info("entering loop")
        loop.run_until_complete(
            asyncio.gather(main_loop(w3, n=n, contract_context=contract_context))
        )
    finally:
        logging.info("closing")
        loop.close()


def main(
    *, contract_context, n=4, t=1, eth_rpc_hostname="localhost", eth_rpc_port=8545,
):
    run_eth(
        contract_context=contract_context,
        n=n,
        t=t,
        eth_rpc_hostname=eth_rpc_hostname,
        eth_rpc_port=eth_rpc_port,
    )


if __name__ == "__main__":
    # Launch an ethereum test chain
    contract_name = "MpcCoordinator"
    contract_filename = "contract.sol"
    contract_filepath = Path(__file__).resolve().parent.joinpath(contract_filename)
    contract_address = get_contract_address(CONTRACT_ADDRESS_FILEPATH)
    contract_context = {
        "address": contract_address,
        "filepath": contract_filepath,
        "name": contract_name,
    }

    eth_rpc_hostname = "blockchain"
    eth_rpc_port = 8545
    n, t = 4, 1
    main(
        contract_context=contract_context,
        n=4,
        t=1,
        eth_rpc_hostname=eth_rpc_hostname,
        eth_rpc_port=eth_rpc_port,
    )
