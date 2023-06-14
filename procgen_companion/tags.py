from __future__ import annotations
from abc import ABC, abstractmethod
from typing import *

import yaml

import procgen_companion.errors as errors


class CustomTag(ABC):
    tag: str

    @classmethod
    @abstractmethod
    def construct(cls, loader: yaml.Loader, node: Any) -> Any:
        pass

    @classmethod
    @abstractmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:  # type: ignore
        pass

    @abstractmethod
    def __getitem__(self, item: Any) -> Any:
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
        ProcList,
        ProcListLabelled,
        ProcColor,
        ProcVector3Scaled,
        ProcRepeatChoice,
        ProcRestrictCombinations,
        ProcIf,
    ]


def GET_SPECIAL_TAGS() -> List[Type[CustomTag]]:
    return [
        Range,
        ProcIfLabels,
    ]


class AnimalAITag():
    """
    Simple marker class for AnimalAI tags.
    """


class ProcGenTag():
    """
    Simple marker class for ProcGen tags.
    """
    pass


class WithId():
    id: Optional[str]  # Might not be initialised to None

    def get_id(self) -> Optional[str]:
        if hasattr(self, 'id'):
            return self.id
        return None


class WithTemplateMeta():
    # This is only used for ArenaConfig, but we do this in a separate class
    # such that proc_meta doesn't show in __dict__.
    proc_meta: Optional[Dict[str, Any]]  # Might not be initialised to None

    def get_proc_meta(self) -> Optional[TemplateMeta]:
        if hasattr(self, 'proc_meta') and self.proc_meta is not None:
            return TemplateMeta(**self.proc_meta)
        return None

    def del_proc_meta(self) -> None:
        if hasattr(self, 'proc_meta'):
            del self.proc_meta


class CustomMappingTag(CustomTag):

    # Note: All AnimalAI mapping specify an order of their fields for dumping.
    # This allows us to:
    # - Specify a fixed, sane, order for all the fields (e.g. x,y,z for Vector3)
    # - Filter out meta-fields like 'id' that are not part of the AnimalAI spec.
    order: Optional[list[str]] = None
    flow_style = 'block'

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.MappingNode) -> Any:
        # Meaning of deep: https://stackoverflow.com/questions/43812020/what-does-deep-true-do-in-pyyaml-loader-construct-mapping
        # Otherwise, the custom tag constructors are called with empty lists and dicts.
        mapping = loader.construct_mapping(node, deep=True)
        str_mapping = {str(k): v for k, v in mapping.items()}

        # Validate
        annotations = cls.__dict__['__annotations__']
        for k in str_mapping.keys():
            if k not in annotations:
                raise ValueError(f"Unexpected key '{k}' in tag '{cls.tag}'")

        return cls(**str_mapping)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:  # type: ignore
        dd = data.__dict__
        fields = (
            list(dd.items()) if (cls.order is None) else  # Unordered
            [(k, dd[k]) for k in cls.order if k in dd])  # Ordered
        fields = [(k, v) for k, v in fields if v != None]  # Filter out None values
        return dumper.represent_mapping(f"!{cls.tag}", fields, flow_style=(cls.flow_style == 'flow'))

    def __getitem__(self, item: Any) -> Any:
        return self.__dict__[item]


class CustomSequenceTag(CustomTag, Iterable[Any]):
    flow_style = 'block'

    @abstractmethod
    def __init__(self, value: Any) -> None:
        pass

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.SequenceNode) -> Any:
        sequence = loader.construct_sequence(node)
        return cls(sequence)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:  # type: ignore
        return dumper.represent_sequence(f"!{cls.tag}", data, flow_style=(cls.flow_style == 'flow'))

    @abstractmethod
    def __setitem__(self, key: int, value: Any) -> None:
        pass

    @abstractmethod
    def __getitem__(self, item: Any) -> Any:
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[Any]:
        pass


