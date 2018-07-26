from commonsubset_functionality import CommonSubset_IdealProtocol
"""
Implementation of Asynchronous Common Subset using an EVM blockchain
"""

import web3
import asyncio

# TODO: compile solidity file commonsubset.sol

def CommonSubsetProtocol(w3, contract, N, f):
    
    class CommonSubset_BlockchainProtocol(object):
        def __init__(self, sid, myid):
            self.sid = sid
            self.myid = myid
            # Accept one value as input (a uint256)
            self.input = asyncio.Future()
            # Output is a vecture of uint256
            self.output = asyncio.Future()

            self._task = asyncio.ensure_future(self._run())
            # TODO: use web3 to look up the contract using `sid` as the key
            # self._contract = ...

        async def _run(self):
            v = await self.input
            print('[%d] Invoking CommonSubset contract.input(%d)' % (self.myid,v))
            contract.input(v, transact={'from':w3.eth.accounts[self.myid]})

            # TODO: alternative to polling?
            while True:
                print("[%d] deadline:%d, blockno:%d"%(self.myid,contract.deadline(),w3.eth.blockNumber))
                if contract.isComplete(): break
                await asyncio.sleep(3)
            count = contract.count()
            outs = [contract.values(i) for i in range(N)]
            print('CommonSubset output ready', contract.count(), outs)
            self.output.set_result(outs)

    return CommonSubset_BlockchainProtocol

def handle_event(event):
    # print('event:',event)
    # and whatever
    pass

from ethereum.tools._solidity import compile_file, compile_code as compile_source
from web3.contract import ConciseContract

async def main_loop(w3):
    compiled_sol = compile_source(open('commonsubset.sol').read()) # Compiled source code
    contract_interface = compiled_sol['<stdin>:CommonSubset']
    contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    tx_hash = contract.constructor(w3.eth.accounts[:7],2).transact({'from':w3.eth.accounts[0], 'gas':820000})
    
    #tx_hash = contract.deploy(transaction={'from': w3.eth.accounts[0], 'gas': 410000})

    # Get tx receipt to get contract address
    while True:
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        if tx_receipt is not None: break
        await asyncio.sleep(1)
    contract_address = tx_receipt['contractAddress']

    # Contract instance in concise mode
    abi = contract_interface['abi']
    contract_instance = w3.eth.contract(address=contract_address, abi=abi,ContractFactoryClass=ConciseContract)

    print(tx_receipt)
    print('N',contract_instance.N())
    print('f',contract_instance.f())
    print('players(0)',contract_instance.players(0))
    print('players(6)',contract_instance.players(6))
    #print('players(7)',contract_instance.players(7))

    CommonSubset = CommonSubsetProtocol(w3, contract_instance,7,2)
    prots = [CommonSubset('sid',i) for i in range(5)]
    outputs = [prot.output for prot in prots]
    for i,prot in enumerate(prots):
        prot.input.set_result(i+17)
    await asyncio.gather(*outputs)
    for prot in prots: prot._task.cancel()
    print('done')
    
async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        await asyncio.sleep(poll_interval)

from contextlib import contextmanager
import subprocess
import sys
    
@contextmanager
def run_and_terminate_process(*args, **kwargs):
    try:
        p = subprocess.Popen(*args, **kwargs)
        yield p
    finally:
        print("Killing ethereumjs-testrpc", p.pid)
        p.terminate() # send sigterm, or ...
        p.kill()      # send sigkill
        p.wait()
        print('done')
            
def run_eth():
    from web3 import Web3, HTTPProvider
    w3 = Web3(HTTPProvider()) # Connect to localhost:8545
    block_filter = w3.eth.filter('latest')
    tx_filter = w3.eth.filter('pending')
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        print('entering loop')
        loop.run_until_complete(
            asyncio.gather(
                main_loop(w3),
                ))
    finally:
        print('closing')
        loop.close()

def main():
    import time
    #with run_and_terminate_process('testrpc -a 50 2>&1 | tee -a acctKeys.json', shell=True, stdout=sys.stdout, stderr=sys.stderr) as proc:
    cmd = "testrpc -a 50 -b 1 > acctKeys.json 2>&1"
    print("Running", cmd)
    with run_and_terminate_process(cmd, shell=True) as proc:
        time.sleep(2)
        run_eth()

if __name__ == '__main__':
    # Launch an ethereum test chain

        main()
