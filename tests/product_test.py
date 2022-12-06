from pytest import approx

from procgen_companion.util import product as procgen_product
from procgen_companion.util import linspace as linspace

product = lambda *args, **kw: list(procgen_product(*args, **kw))


def test_product_single():
    assert product('ABCD') == [('A',), ('B',), ('C',), ('D',)]


def test_product_double():
    assert product('ABCD', 'xy') == [('A', 'x'), ('A', 'y'), ('B', 'x'),
                                     ('B', 'y'), ('C', 'x'), ('C', 'y'), ('D', 'x'), ('D', 'y')]

def test_linspace():
    assert list(linspace(0, 1, num=5, endpoint=True)) == approx([0., 0.25, 0.5, 0.75, 1.])
    assert list(linspace(0, 1, num=5, endpoint=False)) == approx([0., 0.2, 0.4, 0.6, 0.8])