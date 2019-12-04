"""
Volume Matching Auction : buy and sell orders are matched only on volume while price is determined by reference to some external market.

"""
import asyncio
import logging
import copy
from honeybadgermpc.preprocessing import (
    PreProcessedElements as FakePreProcessedElements,
)
from honeybadgermpc.progs.mixins.share_arithmetic import (
    MixinConstants,
    BeaverMultiply,
    BeaverMultiplyArrays,
)
from honeybadgermpc.progs.fixedpoint import FixedPoint
from honeybadgermpc.mpc import TaskProgramRunner

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
}


async def compute_bids(ctx, balances, bids, price):
    one = ctx.Share(1)
    zero = ctx.Share(0)
    fp_zero = FixedPoint(ctx, zero)

    used_balances = {}
    for key in balances.keys():
        used_balances[key] = {
            "eth": create_clear_share(ctx, 0),
            "erc20": create_clear_share(ctx, 0),
        }

    buys = []
    sells = []

    for i, bid in enumerate(bids):
        addr, vol = bid

        is_sell = await vol.ltz()
        is_buy = one - is_sell

        sell_vol = fp_zero.sub(FixedPoint(ctx, await (is_sell * vol.share)))
        buy_vol = FixedPoint(ctx, await (is_buy * vol.share))

        is_sell_vol_valid = one - await balances[addr]["erc20"].lt(
            sell_vol.add(used_balances[addr]["erc20"])
        )
        is_buy_vol_valid = one - await balances[addr]["eth"].lt(
            (await buy_vol.mul(price)).add(used_balances[addr]["eth"])
        )

        fp_is_sell_vol_valid = FixedPoint(ctx, is_sell_vol_valid * 2 ** 32)
        fp_is_buy_vol_valid = FixedPoint(ctx, is_buy_vol_valid * 2 ** 32)

        sell_vol = await fp_is_sell_vol_valid.mul(sell_vol)
        buy_vol = await fp_is_buy_vol_valid.mul(buy_vol)

        sells.append((addr, sell_vol))
        buys.append((addr, buy_vol))

        used_balances[addr]["erc20"] = used_balances[addr]["erc20"].add(sell_vol)
        used_balances[addr]["eth"] = used_balances[addr]["eth"].add(
            await buy_vol.mul(price)
        )

    return buys, sells


async def volume_matching(ctx, bids):
    zero = ctx.Share(0)
    fp_zero = FixedPoint(ctx, zero)

    (buys, sells) = bids
    matched_buys, matched_sells = [], []
    res_buys, res_sells = [], []

    total_sells = fp_zero
    for sell in sells:
        total_sells = total_sells.add(sell[1])

    total_buys = fp_zero
    for buy in buys:
        total_buys = total_buys.add(buy[1])

    f = await total_buys.lt(total_sells)
    fp_f = FixedPoint(ctx, f * 2 ** 32)
    T = (await total_buys.sub(total_sells).mul(fp_f)).add(total_sells)

    L = T
    for i, sell in enumerate(sells):
        addr, sell_vol = sell

        z1 = await fp_zero.lt(L)
        fp_z1 = FixedPoint(ctx, z1 * 2 ** 32)
        z2 = await L.lt(sell_vol)
        fp_z2 = FixedPoint(ctx, z2 * 2 ** 32)

        matched_vol = await (await L.sub(sell_vol).mul(fp_z2)).add(sell_vol).mul(fp_z1)
        L = L.sub(matched_vol)

        matched_sells.append([addr, matched_vol])
        res_sells.append([addr, sell_vol.sub(matched_vol)])

    L = T
    for i, buy in enumerate(buys):
        addr, buy_vol = buy

        z1 = await fp_zero.lt(L)
        fp_z1 = FixedPoint(ctx, z1 * 2 ** 32)
        z2 = await L.lt(buy_vol)
        fp_z2 = FixedPoint(ctx, z2 * 2 ** 32)

        matched_vol = await (await (L.sub(buy_vol)).mul(fp_z2)).add(buy_vol).mul(fp_z1)
        L = L.sub(matched_vol)

        matched_buys.append([addr, matched_vol])
        res_buys.append([addr, buy_vol.sub(matched_vol)])

    return matched_buys, matched_sells, res_buys, res_sells


