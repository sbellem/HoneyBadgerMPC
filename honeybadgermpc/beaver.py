def rec_pub(d_share, e_share):
    raise NotImplementedError


def multiply(x, y, a, b, c):
    """
    Multiply the given pair of secret shares using Beaver's circuit
    randomization technique.
    
    .. todo:: add ref link to Beaver's paper

    :param secret_share_pair: Pair of secret shares to multiply.
    :param beaver_tiple_shares: Shares of a Beaver triple.
    """
    #x, y = secret_share_pair
    #a, b, c = beaver_triple_shares
    d_share = y - b
    e_share = x - a

    # TODO invoke public reconstruction
    d, e = rec_pub(d_share, e_share)
    return d*e +e*b + d*a + c
