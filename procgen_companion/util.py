from __future__ import annotations
import itertools
import collections
from typing import *

import yaml

from procgen_companion import tags


def product(*iterables, **kwargs):
    """
    Cartesian product of input iterables.
    As opposed to itertools.product, this function does not
    consumes the full iterable before returning the first element.
    I.e. there are no huge memory requirements.

    Examples:
        product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy

    References:
        [source] <https://stackoverflow.com/questions/12093364/cartesian-product-of-large-iterators-itertools>
        [itertools.product] <https://docs.python.org/3/library/itertools.html#itertools.product>
    """
    if len(iterables) == 0:
        yield ()
    else:
        iterables = iterables * kwargs.get('repeat', 1)
        it = iterables[0]
        for item in it() if callable(it) else iter(it):
            for items in product(*iterables[1:]):
                yield (item, ) + items


def custom_list_representer(dumper, data):
    """
    Custom representer for lists that uses flow style (i.e. short inline style)
    if all items are scalars or !R ranges.
    """
    if all(isinstance(item, (str, int, float, tags.Range)) for item in data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
    else:
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)


def pprint(node: Any) -> str:
    """
    Pretty print a node.
    """
    return yaml.dump(node, default_flow_style=False, sort_keys=False, Dumper=yaml.SafeDumper)


def consume(iterator, n=None):
    """
    Advance the iterator n-steps ahead. If n is None, consume entirely.

    Source:
        https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        collections.deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(itertools.islice(iterator, n, n), None)


# The first three colors in the list are red, green, and blue, respectively.
# The next three colors are yellow, magenta, and cyan, which are created by mixing the primary colors.
# The last four colors are various shades of gray.
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
          (0, 255, 255), (192, 192, 192), (128, 128, 128), (128, 0, 0), (0, 128, 0)]


class MutablePlaceholder():
    # This could all be in !ProcIf, but we don't want to overload the tags.ProcIf class.
    # Therefore, we replace it during generation with this one, which deals with
    # resolving the conditionals during yaml.dump.

    proc_if: Callable[[Any], Any]
    value: Optional[Any]
    label: Optional[str]

    def __init__(self, proc_if: Callable[[Any], Any]):
        self.proc_if = proc_if
        self.value = None

    def fill(self, root: Any):
        self.value, self.label = self.proc_if(root)
        return self.value, self.label

    def is_filled(self):
        return self.value is not None

    def __getitem__(self, key):
        if self.value is None:
            raise ValueError("MutablePlaceholder has not been filled yet. Programmer error.")
        return self.value[key]

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: MutablePlaceholder) -> Any:
        if data.value is None:
            raise ValueError("MutablePlaceholder has not been filled yet. Programmer error.")
        return dumper.represent_data(data.value)
