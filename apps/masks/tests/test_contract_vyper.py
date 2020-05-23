import pytest

n = 4
t = 1


@pytest.fixture
def mpc_contract_code():
    with open("apps/masks/contract.vy") as f:
        contract_code = f.read()
    return contract_code


@pytest.fixture
def mpc_contract(w3, get_contract, mpc_contract_code):
    contract = get_contract(mpc_contract_code, w3.eth.accounts[:4], t)
    # contract = get_contract(mpc_contract_code, n, t)
    return contract


def test_initial_state(w3, mpc_contract):
    # Check if the constructor of the contract is set up properly
    assert mpc_contract.n() == 4
    assert mpc_contract.t() == t
    for i in range(n):
        assert mpc_contract.servers(i) == w3.eth.accounts[i]
