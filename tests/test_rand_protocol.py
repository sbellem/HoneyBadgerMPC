import asyncio


async def _test_naive(sid='sid',N=4,f=1):
    from honeybadgermpc.secretshare_functionality import SecretShare_IdealProtocol
    from honeybadgermpc.rand_protocol import NaiveShareRandomProtocol
    SecretShare = SecretShare_IdealProtocol(N,f)
    rands = []
    # for i in range(N): # If set to N-1 (simulate crashed party, it gets stuck)
    for i in range(N):
        # Optionally fail to active the last one of them
        rands.append(NaiveShareRandomProtocol(N,f,sid,i,SecretShare,None))

    print('_test_naive: awaiting results...')
    results = await asyncio.gather(*(rand.output for rand in rands))
    print('_test_naive:', results)
      

def test_naive():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try: loop.run_until_complete(_test_naive())
    finally: loop.close()


async def _test_rand(sid='sid',N=4,f=1):
    from honeybadgermpc.commonsubset_functionality import CommonSubset_IdealProtocol
    from honeybadgermpc.secretshare_functionality import SecretShare_IdealProtocol
    from honeybadgermpc.rand_protocol import ShareSingle_Protocol
    SecretShare = SecretShare_IdealProtocol(N,f)
    CommonSubset = CommonSubset_IdealProtocol(N,f)

    rands = []
    # for i in range(N): # If set to N-1 (simulate crashed party, it gets stuck)
    for i in range(N-1):
        # Optionally fail to active the last one of them
        rands.append(ShareSingle_Protocol(N,f,sid,i,SecretShare,CommonSubset))

    print('_test_rand: awaiting results...')
    results = await asyncio.gather(*(rand.output for rand in rands))
    print('_test_rand:', results)
    for a in SecretShare._instances.values():
        a._task.cancel()
     

def test_rand():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try: loop.run_until_complete(_test_rand())
    finally: loop.close()
