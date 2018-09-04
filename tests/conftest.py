import os
import random

from pytest import fixture


def pytest_configure(config):
    # register markers
    config.addinivalue_line(
        'markers',
        'zeros(N, t, k): mark test to generate files of polynomials for zeros',
    )
    config.addinivalue_line(
        'markers',
        'triples(N, t, k): mark test to generate files of polynomials for triples',
    )
    config.addinivalue_line(
        'markers',
        'randoms(N, t, k): mark test to generate files of polynomials for randoms',
    )


@fixture(autouse=True)
def _zeros_marker(request):
    if request.keywords.get('zeros', None):
        request.getfixturevalue('_zeros')


@fixture(autouse=True)
def _triples_marker(request):
    if request.keywords.get('triples', None):
        request.getfixturevalue('_triples')


@fixture(autouse=True)
def _randoms_marker(request):
    if request.keywords.get('randoms', None):
        request.getfixturevalue('_randoms')


@fixture
def _zeros(request, zeros_shares_files):
    kwargs = request.keywords.get('zeros').kwargs
    return zeros_shares_files(**kwargs)


@fixture
def _triples(request, triples_shares_files):
    kwargs = request.keywords.get('triples').kwargs
    return triples_shares_files(**kwargs)


@fixture
def _randoms(request, random_shares_files):
    kwargs = request.keywords.get('randoms').kwargs
    return random_shares_files(**kwargs)


@fixture
def sharedata_tmpdir(tmpdir):
    return tmpdir.mkdir('sharedata')


@fixture
def zeros_files_prefix(sharedata_tmpdir):
    return os.path.join(sharedata_tmpdir, 'test_zeros')


@fixture
def random_files_prefix(sharedata_tmpdir):
    return os.path.join(sharedata_tmpdir, 'test_random')


@fixture
def triples_files_prefix(sharedata_tmpdir):
    return os.path.join(sharedata_tmpdir, 'test_triples')


@fixture
# TODO check whether there could be a better name for this fixture,
# e.g.: bls12_381_field?
def GaloisField():
    from honeybadgermpc.field import GF
    return GF(0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001)


@fixture
def Polynomial(GaloisField):
    from honeybadgermpc.polynomial import polynomialsOver
    return polynomialsOver(GaloisField)


@fixture
def zero_polys(request, Polynomial):
    def _gen(*, t, k):
        return [Polynomial.random(t, 0) for _ in range(k)]
    return _gen


@fixture
def random_polys(GaloisField, Polynomial):

    def _gen(*, t, k):
        return [
            Polynomial.random(t, random.randint(0, GaloisField.modulus-1))
            for _ in range(k)
        ]

    return _gen


@fixture
def triples_fields(GaloisField, Polynomial):

    def _gen(*, k):
        fields_batch = []
        for _ in range(k):
            a = GaloisField(random.randint(0, GaloisField.modulus-1))
            b = GaloisField(random.randint(0, GaloisField.modulus-1))
            c = a*b
            fields_batch.append((a, b, c))
        return fields_batch

    return _gen


@fixture
def triples_polys(triples_fields, Polynomial):

    def _gen(*, t, k):
        triples = triples_fields(k=k)
        return [
            Polynomial.random(t, field)
            for triple in triples for field in triple
        ]

    return _gen


@fixture
def zeros_shares_files(GaloisField, zero_polys, zeros_files_prefix):
    from honeybadgermpc.passive import write_polys

    def _gen(*, N, t, k):
        polys = zero_polys(k=k, t=t)
        write_polys(zeros_files_prefix, GaloisField.modulus, N, t, polys)

    return _gen


@fixture
def random_shares_files(GaloisField, random_polys, random_files_prefix):
    from honeybadgermpc.passive import write_polys

    def _gen(*, N, t, k):
        polys = random_polys(t=t, k=k)
        write_polys(random_files_prefix, GaloisField.modulus, N, t, polys)

    return _gen


@fixture
def triples_shares_files(GaloisField, triples_polys, triples_files_prefix):
    from honeybadgermpc.passive import write_polys

    def _gen(*, N, t, k):
        polys = triples_polys(t=t, k=k)
        write_polys(triples_files_prefix, GaloisField.modulus, N, t, polys)

    return _gen
