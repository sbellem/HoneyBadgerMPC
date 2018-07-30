# from pytest import fixture


def f(x=0):
    return x**2 + x + 3


def g(x=0):
    """Polynomial of degree :math:`t=2` for which a secret :math:`f(0)`
    can be generated.
    """
    return 2*x**2 -x + 2


def b1(x=0):
    return x**2 - x + 2


def b2(x=0):
    return x**2 - x + 3


def b3(x=0):
    return x**2 - x + 6


def test_beaver(mocker):
    from honeybadgermpc.beaver import multiply
    rec_pub_func = 'honeybadgermpc.beaver.rec_pub'
    nodeid = 1
    e = f(0) - b1(0)
    d = g(0) - b2(0)
    mocked_rec_pub = mocker.patch(rec_pub_func)
    mocked_rec_pub.return_value = d, e
    expected_result = d*e + e*b2(1) + d*b1(1) + b3(1)
    result = multiply(f(1), g(1), b1(1), b2(1), b3(1))
    assert result == expected_result
