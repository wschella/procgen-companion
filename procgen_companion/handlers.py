from typing import *
from abc import ABC, abstractmethod
from copy import deepcopy
import random
import functools
import operator

import procgen_companion.tags as tags
import procgen_companion.util as util

NodeType = TypeVar("NodeType")
OutputType = TypeVar("OutputType")

Recursor = Callable[[Any], Any]


class NodeHandler(ABC, Generic[NodeType, OutputType]):
    """
    Singletons. Only bundle logic.
    """

    @staticmethod
    @abstractmethod
    def can_handle(node: Any) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def sample(node: NodeType, sample: Recursor) -> OutputType:
        pass

    @staticmethod
    @abstractmethod
    def count(node: NodeType, count: Recursor) -> int:
        pass

    @staticmethod
    @abstractmethod
    def iterate(node: NodeType, iterate: Recursor) -> Iterator[OutputType]:
        pass

    @staticmethod
    def _count(node: NodeType, count: Recursor, children: Iterable[Any]) -> int:
        child_counts = [count(child) for child in children]
        return functools.reduce(operator.mul, child_counts, 1)


class StaticNodeHandler(NodeHandler[NodeType, OutputType], Generic[NodeType, OutputType]):
    """
    Marker subclass with extra methods for static nodes.
    """
    @staticmethod
    @abstractmethod
    def children(node: NodeType) -> List[Any]:
        pass


class ProcGenNodeHandler(NodeHandler[NodeType, OutputType], Generic[NodeType, OutputType]):
    """
    Marker subclass.
    """

############################################################################
# Plain nodes
############################################################################


class PlainSequence(StaticNodeHandler[list, list]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, list)

    @staticmethod
    def sample(node: list, sample: Recursor) -> list:
        return [sample(child) for child in node]

    @staticmethod
    def count(node: list, count: Recursor) -> int:
        return NodeHandler._count(node, count, node)

    @staticmethod
    def iterate(node: list, iterate: Recursor) -> Iterator[list]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)
        return (list(variant) for variant in product_generator)

    @staticmethod
    def children(node: list) -> Any:
        return node


class PlainMapping(StaticNodeHandler[dict, dict]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, dict)

    @staticmethod
    def sample(node: dict, sample: Recursor) -> dict:
        return {k: sample(v) for k, v in node.items()}

    @staticmethod
    def count(node: dict, count: Recursor) -> int:
        return NodeHandler._count(node, count, node.values())

    @staticmethod
    def iterate(node: dict, iterate: Recursor) -> Iterator[dict]:
        # We get the keys() early so they definitely align with the values().
        keys = list(node.keys())

        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node.values()]

        # Each yield of product_generator is a single variant (but only the dict values).
        product_generator = util.product(*child_iterators)
        redict = lambda variant_values: dict(zip(keys, variant_values))
        return (redict(variant_values) for variant_values in product_generator)

    @staticmethod
    def children(node: dict) -> list[Any]:
        return list(node.values())


YAMLScalar = Union[str, int, float, bool]


class PlainScalar(StaticNodeHandler[YAMLScalar, YAMLScalar]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, (str, int, float, bool))

    @staticmethod
    def sample(node: YAMLScalar, sample: Recursor) -> YAMLScalar:
        return deepcopy(node)

    @staticmethod
    def count(node: YAMLScalar, count: Recursor) -> int:
        return 1

    @staticmethod
    def iterate(node: YAMLScalar, iterate: Recursor) -> Iterator[YAMLScalar]:
        return iter([deepcopy(node)])

    @staticmethod
    def children(node: YAMLScalar) -> list[Any]:
        return []

############################################################################
# AnimalAI nodes
############################################################################


class AnimalAISequence(StaticNodeHandler[tags.CustomSequenceTag, tags.CustomSequenceTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomSequenceTag)

    @staticmethod
    def sample(node: tags.CustomSequenceTag, sample: Recursor) -> tags.CustomSequenceTag:
        values = [sample(child) for child in node]
        return type(node)(values)

    @staticmethod
    def count(node: tags.CustomSequenceTag, count: Recursor) -> int:
        return NodeHandler._count(node, count, node)

    @staticmethod
    def iterate(node: tags.CustomSequenceTag, iterate: Recursor) -> Iterator[tags.CustomSequenceTag]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)
        return (type(node)(list(variant)) for variant in product_generator)

    @staticmethod
    def children(node: tags.CustomSequenceTag) -> list[Any]:
        return list(iter(node))


class AnimalAIMapping(StaticNodeHandler[tags.CustomMappingTag, tags.CustomMappingTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomMappingTag)

    @staticmethod
    def sample(node: tags.CustomMappingTag, sample: Recursor) -> tags.CustomMappingTag:
        kvs = {k: sample(v) for k, v in node.__dict__.items()}
        return type(node)(**kvs)

    @staticmethod
    def count(node: tags.CustomMappingTag, count: Recursor) -> int:
        return NodeHandler._count(node, count, node.__dict__.values())

    @staticmethod
    def iterate(node: tags.CustomMappingTag, iterate: Recursor) -> Iterator[tags.CustomMappingTag]:
        # We get the keys() early so they definitely align with the values().
        keys = list(node.__dict__.keys())

        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node.__dict__.values()]

        # Each yield of product_generator is a single variant (but only the dict values).
        product_generator = util.product(*child_iterators)
        redict = lambda variant_values: dict(zip(keys, variant_values))
        return iter(type(node)(**redict(variant_values)) for variant_values in product_generator)

    @staticmethod
    def children(node: tags.CustomMappingTag) -> list[Any]:
        return list(node.__dict__.values())


