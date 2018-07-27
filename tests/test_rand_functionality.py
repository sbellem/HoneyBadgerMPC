import asyncio

import pytest


async def _test_sharesingle_ideal(sid='sid', N=4, f=1):
    from honeybadgermpc.rand_functionality import ShareSingle_IdealProtocol
    ShareSingle_IdealProtocol._instances = {} # Clear state
    parties = [ShareSingle_IdealProtocol(sid,N,f,i) for i in range(N)]

    # Now can await output from each ShareSingle protocol
    for i in range(N):
        await parties[i].output
        print(i, parties[i].output)


def test_sharesingle_ideal_og():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try:
        loop.run_until_complete(_test_sharesingle_ideal())
    finally:
        loop.close()


# NOTE same test as above (test_sharesingle_ideal_og), but uses pytest-asyncio plugin
# https://github.com/pytest-dev/pytest-asyncio
@pytest.mark.asyncio
async def test_sharesingle_ideal_with_pytest_asyncio(event_loop):
    event_loop.set_debug(True)
    await _test_sharesingle_ideal()
