from __future__ import annotations
from abc import ABC, abstractmethod
from typing import *

import yaml

NodeType = TypeVar("NodeType", bound="yaml.Node")

class CustomTag(ABC):
    tag: str

    @classmethod
    @abstractmethod
    def construct(cls, loader: yaml.Loader, node: Any) -> Any:
        pass

    @classmethod
    @abstractmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:
        pass

def GET_ANIMAL_AI_TAGS() -> List[Type[CustomTag]]:
    return [
        Arena,
        ArenaConfig,
        Item,
        Vector3,
        RGB,
    ]

def GET_PROC_GEN_TAGS() -> List[Type[CustomTag]]:
    return [
        ProcIf,
        ProcRepeatChoice,
        ProcList,
        ProcColor,
        ProcRestrictCombinations,
        ProcVector3Scaled,
    ]


class CustomMappingTag(CustomTag):
    flow_style ='block'
    order: Optional[list[str]] = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.MappingNode) -> Any:
        # Meaning of deep: https://stackoverflow.com/questions/43812020/what-does-deep-true-do-in-pyyaml-loader-construct-mapping
        # Otherwise, the custom tag constructors are called with empty lists and dicts.
        mapping = loader.construct_mapping(node, deep=True)
        str_mapping = {str(k): v for k, v in mapping.items()}
        return cls(**str_mapping)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:
        fields = data.__dict__
        if cls.order is not None:
            fields = [(k, fields[k]) for k in cls.order if k in fields]
        return dumper.represent_mapping(f"!{cls.tag}", fields, flow_style=(cls.flow_style == 'flow'))


class CustomSequenceTag(CustomTag, Iterable[Any]):
    @abstractmethod
    def __init__(self, value: Any) -> None:
        pass

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.SequenceNode) -> Any:
        sequence = loader.construct_sequence(node)
        return cls(sequence)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:
        return dumper.represent_sequence(f"!{cls.tag}", data)

    @abstractmethod
    def __setitem__(self, key: int, value: Any) -> None:
        pass


class CustomScalarTag(CustomTag):

    @abstractmethod
    def __init__(self, value: Any) -> None:
        pass

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.ScalarNode) -> Any:
        return cls(node.value)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:
        assert len(data.__dict__) == 1
        value = next(iter(data.__dict__.values())) # Should only be one value
        return dumper.represent_scalar(f"!{cls.tag}", str(value))

# ------------ AnimalAI Tags ------------

class Arena(CustomMappingTag):
    tag: str = "Arena"
    order = ['pass_mark', 't', 'items']

    pass_mark: Any
    t: Any
    items: Any


class ArenaConfig(CustomMappingTag):
    tag: str = "ArenaConfig"
    arenas: dict[int, Arena] = {}

    def __init__(self, arenas: dict[int, Arena]):
        self.arenas = arenas

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.MappingNode) -> Any:
        mapping = loader.construct_mapping(node)
        arenas: dict[int, Arena] = mapping['arenas']
        return ArenaConfig(arenas)



class Item(CustomMappingTag):
    tag: str = "Item"
    order = ['name', 'positions', 'rotations', 'colors', 'sizes']

    name: str
    positions: Any
    rotations: Any
    colors: Any
    sizes: Any


class Vector3(CustomMappingTag):
    tag: str = "Vector3"
    flow_style: str = 'flow'
    order = ['x', 'y', 'z']

    x: Any
    y: Any
    z: Any

class RGB(CustomMappingTag):
    tag: str = "RGB"
    flow_style: str = 'flow'
    order = ['r', 'g', 'b']

    r: Any
    g: Any
    b: Any

# ------------ ProcGen tags ------------

class ProcIf(CustomMappingTag):
    tag: str = "ProcIf"
    value: str
    range: list
    then: Any
    else_: Any

    # We need to override the constructor to handle the else_ keyword
    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.MappingNode) -> Any:
        mapping = loader.construct_mapping(node)
        str_mapping = {str(k): v for k, v in mapping.items()}
        str_mapping['else_'] = str_mapping['else']
        del str_mapping['else']
        return cls(**str_mapping)


class ProcRepeatChoice(CustomMappingTag):
    tag: str = "ProcRepeatChoice"
    amount: int
    value: Any

    def __init__(self, amount: int, value: Any):
        self.amount = int(amount)
        self.value = value


class ProcList(CustomMappingTag):
    tag: str = "ProcList"
    options: list

# Leaf node
class ProcColor(CustomScalarTag):
    tag: str = "ProcColor"
    amount: int

    def __init__(self, amount: int):
        self.amount = int(amount)


class ProcRestrictCombinations(CustomMappingTag):
    tag: str = "ProcRestrictCombinations"
    amount: int
    item: Any

    def __init__(self, amount: int, item: Any):
        self.amount = int(amount)
        self.item = item


class ProcVector3Scaled(CustomMappingTag):
    tag: str = "ProcVector3Scaled"
    base: Vector3
    range: list[float]
    amount: int

    def __init__(self, base: Vector3, range: list, amount: int):
        self.base = base
        self.range = [float(x) for x in range]
        self.amount = int(amount)
