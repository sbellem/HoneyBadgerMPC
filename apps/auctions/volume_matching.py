"""
Original code was written by Harjasleen Malvai
Volume Matching Auction : buy and sell orders are matched only on volume while price is determined by reference to some external market.

"""
import asyncio
import logging

from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.preprocessing import (
    PreProcessedElements as FakePreProcessedElements,
)
from honeybadgermpc.progs.fixedpoint import FixedPoint
from honeybadgermpc.progs.mixins.share_arithmetic import (
    BeaverMultiply,
    BeaverMultiplyArrays,
    MixinConstants,
)

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
}


async def compute_bids(ctx, balances, bids, price):
    """Compute all valid bids for each user. According to current market price, a bid becomes invalid
    if the user doesn't have enough balance to pay for this bid. We only keep valid bids and classify
    them into buy bids(volume > 0) and sell bids(volume < 0). Invalid bids will be discarded after the
    execution of this function.

    :param balances: {address -> {cointype -> balance}}
                     This is a dict where key is a string representing the address of user and value is
                     a dict representing balances of different cointype of this user. Cointype is a string,
                     which is be either 'eth' or 'erc20'. And balance is a FixedPoint number.
    :param bids: [[address, volume]]
                 This is a list of bids. Each bid is a list of two elements. The first element is the owner of
                 this bid, which is a string. The second element the volume of this bid, which is a FixedPoint
                 number. When volume is larger than zero, then this bid is a buy bid, which means the owner wants
                 to buy 'volume' units of tokens with 'volume * price' units of ETH. When volume is less than zero,
                 the bid is a sell bid, which means the owner wants to sell 'volume' units of tokens for 'volume * price'
                 units of ETH.
    :param price: FixedPoint
                  In volume matching, price is determined by reference to some external lit market. Price is how much
                  units of ETH have the same value as one unit of token.
    :return: buys, sells
             This function returns two lists of bids for buy and sell respectively. Since we have separated buy and
             sell bids, now every bid has volume larger than zero.
    """

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

        sell_vol = fp_zero - FixedPoint(ctx, await (is_sell * vol.share))
        buy_vol = FixedPoint(ctx, await (is_buy * vol.share))

        is_sell_vol_valid = one - await balances[addr]["erc20"].lt(
            sell_vol + used_balances[addr]["erc20"]
        )
        is_buy_vol_valid = one - await balances[addr]["eth"].lt(
            (await buy_vol.__mul__(price)) + used_balances[addr]["eth"]
        )

        fp_is_sell_vol_valid = FixedPoint(ctx, is_sell_vol_valid * 2 ** 32)
        fp_is_buy_vol_valid = FixedPoint(ctx, is_buy_vol_valid * 2 ** 32)

        sell_vol = await fp_is_sell_vol_valid.__mul__(sell_vol)
        buy_vol = await fp_is_buy_vol_valid.__mul__(buy_vol)

        sells.append((addr, sell_vol))
        buys.append((addr, buy_vol))

        used_balances[addr]["erc20"] = used_balances[addr]["erc20"] + sell_vol
        used_balances[addr]["eth"] = used_balances[addr]["eth"] + (
            await buy_vol.__mul__(price)
        )

    return buys, sells


