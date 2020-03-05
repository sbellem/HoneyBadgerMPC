import asyncio

# from pathlib import Path

from pytest import mark

from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.preprocessing import PreProcessedElements, PreProcessingConstants


@mark.asyncio
async def test_get_triple():
    n, t = 4, 1
    num_triples = 2
    pp_elements = PreProcessedElements()
    pp_elements.generate_triples(1000, n, t)

    async def _prog(ctx):
        for _ in range(num_triples):
            a_sh, b_sh, ab_sh = ctx.preproc.get_triples(ctx)
            a, b, ab = await a_sh.open(), await b_sh.open(), await ab_sh.open()
            assert a * b == ab

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_cube():
    n, t = 4, 1
    num_cubes = 2
    pp_elements = PreProcessedElements()
    pp_elements.generate_cubes(1000, n, t)

    async def _prog(ctx):
        for _ in range(num_cubes):
            a1_sh, a2_sh, a3_sh = ctx.preproc.get_cubes(ctx)
            a1, a2, a3 = await a1_sh.open(), await a2_sh.open(), await a3_sh.open()
            assert a1 * a1 == a2
            assert a1 * a2 == a3

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_zero():
    n, t = 4, 1
    num_zeros = 2
    pp_elements = PreProcessedElements()
    pp_elements.generate_zeros(1000, n, t)

    async def _prog(ctx):
        for _ in range(num_zeros):
            x_sh = ctx.preproc.get_zero(ctx)
            assert await x_sh.open() == 0

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_rand():
    n, t = 4, 1
    num_rands = 2
    pp_elements = PreProcessedElements()
    pp_elements.generate_rands(1000, n, t)

    async def _prog(ctx):
        for _ in range(num_rands):
            # Nothing to assert here, just check if the
            # required number of rands are generated
            ctx.preproc.get_rand(ctx)

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_bit():
    n, t = 4, 1
    num_bits = 20
    pp_elements = PreProcessedElements()
    pp_elements.generate_bits(1000, n, t)

    async def _prog(ctx):
        shares = [ctx.preproc.get_bit(ctx) for _ in range(num_bits)]
        x = ctx.ShareArray(shares)
        x_ = await x.open()
        for i in x_:
            assert i == 0 or i == 1

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_powers():
    n, t = 4, 1
    pp_elements = PreProcessedElements()
    nums, num_powers = 2, 3

    pp_elements.generate_powers(num_powers, n, t, nums)

    async def _prog(ctx):
        for i in range(nums):
            powers = ctx.preproc.get_powers(ctx, i)
            x = await powers[0].open()
            for i, power in enumerate(powers[1:]):
                assert await power.open() == pow(x, i + 2)

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_share():
    n, t = 4, 1
    x = 41
    pp_elements = PreProcessedElements()
    sid = pp_elements.generate_share(n, t, x)

    async def _prog(ctx):
        x_sh = ctx.preproc.get_share(ctx, sid)
        assert await x_sh.open() == x

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_double_share():
    n, t = 9, 2
    pp_elements = PreProcessedElements()
    pp_elements.generate_double_shares(1000, n, t)

    async def _prog(ctx):
        r_t_sh, r_2t_sh = ctx.preproc.get_double_shares(ctx)
        assert r_t_sh.t == ctx.t
        assert r_2t_sh.t == ctx.t * 2
        await r_t_sh.open()
        await r_2t_sh.open()
        assert await r_t_sh.open() == await r_2t_sh.open()

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_share_bits():
    n, t, = 4, 1
    pp_elements = PreProcessedElements()
    pp_elements.generate_share_bits(1, n, t)

    async def _prog(ctx):
        share, bits = ctx.preproc.get_share_bits(ctx)
        opened_share = await share.open()
        opened_bits = await asyncio.gather(*[b.open() for b in bits])
        bit_value = int("".join([str(b.value) for b in reversed(opened_bits)]), 2)
        assert bit_value == opened_share.value

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    await program_runner.join()


@mark.asyncio
async def test_get_cross_shard_masks():
    n, t = 4, 1
    shard_1_id, shard_2_id = 3, 8
    # num_triples = 2
    pp_elements = PreProcessedElements()
    # pp_elements.generate_triples(1000, n, t)
    breakpoint()
    pp_elements.generate_cross_shard_masks(
        100, n, t, shard_1_id=shard_1_id, shard_2_id=shard_2_id
    )

    # async def _prog(ctx):
    #    for _ in range(num_triples):
    #        a_sh, b_sh, ab_sh = ctx.preproc.get_triples(ctx)
    #        a, b, ab = await a_sh.open(), await b_sh.open(), await ab_sh.open()
    #        assert a * b == ab

    # program_runner = TaskProgramRunner(n, t)
    # program_runner.add(_prog)
    # await program_runner.join()


def test_generate_cross_shard_masks():
    k, n, t = 100, 4, 1
    shards = (3, 8)
    pp_elements = PreProcessedElements()
    pp_elements.generate_cross_shard_masks(
        k, n, t, shard_1_id=shards[0], shard_2_id=shards[1]
    )
    cross_shard_masks = pp_elements._cross_shard_masks
    # check the cache
    cache = cross_shard_masks.cache
    assert len(cache) == 2 * n  # there are 2 shards with n servers in each
    # Check that the cache contains all expected keys. A key is a 3-tuple made
    # from (context_id, n, t), The context_id is made from "{i}-{shard_id}".
    assert all((f"{i}-{s}", n, t) in cache for i in range(n) for s in shards)
    breakpoint()
    assert all(len(tuple(elements)) == k for elements in cache.values())
    # check all the expected files have been created
    # TODO parse the files to be sure their content is as expected
    data_dir_path = cross_shard_masks.data_dir_path
    for shard_index, shard_id in enumerate(shards):
        other_shard = shards[1 - shard_index]
        for node_id in range(n):
            node_path = data_dir_path.joinpath(f"{node_id}-{shard_id}")
            assert node_path.exists()
            csm_path = node_path.joinpath(cross_shard_masks.preprocessing_name)
            assert csm_path.exists()
            file_path = csm_path.joinpath(f"{n}_{t}-{shard_id}_{other_shard}")
            full_file_path = file_path.with_suffix(
                PreProcessingConstants.SHARE_FILE_EXT.value
            )
            assert full_file_path.exists()
