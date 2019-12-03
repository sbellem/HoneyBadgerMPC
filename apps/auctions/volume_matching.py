"""
Volume Matching Auction : buy and sell orders are matched only on volume while price is determined by reference to some external market.

"""
import asyncio
import logging
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
    fp_one = FixedPoint(ctx, one * 2 ** 32)
    fp_zero = FixedPoint(ctx, zero)
    buys = []
    sells = []

    for i, bid in enumerate(bids):
        addr, vol = bid

        is_sell = await vol.ltz()
        is_buy = one - is_sell

        sell_vol = FixedPoint(ctx, await (is_sell * vol.share))
        buy_vol = FixedPoint(ctx, await (is_buy * vol.share))

        is_sell_vol_valid = one - await balances[addr]["erc20"].lt(sell_vol)
        is_buy_vol_valid = one - await balances[addr]["eth"].lt(
            await buy_vol.mul(price)
        )

        fp_is_sell_vol_valid = FixedPoint(ctx, is_sell_vol_valid * 2 ** 32)
        fp_is_buy_vol_valid = FixedPoint(ctx, is_buy_vol_valid * 2 ** 32)

        sells.append((addr, fp_zero.sub(await fp_is_sell_vol_valid.mul(sell_vol))))
        buys.append((addr, await fp_is_buy_vol_valid.mul(buy_vol)))

    return buys, sells


async def volume_matching(ctx, bids):
    one = ctx.Share(1)
    zero = ctx.Share(0)
    fp_one = FixedPoint(ctx, one * 2 ** 32)
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

        matched_vol = (await L.sub(sell_vol).mul(fp_z2)).add(await sell_vol.mul(fp_z1))
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

        matched_vol = (await (L.sub(buy_vol)).mul(fp_z2)).add(await buy_vol.mul(fp_z1))
        L = L.sub(matched_vol)

        matched_buys.append([addr, matched_vol])
        res_buys.append([addr, buy_vol.sub(matched_vol)])

    return matched_buys, matched_sells, res_buys, res_sells


async def compute_new_balances(ctx, balances, matched_buys, matched_sells, price):
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


async def dot_product(ctx, xs, ys):
    return sum((x * y for x, y in zip(xs, ys)), ctx.Share(0))


async def prog(ctx):
    ctx.preproc = FakePreProcessedElements()
    bids = []
    bids.append(["0x125", create_secret_share(ctx, 5)])
    bids.append(["0x127", create_secret_share(ctx, 7)])
    bids.append(["0x128", create_secret_share(ctx, -3)])
    bids.append(["0x129", create_secret_share(ctx, -11)])

    balances = {}
    balances["0x125"] = {
        "eth": create_clear_share(ctx, 15),
        "erc20": create_clear_share(ctx, 1),
    }
    balances["0x127"] = {
        "eth": create_clear_share(ctx, 18),
        "erc20": create_clear_share(ctx, 0),
    }
    balances["0x128"] = {
        "eth": create_clear_share(ctx, 2),
        "erc20": create_clear_share(ctx, 3),
    }
    balances["0x129"] = {
        "eth": create_clear_share(ctx, 0),
        "erc20": create_clear_share(ctx, 15),
    }

    bal = [(await x["eth"].open(), await x["erc20"].open()) for x in balances.values()]
    print(f"balances initial {bal}")

    price = create_clear_share(ctx, 3)
    buys, sells = await compute_bids(ctx, balances, bids, price)

    _buys = [await x[1].open() for x in buys]
    _sells = [await x[1].open() for x in sells]
    print(f"buys initial: {_buys} and sells initial: {_sells}")

    logging.info(f"[{ctx.myid}] Running prog 1.")
    matched_buys, matched_sells, res_buys, res_sells = await volume_matching(
        ctx, (buys, sells)
    )

    _buys = [await x[1].open() for x in matched_buys]
    _sells = [await x[1].open() for x in matched_sells]
    print(f"buys matched: {_buys} and sells matched: {_sells}")

    _buys = [await x[1].open() for x in res_buys]
    _sells = [await x[1].open() for x in res_sells]
    print(f"buys rest: {_buys} and sells rest: {_sells}")

    balances = await compute_new_balances(
        ctx, balances, matched_buys, matched_sells, price
    )

    bal = [(await x["eth"].open(), await x["erc20"].open()) for x in balances.values()]
    print(f"balances rest {bal}")

    logging.info(f"[{ctx.myid}] done")


async def dark_pewl():
    n, t = 4, 1
    pp = FakePreProcessedElements()
    pp.generate_zeros(10000, n, t)
    pp.generate_triples(10000, n, t)
    pp.generate_bits(10000, n, t)
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
