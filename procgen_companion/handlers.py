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
    def _count(node: NodeType, count: Recursor, children: Iterable[Any]) -> int:
        child_counts = [count(child) for child in children]
        return functools.reduce(operator.mul, child_counts, 1)

    # @abstractmethod
    # def iterate(self, node: NodeType) -> Iterator[OutputType]:
        # pass


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
    Marker subclass with extra methods for static nodes.
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
    def children(node: dict) -> list[Any]:
        return list(node.values())


YAMLScalar = Union[str, int, float, bool]


class PlainScalar(StaticNodeHandler[YAMLScalar, YAMLScalar]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, (str, int, float, bool))

    @staticmethod
    def sample(node: YAMLScalar, sample: Recursor) -> YAMLScalar:
        return node

    @staticmethod
    def count(node: YAMLScalar, count: Recursor) -> int:
        return 1

    @staticmethod
    def children(node: YAMLScalar) -> list[Any]:
        return []

############################################################################
# AnimalAI nodes
############################################################################


class AnimalAIMapping(StaticNodeHandler[tags.CustomMappingTag, tags.CustomMappingTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomMappingTag)

    @staticmethod
    def sample(node: tags.CustomMappingTag, sample: Recursor) -> tags.CustomMappingTag:
        for k, v in node.__dict__.items():
            setattr(node, k, sample(v))
        return node

    @staticmethod
    def count(node: tags.CustomMappingTag, count: Recursor) -> int:
        return NodeHandler._count(node, count, node.__dict__.values())

    @staticmethod
    def children(node: tags.CustomMappingTag) -> list[Any]:
        return list(node.__dict__.values())


class AnimalAISequence(StaticNodeHandler[tags.CustomSequenceTag, tags.CustomSequenceTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomSequenceTag)

    @staticmethod
    def sample(node: tags.CustomSequenceTag, sample: Recursor) -> tags.CustomSequenceTag:
        for i, child in enumerate(node):
            node[i] = sample(child)
        return node

    @staticmethod
    def count(node: tags.CustomSequenceTag, count: Recursor) -> int:
        return NodeHandler._count(node, count, node)

    @staticmethod
    def children(node: tags.CustomSequenceTag) -> list[Any]:
        return list(iter(node))


class AnimalAIScalar(StaticNodeHandler[tags.CustomScalarTag, tags.CustomScalarTag]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomScalarTag)

    @staticmethod
    def sample(node: tags.CustomScalarTag, sample: Recursor) -> tags.CustomScalarTag:
        return node

    @staticmethod
    def count(node: tags.CustomScalarTag, count: Recursor) -> int:
        return 1

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
        return random.choice(node.options)

    @staticmethod
    def count(node: tags.ProcList, count: Recursor) -> int:
        return len(node.options)


class ProcColor(ProcGenNodeHandler[tags.ProcColor, tags.RGB]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcColor)

    @staticmethod
    def sample(node: tags.ProcColor, sample: Recursor) -> tags.RGB:
        return to_rgb(random.choice(util.COLORS))

    @staticmethod
    def count(node: tags.ProcColor, count: Recursor) -> int:
        return node.amount


def to_rgb(color: Tuple[int, int, int]) -> tags.RGB:
    return tags.RGB(r=color[0], g=color[1], b=color[2])


class ProcVector3Scaled(ProcGenNodeHandler[tags.ProcVector3Scaled, tags.Vector3]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcVector3Scaled)

    @staticmethod
    def sample(node: tags.ProcVector3Scaled, sample: Recursor) -> tags.Vector3:
        base = node.base if node.base is not None else tags.Vector3(x=0, y=0, z=0)
        scale = random.choice(node.scales)
        return scale_vector3(base, scale)

    @staticmethod
    def count(node: tags.ProcVector3Scaled, count: Recursor) -> int:
        return len(node.scales)


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


class ProcIf(ProcGenNodeHandler[tags.ProcIf, Any]):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcIf)

    @staticmethod
    def sample(node: tags.ProcIf, sample: Recursor) -> Any:
        # TODO: Implement
        # raise NotImplementedError()
        return random.choice(node.then)

    @staticmethod
    def count(node: tags.ProcIf, count: Recursor) -> int:
        # !ProcIf does not increase the number of variations.
        # It only sets some values in existing ones.
        return 1
