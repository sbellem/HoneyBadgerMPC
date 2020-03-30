from pathlib import Path

from web3 import HTTPProvider, Web3

from apps.masks.config import CONTRACT_ADDRESS_FILEPATH
from apps.utils import create_and_deploy_contract

PARENT_DIR = Path(__file__).resolve().parent


def deploy(
    *, contract_name, contract_filepath, n=4, t=1, eth_rpc_hostname, eth_rpc_port
):
    w3_endpoint_uri = f"http://{eth_rpc_hostname}:{eth_rpc_port}"
    w3 = Web3(HTTPProvider(w3_endpoint_uri))
    deployer = w3.eth.accounts[49]
    mpc_addrs = w3.eth.accounts[:n]
    contract_address, abi = create_and_deploy_contract(
        w3,
        deployer=deployer,
        contract_name=contract_name,
        contract_filepath=contract_filepath,
        args=(mpc_addrs, t),
    )
    return contract_address


if __name__ == "__main__":
    contract_name = "MpcCoordinator"
    contract_filename = "contract.sol"
    contract_filepath = PARENT_DIR.joinpath(contract_filename)
    eth_rpc_hostname = "blockchain"
    eth_rpc_port = 8545
    n, t = 4, 1
    contract_address = deploy(
        contract_name=contract_name,
        contract_filepath=contract_filepath,
        t=1,
        eth_rpc_hostname=eth_rpc_hostname,
        eth_rpc_port=eth_rpc_port,
    )

    with open(CONTRACT_ADDRESS_FILEPATH, "w") as f:
        f.write(contract_address)
