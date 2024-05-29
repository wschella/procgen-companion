from procgen_companion.util import product as procgen_product

def product(*args, **kw):
    return list(procgen_product(*args, **kw))


def test_product_single():
    assert product('ABCD') == [('A',), ('B',), ('C',), ('D',)]


def test_product_double():
    assert product('ABCD', 'xy') == [('A', 'x'), ('A', 'y'), ('B', 'x'),
                                     ('B', 'y'), ('C', 'x'), ('C', 'y'), ('D', 'x'), ('D', 'y')]
