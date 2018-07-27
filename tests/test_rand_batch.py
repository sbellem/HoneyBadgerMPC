import asyncio


async def _test_rand(sid='sid', N=4, f=1):
    from honeybadgermpc.commonsubset_functionality import CommonSubset_IdealProtocol
    from honeybadgermpc.secretshare_functionality import SecretShare_IdealProtocol
    from honeybadgermpc.rand_batch import ShareRandom_Protocol, Poly
    SecretShare = SecretShare_IdealProtocol(N,f)
    CommonSubset = CommonSubset_IdealProtocol(N,f)

    B = 11
    rands = []
    # for i in range(N): # If set to N-1 (simulate crashed party, it gets stuck)
    for i in range(N):
        # Optionally fail to active the last one of them
        rands.append(ShareRandom_Protocol(B,N,f,sid,i,SecretShare,CommonSubset))

    print('_test_rand: awaiting results...')
    results = await asyncio.gather(*(rand.output for rand in rands))

    # Check reconstructions are valid
    for i in range(len(results[0])):
        shares = [(j+1,r[i]) for j,r in enumerate(results)]
        t1 = Poly.interpolate_at(shares[:f+1])
        t2 = Poly.interpolate_at(shares[-(f+1):])
        assert t1 == t2
    
    print('Done!')
    for a in SecretShare._instances.values():
        a._task.cancel()


def test_rand():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    try: loop.run_until_complete(_test_rand())
    finally: loop.close()