async def volume_matching(ctx, buys, sells):
    """Given all valid buy and sell bids, this function run the volume matching algorithm,
    where buy and sell bids are matched only on volume with no price information considered.
    First we compute the amount to be matched, i.e., the smaller one between total buy volume
    and total sell volume. Then we match for buy bids and sell bids respectively.

    :param buys: list of valid buy bids
    :param sells: list of valid sell bids
    :return: matched_buys, matched_sells, res_buys, res_sells
             After matching, each bid is split into matched and rest part. This function returns
             four lists of bids, where matched_buys + res_buys = buys and
             matched_sells + res_sells = sells.
    """

    zero = ctx.Share(0)
    fp_zero = FixedPoint(ctx, zero)

    # compute total amount of volume to be matched
    matched_buys, matched_sells = [], []
    res_buys, res_sells = [], []

    total_sells = fp_zero
    for sell in sells:
        total_sells = total_sells + sell[1]

    total_buys = fp_zero
    for buy in buys:
        total_buys = total_buys + buy[1]

    f = await total_buys.lt(total_sells)
    fp_f = FixedPoint(ctx, f * 2 ** 32)
    matching_volume = (await (total_buys - total_sells).__mul__(fp_f)) + total_sells

    # match for sell bids
    rest_volume = matching_volume
    for i, sell in enumerate(sells):
        addr, sell_vol = sell

        z1 = await fp_zero.lt(rest_volume)
        fp_z1 = FixedPoint(ctx, z1 * 2 ** 32)
        z2 = await rest_volume.lt(sell_vol)
        fp_z2 = FixedPoint(ctx, z2 * 2 ** 32)

        matched_vol = await (
            (await (rest_volume - sell_vol).__mul__(fp_z2)) + sell_vol
        ).__mul__(fp_z1)
        rest_volume = rest_volume - matched_vol

        matched_sells.append([addr, matched_vol])
        res_sells.append([addr, sell_vol - matched_vol])

    # match for buy bids
    rest_volume = matching_volume
    for i, buy in enumerate(buys):
        addr, buy_vol = buy

        z1 = await fp_zero.lt(rest_volume)
        fp_z1 = FixedPoint(ctx, z1 * 2 ** 32)
        z2 = await rest_volume.lt(buy_vol)
        fp_z2 = FixedPoint(ctx, z2 * 2 ** 32)

        matched_vol = await (
            (await (rest_volume - buy_vol).__mul__(fp_z2)) + buy_vol
        ).__mul__(fp_z1)
        rest_volume = rest_volume - matched_vol

        matched_buys.append([addr, matched_vol])
        res_buys.append([addr, buy_vol - matched_vol])

    return matched_buys, matched_sells, res_buys, res_sells


async def compute_new_balances(balances, matched_buys, matched_sells, price):
    """
    Update balances of each user after matching

    :param balances: balances of users before matching
    :param matched_buys: list of matched buy bids
    :param matched_sells: list of matched sell bids
    :param price: external price
    :return: new balances after matching
    """

    for i, sell in enumerate(matched_sells):
        addr, vol = sell

        balances[addr]["erc20"] = balances[addr]["erc20"] - vol
        balances[addr]["eth"] = balances[addr]["eth"] + (await vol.__mul__(price))

    for i, buy in enumerate(matched_buys):
        addr, vol = buy

        balances[addr]["eth"] = balances[addr]["eth"] - (await vol.__mul__(price))
        balances[addr]["erc20"] = balances[addr]["erc20"] + vol

    return balances


def create_secret_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** 32) + ctx.preproc.get_zero(ctx))


def create_clear_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** 32))


async def prog(ctx):
    ctx.preproc = FakePreProcessedElements()

    price = create_clear_share(ctx, 3)

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

    _balances = [
        (await x["eth"].open(), await x["erc20"].open()) for x in balances.values()
    ]
    logging.info(f"balances initial {_balances}")

    bids = []
    bids.append(["0x125", create_secret_share(ctx, 5)])
    bids.append(["0x127", create_secret_share(ctx, 7)])
    bids.append(["0x128", create_secret_share(ctx, -3)])
    bids.append(["0x129", create_secret_share(ctx, -11)])
    buys, sells = await compute_bids(ctx, balances, bids, price)

    _buys = [await x[1].open() for x in buys]
    _sells = [await x[1].open() for x in sells]
    logging.info(f"buys initial: {_buys} and sells initial: {_sells}")

    matched_buys, matched_sells, res_buys, res_sells = await volume_matching(
        ctx, buys, sells
    )

    _matched_buys = [await x[1].open() for x in matched_buys]
    _matched_sells = [await x[1].open() for x in matched_sells]
    logging.info(f"buys matched: {_matched_buys} and sells matched: {_matched_sells}")

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