async def compute_new_balances(balances, matched_buys, matched_sells, price):
    for i, sell in enumerate(matched_sells):
        addr, vol = sell

        balances[addr]["erc20"] = balances[addr]["erc20"].sub(vol)
        balances[addr]["eth"] = balances[addr]["eth"].add(await vol.mul(price))

    for i, buy in enumerate(matched_buys):
        addr, vol = buy

        balances[addr]["eth"] = balances[addr]["eth"].sub(await vol.mul(price))
        balances[addr]["erc20"] = balances[addr]["erc20"].add(vol)

    return balances


def create_secret_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** 32) + ctx.preproc.get_zero(ctx))


def create_clear_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** 32))


async def prog(ctx):
    ctx.preproc = FakePreProcessedElements()

    price = create_clear_share(ctx, 3)
    # price = create_clear_share(ctx, 2)

    balances = {}
    # balances["0x125"] = {
    #     "eth": create_clear_share(ctx, 15),
    #     "erc20": create_clear_share(ctx, 1),
    # }
    # balances["0x127"] = {
    #     "eth": create_clear_share(ctx, 18),
    #     "erc20": create_clear_share(ctx, 0),
    # }
    # balances["0x128"] = {
    #     "eth": create_clear_share(ctx, 2),
    #     "erc20": create_clear_share(ctx, 3),
    # }
    # balances["0x129"] = {
    #     "eth": create_clear_share(ctx, 0),
    #     "erc20": create_clear_share(ctx, 15),
    # }

    balances["0x120"] = {
        "eth": create_clear_share(ctx, 78),
        "erc20": create_clear_share(ctx, 15),
    }

    balances["0x121"] = {
        "eth": create_clear_share(ctx, 42),
        "erc20": create_clear_share(ctx, 11),
    }

    _balances = [
        (await x["eth"].open(), await x["erc20"].open()) for x in balances.values()
    ]
    logging.info(f"balances initial {_balances}")

    bids = []
    # bids.append(["0x125", create_secret_share(ctx, 5)])
    # bids.append(["0x127", create_secret_share(ctx, 7)])
    # bids.append(["0x128", create_secret_share(ctx, -3)])
    # bids.append(["0x129", create_secret_share(ctx, -11)])
    bids.append(["0x121", create_secret_share(ctx, 1)])
    bids.append(["0x120", create_secret_share(ctx, -5)])
    bids.append(["0x121", create_secret_share(ctx, -9)])

    buys, sells = await compute_bids(ctx, balances, bids, price)

    _buys = [await x[1].open() for x in buys]
    _sells = [await x[1].open() for x in sells]
    logging.info(f"buys initial: {_buys} and sells initial: {_sells}")

    matched_buys, matched_sells, res_buys, res_sells = await volume_matching(
        ctx, (buys, sells)
    )

    _matched_buys = [await x[1].open() for x in matched_buys]
    _matched_sells = [await x[1].open() for x in matched_sells]
    logging.info(f"buys matched: {_matched_buys} and sells matched: {_sells}")

    _res_buys = [await x[1].open() for x in res_buys]
    _res_sells = [await x[1].open() for x in res_sells]
    logging.info(f"buys rest: {_res_buys} and sells rest: {_res_sells}")

    _balances = [
        (await x["eth"].open(), await x["erc20"].open()) for x in balances.values()
    ]
    logging.info(f"balances rest {_balances}")

    final_balances = await compute_new_balances(
        balances, matched_buys, matched_sells, price
    )

    _final_balances = [
        (await x["eth"].open(), await x["erc20"].open())
        for x in final_balances.values()
    ]
    logging.info(f"balances rest {_final_balances}")

    logging.info(f"[{ctx.myid}] done")


async def dark_pewl():
    n, t = 4, 1
    k = 10000
    pp = FakePreProcessedElements()
    pp.generate_zeros(k, n, t)
    pp.generate_triples(k, n, t)
    pp.generate_bits(k, n, t)
    program_runner = TaskProgramRunner(n, t, config)
    program_runner.add(prog)
    results = await program_runner.join()
    return results


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dark_pewl())


if __name__ == "__main__":
    main()
