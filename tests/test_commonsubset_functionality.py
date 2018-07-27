import asyncio


async def _test_acs_ideal(sid='sid',N=4,f=1):
    from honeybadgermpc.commonsubset_functionality import CommonSubset_IdealProtocol
    ACS = CommonSubset_IdealProtocol(N, f)
    parties = [ACS(sid,i) for i in range(N)]

    # Provide input
    # for i in range(N-1): # if set to N-1, will still succeed, but N-2 fails
    for i in range(N):
        parties[i].input.set_result('hi'+str(i))

    # Now can await output from each ACS protocol
    for i in range(N):
        await parties[i].output
        print(i, parties[i].output)


def test_acs_ideal():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try: loop.run_until_complete(_test_acs_ideal())
    finally: loop.close()
