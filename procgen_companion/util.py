import types


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


def allstatic(cls):
    """
    Class decorator that makes all methods static.

    Source: https://stackoverflow.com/questions/35292547/how-to-decorate-class-or-static-methods
    """
    for name, member in vars(cls).items():
        # Good old function object, just decorate it
        if isinstance(member, (types.FunctionType, types.BuiltinFunctionType)):
            setattr(cls, name, staticmethod(member))
            continue

        # Class methods: do the dark magic
        if isinstance(member, (classmethod)):
            inner_func = member.__func__
            method_type = type(member)
            decorated = method_type(staticmethod(inner_func))
            setattr(cls, name, decorated)
            continue

        # We don't care about anything else

    return cls

# def linspace(start, stop, num=50, endpoint=True) -> list:
#     return list(linspace_gen(start, stop, num, endpoint))

# def linspace_gen(start, stop, num=50, endpoint=True):
#     num = int(num)
#     start = start * 1.
#     stop = stop * 1.

#     if num == 1:
#         yield stop
#         return
#     if endpoint:
#         step = (stop - start) / (num - 1)
#     else:
#         step = (stop - start) / num

#     for i in range(num):
#         yield start + step * i


# The first three colors in the list are red, green, and blue, respectively.
# The next three colors are yellow, magenta, and cyan, which are created by mixing the primary colors.
# The last four colors are various shades of gray.
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
          (0, 255, 255), (192, 192, 192), (128, 128, 128), (128, 0, 0), (0, 128, 0)]