class CustomScalarTag(CustomTag):

    @abstractmethod
    def __init__(self, value: Any) -> None:
        pass

    @classmethod
    def construct(cls, loader: yaml.Loader, node: yaml.nodes.ScalarNode) -> Any:
        return cls(node.value)

    @classmethod
    def represent(cls, dumper: yaml.Dumper, data: Self) -> Any:  # type: ignore
        assert len(data.__dict__) == 1
        value = next(iter(data.__dict__.values()))  # Should only be one value
        return dumper.represent_scalar(f"!{cls.tag}", str(value))

    def __getitem__(self, item: Any) -> Any:
        raise ValueError(f"Scalar tag '{self.tag} {self}' does not being indexed.")

# ------------ AnimalAI Tags ------------


class ArenaConfig(CustomMappingTag, AnimalAITag, WithId, WithTemplateMeta):
    # Optional meta information that will not be printed
    tag: str = "ArenaConfig"
    order: list[str] = ['arenas']
    proc_meta: Optional[dict[str, Any]]
    id: Optional[str]

    # Actual fields
    arenas: dict[int, Arena] = {}


class Arena(CustomMappingTag, AnimalAITag, WithId):
    tag: str = "Arena"
    order = ['pass_mark', 't', 'items']
    id: Optional[str]

    pass_mark: Any
    t: Any
    items: Any


class Item(CustomMappingTag, AnimalAITag, WithId):
    tag: str = "Item"
    order = ['name', 'positions', 'rotations', 'colors', 'sizes']
    id: Optional[str]

    name: str
    positions: Any
    rotations: Any
    colors: Any
    sizes: Any
    symbolNames: Any


class Vector3(CustomMappingTag, AnimalAITag, WithId):
    tag: str = "Vector3"
    flow_style: str = 'flow'
    order = ['x', 'y', 'z']
    id: Optional[str]

    x: Any
    y: Any
    z: Any

    def __init__(self, x: Any, y: Any, z: Any) -> None:
        self.x = x
        self.y = y
        self.z = z

        if isinstance(x, list) or isinstance(y, list) or isinstance(z, list):
            raise errors.NodeAnnotatedProcGenError(
                self, "FaultyType", "Vector3 fields x, y, z can not have lists as values.")


class RGB(CustomMappingTag, AnimalAITag, WithId):
    tag: str = "RGB"
    flow_style: str = 'flow'
    order = ['r', 'g', 'b']
    id: Optional[str]

    r: Any
    g: Any
    b: Any

# ------------ ProcGen tags ------------


class ProcList(CustomSequenceTag, ProcGenTag):
    tag: str = "ProcList"

    options: list

    def __init__(self, options: Any) -> None:
        self.options = options

    def __setitem__(self, key: int, value: Any) -> None:
        return self.options.__setitem__(key, value)

    def __getitem__(self, item: Any) -> Any:
        return self.options.__getitem__(item)

    def __iter__(self) -> Iterator[Any]:
        return self.options.__iter__()


class ProcListLabelled(CustomSequenceTag, ProcGenTag):
    tag: str = "ProcListLabelled"

    options: list

    def __init__(self, options: Any) -> None:
        self.options = [new_labelled_option(option) for option in options]

    def __setitem__(self, key: int, value: Any) -> None:
        return self.options.__setitem__(key, value)

    def __getitem__(self, item: Any) -> Any:
        return self.options.__getitem__(item)

    def __iter__(self) -> Iterator[Any]:
        return self.options.__iter__()


def new_labelled_option(option) -> LabelledOption:
    msg = f"!ProcListLabelled items must be a mapping of (value, label) got {option}"
    assert isinstance(option, dict), msg
    assert 'label' in option, msg
    assert 'value' in option, msg
    return LabelledOption(label=option['label'], value=option['value'])


class LabelledOption(TypedDict):
    label: str
    value: Any


class ProcColor(CustomScalarTag, ProcGenTag):
    tag: str = "ProcColor"

    amount: int

    def __init__(self, amount: int):
        # TODO: Check when amount is higher than the colors available.
        self.amount = int(amount)


class ProcVector3Scaled(CustomMappingTag, ProcGenTag):
    tag: str = "ProcVector3Scaled"

    base: Optional[Vector3]
    scales: list[float]
    labels: Optional[list[str]]

    def __init__(self, scales: list, base: Optional[Vector3] = None, labels: Optional[list[str]] = None):
        self.scales = [float(x) for x in scales]
        self.base = base
        self.labels = labels


