from pytest import mark


@mark.asyncio
@mark.zeros(N=3, t=2, k=1000)
async def test_open_shares(zeros_files_prefix):
    from honeybadgermpc.passive import runProgramInNetwork
    N, t = 3, 2
    number_of_secrets = 100

    async def _prog(context):
        filename = f'{zeros_files_prefix}-{context.myid}.share'
        shares = context.read_shares(open(filename))

        print('[%d] read %d shares' % (context.myid, len(shares)))

        secrets = []
        for share in shares[:number_of_secrets]:
            s = await share.open()
            assert s == 0
            secrets.append(s)
        print('[%d] Finished' % (context.myid,))
        return secrets

    results = await runProgramInNetwork(_prog, N, t)
    assert len(results) == N
    assert all(len(secrets) == number_of_secrets for secrets in results)
    assert all(secret == 0 for secrets in results for secret in secrets)


@mark.asyncio
@mark.zeros(N=3, t=2, k=1000)
@mark.triples(N=3, t=2, k=1000)
async def test_beaver_mul_with_zeros(zeros_files_prefix, triples_files_prefix):
    from honeybadgermpc.passive import runProgramInNetwork
    N, t = 3, 2
    x_secret, y_secret = 10, 15

    async def _prog(context):
        filename = f'{zeros_files_prefix}-{context.myid}.share'
        zeros = context.read_shares(open(filename))
        filename = f'{triples_files_prefix}-{context.myid}.share'
        triples = context.read_shares(open(filename))

        # Example of Beaver multiplication
        x = zeros[0] + context.Share(x_secret)
        y = zeros[1] + context.Share(y_secret)

        a, b, ab = triples[:3]
        assert await a.open() * await b.open() == await ab.open()

        D = await (x - a).open()
        E = await (y - b).open()

        # This is a random share of x*y
        xy = context.Share(D*E) + D*b + E*a + ab

        X, Y, XY = await x.open(), await y.open(), await xy.open()
        assert X * Y == XY

        print("[%d] Finished" % (context.myid,), X, Y, XY)
        return XY

    results = await runProgramInNetwork(_prog, N, t)
    assert len(results) == N
    assert all(res == x_secret * y_secret for res in results)


@mark.asyncio
@mark.triples(N=3, t=2, k=1000)
@mark.randoms(N=3, t=2, k=1000)
async def test_beaver_mul(random_files_prefix, triples_files_prefix):
    from honeybadgermpc.passive import runProgramInNetwork
    N, t = 3, 2
    # TODO find a way to "pin down" the random polys so that they can be reused
    # f, g = random_polys(t=t, k=k)[:2]
    # x_secret, y_secret = f(0), g(0)

    async def _prog(context):
        filename = f'{random_files_prefix}-{context.myid}.share'
        randoms = context.read_shares(open(filename))
        filename = f'{triples_files_prefix}-{context.myid}.share'
        triples = context.read_shares(open(filename))

        # Example of Beaver multiplication
        x, y = randoms[:2]

        a, b, ab = triples[:3]
        assert await a.open() * await b.open() == await ab.open()

        D = await (x - a).open()
        E = await (y - b).open()

        # This is a random share of x*y
        xy = context.Share(D*E) + D*b + E*a + ab

        X, Y, XY = await x.open(), await y.open(), await xy.open()
        assert X * Y == XY

        print("[%d] Finished" % (context.myid,), X, Y, XY)
        return XY

    results = await runProgramInNetwork(_prog, N, t)
    assert len(results) == N
    # assert all(res == x_secret * y_secret for res in results)
