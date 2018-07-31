def rec_pub(d_share, e_share):
    raise NotImplementedError


def multiply(x, y, a, b, c):
    """
    Multiply the given pair of secret shares using Beaver's circuit
    randomization technique.
    
    .. todo:: add ref link to Beaver's paper

    :param secret_share_pair: Pair of secret shares to multiply.
    :param beaver_tiple_shares: Shares of a Beaver triple.

    :return: The result of :math:`[x \cdot y]_t` using Beaver's trick.
    """
    #x, y = secret_share_pair
    #a, b, c = beaver_triple_shares
    d_share = y - b
    e_share = x - a

    # TODO invoke public reconstruction
    d, e = rec_pub(d_share, e_share)

    return d*e +e*b + d*a + c


def batch_multiply(shares):
    """Batch multiply a set of :math:`t`-shared pairs, using Beaver's
    circuit randomization technique.

    :param shares: A set of length :math:`l` of the form:

    .. math::

        \{([x^{(i)}]_t, [y^{(i)}]_t, a^{(i)}, b^{(i)}, c^{(i)})\}_{i \in l}

    :return: The set :math:`\{[x^{(i)} y^{(i)}]_t\}_{i \in l}`
    """
    raise NotImplementedError
