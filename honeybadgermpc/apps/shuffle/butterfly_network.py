import random
from math import log
import asyncio
from honeybadgermpc.passive import (
    Field, Poly, generate_test_triples, write_polys, runProgramAsTasks
)


sharedatadir = "sharedata"
triplesprefix = f'{sharedatadir}/test_triples'
oneminusoneprefix = f'{sharedatadir}/test_one_minusone'
filecount = 0


async def multiplyShares(x, y, a, b, ab):
    D = (x - a).open()
    E = (y - b).open()
    xy = D*E + D*b + E*a + ab
    return await xy.open()


async def switch(ctx, a, b, sbit, x, y, xy):
    a, b, x, y, xy, sbit = map(ctx.Share, [a, b, x, y, xy, sbit])
    m = ctx.Share(await multiplyShares(sbit, (a - b), x, y, xy))
    n = 1 / Field(2)

    x = n * (a + b + m).v
    y = n * (a + b - m).v
    return x, y


async def writeToFile(shares, nodeid):
    global filecount
    with open(f"{sharedatadir}/butterfly_online_{filecount}_{nodeid}.share", "w") as f:
        for share in shares:
            print(share.value, file=f)
    filecount += 1


async def getTriplesAndSbit(tripleshares, randshares):
    a, b, ab = next(tripleshares).v, next(tripleshares).v, next(tripleshares).v
    sbit = next(randshares).v
    return a, b, ab, sbit


async def permutationNetwork(ctx, inputs, k, num, d, randshares, tripleshares, level=0):
    if level == int(log(k, 2)) - d:
        await writeToFile(inputs, ctx.myid)
        return None

    if level > int(log(k, 2)) - d:
        return None

    if num == 2:
        a, b, ab, sbit = await getTriplesAndSbit(tripleshares, randshares)
        return await switch(ctx, inputs[0], inputs[1], sbit, a, b, ab)

    layer1output1, layer1output2, result = [], [], []
    for i in range(int(num/2)):
        a, b, ab, sbit = await getTriplesAndSbit(tripleshares, randshares)
        t1, t2 = await switch(ctx, inputs[2*i], inputs[2*i + 1], sbit, a, b, ab)
        layer1output1.append(t1)
        layer1output2.append(t2)

    layer2outpu1 = await permutationNetwork(
        ctx, layer1output1, k, num/2, d, randshares, tripleshares, level+1
    )
    layer2output2 = await permutationNetwork(
        ctx, layer1output2, k, num/2, d, randshares, tripleshares, level+1
    )

    if layer2outpu1 is None or layer2output2 is None:
        return None

    for i in range(int(num/2)):
        a, b, ab, sbit = await getTriplesAndSbit(tripleshares, randshares)
        t1, t2 = await switch(ctx, layer2outpu1[i], layer2output2[i], sbit, a, b, ab)
        result.append(t1)
        result.append(t2)

    return result


async def butterflyNetwork(ctx, **kwargs):
    k, delta, inputs = kwargs['k'], kwargs['delta'], kwargs['inputs']
    tripleshares = ctx.read_shares(open(f'{triplesprefix}-{ctx.myid}.share'))
    randshares = ctx.read_shares(open(f'{oneminusoneprefix}-{ctx.myid}.share'))
    print(f"[{ctx.myid}] Running permutation network.")
    shuffled = await permutationNetwork(
        ctx, inputs, k, k, delta, iter(randshares), iter(tripleshares)
    )
    if shuffled is not None:
        shuffledShares = list(map(ctx.Share, shuffled))
        # openedValues = await asyncio.gather(*[s.open() for s in shuffledShares])
        # print(f"[{ctx.myid}]", openedValues)
        return shuffledShares
    return None


def generate_random_shares(prefix, k, N, t):
    polys = [Poly.random(t, random.randint(0, 1)*2 - 1) for _ in range(k)]
    write_polys(prefix, Field.modulus, N, t, polys)


def runButterlyNetworkInTasks():
    N, t, k, delta = 3, 2, 128, 6
    inputs = [Field(i) for i in range(1, k+1)]

    print('Generating random shares of triples in sharedata/')
    generate_test_triples(triplesprefix, 1000, N, t)
    print('Generating random shares of 1/-1 in sharedata/')
    generate_random_shares(oneminusoneprefix, k * int(log(k, 2)), N, t)

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try:
        loop.run_until_complete(
            runProgramAsTasks(butterflyNetwork, N, t, k=k, delta=delta, inputs=inputs)
        )
    finally:
        loop.close()


if __name__ == "__main__":
    import sys
    from honeybadgermpc.config import load_config
    from honeybadgermpc.ipc import NodeDetails, runProgramAsProcesses

    nodeid = int(sys.argv[1])
    configfile = sys.argv[2]
    config_dict = load_config(configfile)

    N = config_dict['N']
    t = config_dict['t']

    network_info = {
        int(peerid): NodeDetails(addrinfo.split(':')[0], int(addrinfo.split(':')[1]))
        for peerid, addrinfo in config_dict['peers'].items()
    }

    k, delta = 128, -999
    inputs = [Field(i) for i in range(1, k+1)]

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try:
        if nodeid == 0:
            print('Generating random shares of triples in sharedata/')
            generate_test_triples(triplesprefix, 1000, N, t)
            print('Generating random shares of 1/-1 in sharedata/')
            generate_random_shares(oneminusoneprefix, k * int(log(k, 2)), N, t)
        else:
            loop.run_until_complete(asyncio.sleep(2))

        loop.run_until_complete(
            runProgramAsProcesses(
                butterflyNetwork,
                network_info,
                N,
                t,
                nodeid,
                k=k,
                delta=delta,
                inputs=inputs
            )
        )
    finally:
        loop.close()
