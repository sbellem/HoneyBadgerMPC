import asyncio
import logging

from web3.contract import ConciseContract

from apps.toolkit.client import Client as _Client
from apps.toolkit.utils import wait_for_receipt

from honeybadgermpc.utils.misc import print_exception_callback


class Client(_Client):
    def _fake_bids(self):
        bids = [5, 7, -3, -11]
        return bids

    async def _run(self):
        contract_concise = ConciseContract(self.contract)
        # Client sends several batches of messages then quits
        for epoch in range(self.number_of_epoch):
            logging.info(f"[Client] Starting Epoch {epoch}")
            receipts = []
            for i in range(self.msg_batch_size):
                m = f"Hello! (Client Epoch: {epoch}:{i})"
                task = asyncio.ensure_future(self.send_message(m))
                task.add_done_callback(print_exception_callback)
                receipts.append(task)
            receipts = await asyncio.gather(*receipts)

            while True:  # wait before sending next
                if contract_concise.outputs_ready() > epoch:
                    break
                await asyncio.sleep(5)

    async def send_message(self, m, *, sender_addr=None):
        logging.info("sending message ...")
        # Submit a message to be unmasked
        contract_concise = ConciseContract(self.contract)

        if sender_addr is None:
            sender_addr = self.w3.eth.accounts[0]

        # Step 1. Wait until there is input available, and enough triples
        while True:
            inputmasks_available = contract_concise.inputmasks_available()
            logging.info(f"inputmasks_available: {inputmasks_available}")
            if inputmasks_available >= 1:
                break
            await asyncio.sleep(5)

        # Step 2. Reserve the input mask
        logging.info("trying to reserve an input mask ...")
        tx_hash = self.contract.functions.reserve_inputmask().transact(
            {"from": self.w3.eth.accounts[0]}
        )
        tx_receipt = await wait_for_receipt(self.w3, tx_hash)
        rich_logs = self.contract.events.InputMaskClaimed().processReceipt(tx_receipt)
        if rich_logs:
            inputmask_idx = rich_logs[0]["args"]["inputmask_idx"]
        else:
            raise ValueError
        logging.info(f"input mask (id: {inputmask_idx}) reserved")
        logging.info(f"tx receipt hash is: {tx_receipt['transactionHash'].hex()}")

        # Step 3. Fetch the input mask from the servers
        logging.info("query the MPC servers for their share of the input mask ...")
        inputmask = await self._get_inputmask(inputmask_idx)
        logging.info("input mask has been privately reconstructed")
        message = int.from_bytes(m.encode(), "big")
        logging.info("masking the message ...")
        masked_message = message + inputmask
        masked_message_bytes = self.w3.toBytes(hexstr=hex(masked_message.value))
        masked_message_bytes = masked_message_bytes.rjust(32, b"\x00")

        # Step 4. Publish the masked input
        logging.info("publish the masked message to the public contract ...")
        tx_hash = self.contract.functions.submit_message(
            inputmask_idx, masked_message_bytes
        ).transact({"from": self.w3.eth.accounts[0]})
        tx_receipt = await wait_for_receipt(self.w3, tx_hash)
        rich_logs = self.contract.events.MessageSubmitted().processReceipt(tx_receipt)
        if rich_logs:
            idx = rich_logs[0]["args"]["idx"]
            inputmask_idx = rich_logs[0]["args"]["inputmask_idx"]
            masked_input = rich_logs[0]["args"]["masked_input"]
        else:
            raise ValueError
        logging.info(
            f"masked message {masked_input} has been published to the "
            f"public contract at address {self.contract.address} "
            f"and is queued at index {idx}"
        )
        logging.info(f"tx receipt hash is: {tx_receipt['transactionHash'].hex()}")


async def main(config_file):
    client = Client.from_toml_config(config_file)
    await client.join()


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    PARENT_DIR = Path(__file__).resolve().parent
    default_config_path = PARENT_DIR.joinpath("client.toml")
    # default_client_home = Path.home().joinpath(".hbmpc")
    # default_contract_address_path = default_client_home.joinpath(
    #    "public/contract_address"
    # )
    parser = argparse.ArgumentParser(description="MPC client.")
    parser.add_argument(
        "-c",
        "--config-file",
        default=str(default_config_path),
        help=f"Configuration file to use. Defaults to '{default_config_path}'.",
    )
    args = parser.parse_args()

    # Launch a client
    asyncio.run(main(Path(args.config_file).expanduser()))