class ProcRepeatChoice(CustomMappingTag, ProcGenTag):
    tag: str = "ProcRepeatChoice"

    amount: int
    value: Any

    def __init__(self, amount: int, value: Any):
        self.amount = int(amount)
        self.value = value


class ProcRestrictCombinations(CustomMappingTag, ProcGenTag):
    tag: str = "ProcRestrictCombinations"

    amount: int
    item: Any  # TODO: Rename to value

    def __init__(self, amount: int, item: Any):
        self.amount = int(amount)
        self.item = item


class ProcIf(CustomMappingTag, ProcGenTag):
    tag: str = "ProcIf"

    value: Union[str, list[str]]
    cases: List[Any]
    then: List[Any]
    default: Optional[Any]
    labels: Optional[list[str]]
    default_label: Optional[str]

    def __init__(
            self,
            value: Union[str, list[str]],
            cases: List[Any],
            then: List[Any],
            default: Optional[Any] = None,
            labels: Optional[list[str]] = None,
            default_label: Optional[str] = None):
        self.value = value
        self.cases = cases
        self.then = then
        self.default = default
        self.labels = labels
        self.default_label = default_label

        if len(self.then) != len(self.cases):
            raise errors.NodeAnnotatedProcGenError(
                self, "LengthMismatch",
                f"!ProcIf `cases` and `then` must have the same length. " +
                f"Got `cases` with length {len(self.cases)} and `then` with length {len(self.then)}.")

        if self.labels and len(self.labels) != len(self.cases):
            raise errors.NodeAnnotatedProcGenError(
                self, "LengthMismatch",
                f"!ProcIf `cases` and `labels` must have the same length. " +
                f"Got `cases` with length {len(self.cases)} and `then` with length {len(self.labels)}.")

# ------------ Exceptions ------------


class ProcIfLabels(CustomMappingTag):
    tag: str = "ProcIfLabels"

    value: Union[str, list[str]]
    cases: list[Any]
    labels: list[str]
    default: Optional[str]

    def __init__(self, value: Union[str, list[str]], cases: list[Any], labels: list[str], default: Optional[str] = None):
        self.value = value
        self.cases = cases
        self.labels = labels
        self.default = default

        if self.labels and len(self.labels) != len(self.cases):
            raise errors.NodeAnnotatedProcGenError(
                self, "LengthMismatch",
                f"!ProcIf `cases` and `labels` must have the same length. " +
                f"Got `cases` with length {len(self.cases)} and `then` with length {len(self.labels)}.")


class TemplateMeta():
    """
    Not a tag for (weird?) verbosity reasons.
    """
    proc_labels: list[ProcIfLabels]

    def __init__(self, proc_labels: Optional[list[ProcIfLabels]] = None):
        self.proc_labels = proc_labels or []

    @staticmethod
    def default() -> TemplateMeta:
        return TemplateMeta(proc_labels=[])

    def to_dict(self) -> dict:
        return {
            'proc_labels': self.proc_labels
        }


class Range(CustomSequenceTag):
    tag: str = "R"
    flow_style: str = 'flow'

    min: float
    max: float

    def __init__(self, value: list[float]) -> None:
        self.min = value[0]
        self.max = value[1]
        if len(value) != 2:
            raise ValueError(f"Range !R must have exactly 2 elements, got {len(value)}.")
        if self.min > self.max:
            raise ValueError(f"Range !R minimum {self.min} is greater than maximum {self.max}.")

    def __setitem__(self, key: int, value: Any) -> None:
        if key == 0:
            self.min = value
        elif key == 1:
            self.max = value
        else:
            raise IndexError(f"Index {key} out of range for !R (max length 2)")

    def __getitem__(self, item: Any) -> Any:
        if item == 0:
            return self.min
        elif item == 1:
            return self.max
        else:
            raise IndexError(f"Index {item} out of range for !R (max length 2)")

    def __iter__(self) -> Iterator[Any]:
        return iter([self.min, self.max])
