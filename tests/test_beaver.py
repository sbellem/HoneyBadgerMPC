from pytest import fixture, mark


def _f(x):
    """Polynomial of degree :math:`t=2` for which a secret :math:`f(0)`
    can be generated.
    """
    return x**2 + x + 3


@fixture
def f(request):
    x = getattr(request, 'param', 0)
    return _f(x)


def _g(x):
    """Polynomial of degree :math:`t=2` for which a secret :math:`f(0)`
    can be generated.
    """
    return 2*x**2 -x + 2


@fixture
def g(request):
    x = getattr(request, 'param', 0)
    return _g(x)


@fixture
def b1(request):
    x = getattr(request, 'param', 0)
    return x**2 - x + 2


@fixture
def b2(request):
    x = getattr(request, 'param', 0)
    return x**2 - x + 3


@fixture
def b3(request):
    x = getattr(request, 'param', 0)
    return x**2 - x + 6


@fixture
def d(g, b2):
    return g - b2


@fixture
def e(f, b1):
    return f - b1


@fixture
def polynomials(f, g, b1, b2, b3):
    return f, g, b1, b2, b3


@mark.parametrize('polynomials', (1, 2, 3), indirect=('polynomials',))
def test_beaver(mocker, polynomials, e, d):
    from honeybadgermpc.beaver import multiply
    rec_pub_func = 'honeybadgermpc.beaver.rec_pub'
    mocked_rec_pub = mocker.patch(rec_pub_func)
    mocked_rec_pub.return_value = d, e
    f, g, b1, b2, b3 = polynomials
    expected_result = d*e + e*b2 + d*b1 + b3
    result = multiply(f, g, b1, b2, b3)
    assert result == expected_result
