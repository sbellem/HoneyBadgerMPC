import asyncio
import os

from honeybadgermpc.passive import PassiveMpc, Poly, Field

# XXX wonder whether these should part of tests as helpers
from honeybadgermpc.passive import (
    write_polys,
    generate_test_triples,
    generate_test_zeros,
    generate_test_randoms,
)
from honeybadgermpc.router import  simple_router
# XXX end of wonder


TESTS_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
SHAREDATA_DIR_PATH = os.path.join(TESTS_DIR_PATH, 'sharedata')


# Create a fake network with N instances of the program
async def runProgramInNetwork(program, N, t):
    loop = asyncio.get_event_loop()
    sends,recvs = simple_router(N)

    tasks = []
    bgtasks = []
    for i in range(N):
        context = PassiveMpc('sid', N, t, i, sends[i], recvs[i], program)
        tasks.append(loop.create_task(context._run()))

    await asyncio.gather(*tasks)


async def _test_prog1(context):

    filename = os.path.join(SHAREDATA_DIR_PATH, f'test_zeros-{context.myid}.share')
    zeros = context.read_shares(open(filename))

    filename = 'sharedata/test_triples-%d.share' % (context.myid,)
    filename = os.path.join(SHAREDATA_DIR_PATH, f'test_triples-{context.myid}.share')
    triples = context.read_shares(open(filename))

    # Example of Beaver multiplication
    x = zeros[0] + context.Share(10)
    y = zeros[1] + context.Share(15)

    a,b,ab = triples[:3]
    # assert await a.open() * await b.open() == await ab.open()

    D = await (x - a).open()
    E = await (y - b).open()

    # This is a random share of x*y
    xy = context.Share(D*E) + D*b + E*a + ab

    X,Y,XY = await x.open(), await y.open(), await xy.open()
    assert X * Y == XY
    
    print("[%d] Finished" % (context.myid,), X,Y,XY)


# Read zeros from file, open them
async def _test_prog2(context):

    filename = os.path.join(SHAREDATA_DIR_PATH, f'test_zeros-{context.myid}.share')
    shares = context.read_shares(open(filename))

    print('[%d] read %d shares' % (context.myid, len(shares)))

    for share in shares[:100]:
        s = await share.open()
        assert s == 0
    print('[%d] Finished' % (context.myid,))
    

# Run some test cases
def test():
    print('Generating random shares of zero in sharedata/')
    zeros_filepath = os.path.join(SHAREDATA_DIR_PATH, 'test_zeros')
    generate_test_zeros(zeros_filepath, 1000, 3, 2)
    print('Generating random shares of triples in sharedata/')
    triples_filepath = os.path.join(SHAREDATA_DIR_PATH, 'test_triples')
    generate_test_triples('triples_filepath', 1000, 3, 2)
    
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try:
        loop.run_until_complete(runProgramInNetwork(_test_prog1, 3, 2))
        loop.run_until_complete(runProgramInNetwork(_test_prog2, 3, 2))
    finally:
        loop.close()
