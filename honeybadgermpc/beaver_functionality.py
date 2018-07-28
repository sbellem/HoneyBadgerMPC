"""
Batch Beaver Multiplication

"""


def batch_beaver_mul(*, shared_pairs, beaver_triples):
    """Represents a protocol, which takes as input a set of pairs of
    :math:`t`-shared values along with a set of :math:`t`-shared
    triples; each triple will be "associated" with an input pair.
    Protocol ``BatchBeaver`` outputs a set of :math:`t`-sharing of the
    product of each pair of values if and only if the corresponding
    associated :math:`t`-shared triple is a multiplication-triple.
    
    """
    raise NotImplementedError