class AnimalAIScalar(StaticNodeHandler[tags.CustomScalarTag, tags.CustomScalarTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomScalarTag)

    @staticmethod
    def sample(node: tags.CustomScalarTag, sample: Recursor) -> tags.CustomScalarTag:
        return deepcopy(node)

    @staticmethod
    def count(node: tags.CustomScalarTag, count: Recursor) -> int:
        return 1

    @staticmethod
    def iterate(node: tags.CustomScalarTag, iterate: Recursor) -> Iterator[tags.CustomScalarTag]:
        return iter([deepcopy(node)])

    @staticmethod
    def children(node: tags.CustomScalarTag) -> list[Any]:
        return []


############################################################################
# ProcGen nodes
############################################################################


class ProcList(ProcGenNodeHandler[tags.ProcList, Any]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcList)

    @staticmethod
    def sample(node: tags.ProcList, sample: Recursor) -> Any:
        return deepcopy(random.choice(node.options))

    @staticmethod
    def count(node: tags.ProcList, count: Recursor) -> int:
        return len(node.options)

    @staticmethod
    def iterate(node: tags.ProcList, iterate: Recursor) -> Iterator[Any]:
        return (deepcopy(option) for option in node.options)


class ProcColor(ProcGenNodeHandler[tags.ProcColor, tags.RGB]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcColor)

    @staticmethod
    def sample(node: tags.ProcColor, sample: Recursor) -> tags.RGB:
        return to_rgb(deepcopy(random.choice(util.COLORS)))

    @staticmethod
    def count(node: tags.ProcColor, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcColor, iterate: Recursor) -> Iterator[tags.RGB]:
        return iter([to_rgb(deepcopy(c)) for c in util.COLORS[:node.amount]])


def to_rgb(color: Tuple[int, int, int]) -> tags.RGB:
    return tags.RGB(r=color[0], g=color[1], b=color[2])


class ProcVector3Scaled(ProcGenNodeHandler[tags.ProcVector3Scaled, tags.Vector3]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcVector3Scaled)

    @staticmethod
    def sample(node: tags.ProcVector3Scaled, sample: Recursor) -> tags.Vector3:
        base = deepcopy(node.base) if node.base is not None else tags.Vector3(x=0, y=0, z=0)
        scale = random.choice(node.scales)
        return scale_vector3(base, scale)

    @staticmethod
    def count(node: tags.ProcVector3Scaled, count: Recursor) -> int:
        return len(node.scales)

    @staticmethod
    def iterate(node: tags.ProcVector3Scaled, iterate: Recursor) -> Iterator[tags.Vector3]:
        base = node.base if node.base is not None else tags.Vector3(x=0, y=0, z=0)
        return iter([scale_vector3(deepcopy(base), scale) for scale in node.scales])


def scale_vector3(vector: tags.Vector3, scale: float) -> tags.Vector3:
    return tags.Vector3(x=vector.x * scale, y=vector.y * scale, z=vector.z * scale)


class ProcRepeatChoice(ProcGenNodeHandler[tags.ProcRepeatChoice, Any]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRepeatChoice)

    @staticmethod
    def sample(node: tags.ProcRepeatChoice, sample: Recursor) -> Any:
        choice = sample(node.value)
        return [choice] + [deepcopy(choice) for _ in range(node.amount - 1)]

    @staticmethod
    def count(node: tags.ProcRepeatChoice, count: Recursor) -> int:
        return count(node.value)

    @staticmethod
    def iterate(node: tags.ProcRepeatChoice, iterate: Recursor) -> Iterator[Any]:
        duplicate = lambda var: [var] + [deepcopy(var) for _ in range(node.amount - 1)]
        return (duplicate(var) for var in iterate(node.value))


class ProcRestrictCombinations(ProcGenNodeHandler[tags.ProcRestrictCombinations, Any]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRestrictCombinations)

    @staticmethod
    def sample(node: tags.ProcRestrictCombinations, sample: Recursor) -> Any:
        return sample(node.item)

    @staticmethod
    def count(node: tags.ProcRestrictCombinations, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcRestrictCombinations, iterate: Recursor) -> Iterator[Any]:
        # This implementation would take the first amount of variations...
        # item_iter = iterate(node.item)
        # return (next(item_iter) for _ in range(node.amount))

        # ... but we want to sample instead, as that result in a wider selection of variations.
        from procgen_companion.procgen import sample_recursive
        return (sample_recursive(node.item) for _ in range(node.amount))


class ProcIf(ProcGenNodeHandler[tags.ProcIf, Any]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcIf)

    @staticmethod
    def sample(node: tags.ProcIf, sample: Recursor) -> Any:
        # TODO: Implement
        # raise NotImplementedError()
        # return random.choice(node.then)
        return node

    @staticmethod
    def count(node: tags.ProcIf, count: Recursor) -> int:
        # !ProcIf does not increase the number of variations.
        # It only sets some values in existing ones.
        return 1

    @staticmethod
    def iterate(node: tags.ProcIf, iterate: Recursor) -> Iterator[Any]:
        # raise NotImplementedError()
        # TODO: Implement
        return iter([deepcopy(node)])
