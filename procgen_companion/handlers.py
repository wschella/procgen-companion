from typing import *
from abc import ABC, abstractmethod
from copy import deepcopy
import random
import functools
import operator
import math

import procgen_companion.tags as tags
import procgen_companion.util as util
import procgen_companion.meta as meta

NodeType = TypeVar("NodeType")
OutputType = TypeVar("OutputType")

Recursor = Callable[[Any], Any]
Label = Optional[str]


class NodeHandler(ABC, Generic[NodeType, OutputType]):
    """
    Singletons. Only bundle logic.
    TODO: Check out ABC / Interface
    """

    @staticmethod
    @abstractmethod
    def can_handle(node: Any) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def sample(node: NodeType, sample: Recursor) -> Tuple[OutputType, Label]:
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
    @abstractmethod
    def children(node: NodeType) -> List[Any]:
        pass


class Util():
    @staticmethod
    def count(children: Iterable[Any], count: Recursor) -> int:
        child_counts = [count(child) for child in children]
        return functools.reduce(operator.mul, child_counts, 1)


class StaticNodeHandler():
    """
    Marker subclass with extra methods for static nodes.
    """


class ProcGenNodeHandler():
    """
    Marker subclass.
    """

############################################################################
# Plain nodes
############################################################################


class PlainSequence(NodeHandler[list, list], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, list)

    @staticmethod
    def sample(node: list, sample: Recursor) -> Tuple[list, Label]:
        return [sample(child) for child in node], None

    @staticmethod
    def count(node: list, count: Recursor) -> int:
        return Util.count(PlainSequence.children(node), count)

    @staticmethod
    def iterate(node: list, iterate: Recursor) -> Iterator[list]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)
        return (list(variant) for variant in product_generator)

    @staticmethod
    def children(node: list) -> Any:
        return node


class PlainMapping(NodeHandler[dict, dict], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, dict)

    @staticmethod
    def sample(node: dict, sample: Recursor) -> Tuple[dict, Label]:
        return {k: sample(v) for k, v in node.items()}, None

    @staticmethod
    def count(node: dict, count: Recursor) -> int:
        return Util.count(PlainMapping.children(node), count)

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


class PlainScalar(NodeHandler[YAMLScalar, YAMLScalar], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, (str, int, float, bool))

    @staticmethod
    def sample(node: YAMLScalar, sample: Recursor) -> Tuple[YAMLScalar, Label]:
        return deepcopy(node), None

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


class AnimalAISequence(NodeHandler[tags.CustomSequenceTag, tags.CustomSequenceTag], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomSequenceTag)

    @staticmethod
    def sample(node: tags.CustomSequenceTag, sample: Recursor) -> Tuple[tags.CustomSequenceTag, None]:
        values = [sample(child) for child in node]
        return type(node)(values), None

    @staticmethod
    def count(node: tags.CustomSequenceTag, count: Recursor) -> int:
        return Util.count(AnimalAISequence.children(node), count)

    @staticmethod
    def iterate(node: tags.CustomSequenceTag, iterate: Recursor) -> Iterator[tags.CustomSequenceTag]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)
        return (type(node)(list(variant)) for variant in product_generator)

    @staticmethod
    def children(node: tags.CustomSequenceTag) -> list[Any]:
        return list(iter(node))


class AnimalAIMapping(NodeHandler[tags.CustomMappingTag, tags.CustomMappingTag], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomMappingTag)

    @staticmethod
    def sample(node: tags.CustomMappingTag, sample: Recursor) -> Tuple[tags.CustomMappingTag, None]:
        kvs = {k: sample(v) for k, v in node.__dict__.items()}
        return type(node)(**kvs), None

    @staticmethod
    def count(node: tags.CustomMappingTag, count: Recursor) -> int:
        return Util.count(AnimalAIMapping.children(node), count)

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


class AnimalAIScalar(NodeHandler[tags.CustomScalarTag, tags.CustomScalarTag], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomScalarTag)

    @staticmethod
    def sample(node: tags.CustomScalarTag, sample: Recursor) -> Tuple[tags.CustomScalarTag, Label]:
        return deepcopy(node), None

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


class ProcList(NodeHandler[tags.ProcList, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcList)

    @staticmethod
    def sample(node: tags.ProcList, sample: Recursor) -> Tuple[Any, Label]:
        return deepcopy(random.choice(node.options))

    @staticmethod
    def count(node: tags.ProcList, count: Recursor) -> int:
        return len(node.options)

    @staticmethod
    def iterate(node: tags.ProcList, iterate: Recursor) -> Iterator[Any]:
        return (deepcopy(option) for option in node.options)

    @staticmethod
    def children(node: tags.ProcList) -> list[Any]:
        return list(node.options)


class ProcListLabelled(NodeHandler[tags.ProcListLabelled, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcListLabelled)

    @staticmethod
    def sample(node: tags.ProcListLabelled, sample: Recursor) -> Tuple[Any, Label]:
        option = deepcopy(random.choice(node.options))
        return option.value, option.label

    @staticmethod
    def count(node: tags.ProcListLabelled, count: Recursor) -> int:
        return len(node.options)

    @staticmethod
    def iterate(node: tags.ProcListLabelled, iterate: Recursor) -> Iterator[Any]:
        return (deepcopy(option.value) for option in node.options)

    @staticmethod
    def children(node: tags.ProcListLabelled) -> list[Any]:
        return list(node.options)


class ProcColor(NodeHandler[tags.ProcColor, tags.RGB], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcColor)

    @staticmethod
    def sample(node: tags.ProcColor, sample: Recursor) -> Tuple[tags.RGB, Label]:
        return to_rgb(deepcopy(random.choice(util.COLORS))), None

    @staticmethod
    def count(node: tags.ProcColor, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcColor, iterate: Recursor) -> Iterator[tags.RGB]:
        return iter([to_rgb(deepcopy(c)) for c in util.COLORS[:node.amount]])

    @staticmethod
    def children(node: tags.ProcColor) -> list[Any]:
        return [node.amount]


def to_rgb(color: Tuple[int, int, int]) -> tags.RGB:
    return tags.RGB(r=color[0], g=color[1], b=color[2])


class ProcVector3Scaled(NodeHandler[tags.ProcVector3Scaled, tags.Vector3], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcVector3Scaled)

    @staticmethod
    def sample(node: tags.ProcVector3Scaled, sample: Recursor) -> Tuple[tags.Vector3, Label]:
        base = deepcopy(node.base) if node.base is not None else tags.Vector3(x=0, y=0, z=0)
        scale_idx = random.randint(0, len(node.scales) - 1)
        scale = node.scales[scale_idx]
        if node.labels is None:
            return scale_vector3(base, scale), None

        assert (len(node.labels) == len(node.scales)), "Labels and scales must be the same length."
        return scale_vector3(base, scale), node.labels[scale_idx]

    @staticmethod
    def count(node: tags.ProcVector3Scaled, count: Recursor) -> int:
        return len(node.scales)

    @staticmethod
    def iterate(node: tags.ProcVector3Scaled, iterate: Recursor) -> Iterator[tags.Vector3]:
        base = node.base if node.base is not None else tags.Vector3(x=0, y=0, z=0)
        return iter([scale_vector3(deepcopy(base), scale) for scale in node.scales])

    @staticmethod
    def children(node: tags.ProcVector3Scaled) -> list[Any]:
        base = [node.base] if node.base is not None else []
        return [base] + node.scales


def scale_vector3(vector: tags.Vector3, scale: float) -> tags.Vector3:
    return tags.Vector3(x=vector.x * scale, y=vector.y * scale, z=vector.z * scale)


class ProcRepeatChoice(NodeHandler[tags.ProcRepeatChoice, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRepeatChoice)

    @staticmethod
    def sample(node: tags.ProcRepeatChoice, sample: Recursor) -> Tuple[Any, Label]:
        choice = sample(node.value)
        return [choice] + [deepcopy(choice) for _ in range(node.amount - 1)], None

    @staticmethod
    def count(node: tags.ProcRepeatChoice, count: Recursor) -> int:
        return count(node.value)

    @staticmethod
    def iterate(node: tags.ProcRepeatChoice, iterate: Recursor) -> Iterator[Any]:
        duplicate = lambda var: [var] + [deepcopy(var) for _ in range(node.amount - 1)]
        return (duplicate(var) for var in iterate(node.value))

    @staticmethod
    def children(node: tags.ProcRepeatChoice) -> list[Any]:
        return [node.amount, node.value]


class ProcRestrictCombinations(NodeHandler[tags.ProcRestrictCombinations, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRestrictCombinations)

    @staticmethod
    def sample(node: tags.ProcRestrictCombinations, sample: Recursor) -> Tuple[Any, Label]:
        return sample(node.item), None

    @staticmethod
    def count(node: tags.ProcRestrictCombinations, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcRestrictCombinations, iterate: Recursor) -> Iterator[Any]:
        # This implementation would take the first amount of variations...
        # item_iter = iterate(node.item)
        # return (next(item_iter) for _ in range(node.amount))

        # ... but we want to sample instead, as that result in a wider selection of variations.
        # TODO: Check if this is correct.
        from procgen_companion.procgen import sample_recursive
        return (sample_recursive(node.item, meta.Meta()) for _ in range(node.amount))

    @staticmethod
    def children(node: tags.ProcRestrictCombinations) -> list[Any]:
        return [node.amount, node.item]


class ProcIf(NodeHandler[tags.ProcIf, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcIf)

    @staticmethod
    def sample(node: tags.ProcIf, sample: Recursor) -> Tuple[util.MutablePlaceholder, Label]:
        proc_if = lambda root: ProcIf.__resolve_condition(node, root)
        return util.MutablePlaceholder(proc_if), None

    @staticmethod
    def count(node: tags.ProcIf, count: Recursor) -> int:
        # !ProcIf does not increase the number of variations.
        # It only sets some values in existing ones.
        return 1

    @staticmethod
    def iterate(node: tags.ProcIf, iterate: Recursor) -> Iterator[Any]:
        # TODO: Remove if implement labelling for iteration.
        proc_if = lambda root: ProcIf.__resolve_condition(node, root)[0]
        placeholder = util.MutablePlaceholder(proc_if)
        return iter([placeholder])

    @staticmethod
    def children(node: tags.ProcIf) -> list[Any]:
        default = [node.default] if node.default is not None else []
        return [node.variable, node.cases, node.then, default]

    @staticmethod
    def __resolve_condition(node: tags.ProcIf, root: Any) -> Tuple[Any, Label]:
        variables = node.variable if isinstance(node.variable, list) else [node.variable]
        values = [ProcIf.__find_variable(variable, root) for variable in variables]
        labels: list[Any] = node.labels if node.labels else [cast(str, None)] * len(node.cases)
        assert (len(labels) == len(node.cases)), "Labels and cases must be the same length."

        for idx, (case, then, label) in enumerate(zip(node.cases, node.then, labels)):
            case = case if isinstance(case, list) else [case]
            if len(case) != len(values):
                msg = f"Length of case {idx} {case} does not match with variables {variables}."
                raise ValueError(msg)

            if all(ProcIf.__matches(v1, v2) for v1, v2 in zip(values, case)):
                return then, label

        if node.default is not None:
            return node.default, node.default_label

        raise ValueError(f"Could not find a matching case for {values} in {node.variable}")

    @staticmethod
    def __find_variable(variable: str, root: Any) -> Any:
        item_id, *path_ = variable.split(".")
        item = ProcIf.__find_item(item_id, root)
        if item is None:
            raise ValueError(f"Could not find item with id {item_id}.")

        # Deal with list indices
        path = [int(key) if key.isdigit() else key for key in path_]

        # All custom tags implement __getitem__, as do dicts and list.
        # Scalars will raise an exception.
        value = item
        for key in path:
            value = value[key]
        return value

    @staticmethod
    def __matches(v_var: Any, v_case: Any) -> bool:
        if isinstance(v_case, tags.Range):
            return v_case.min <= v_var <= v_case.max
        if isinstance(v_case, (int, float)):
            return math.isclose(v_var, v_case)
        return v_var == v_case

    @staticmethod
    def __find_item(item_id: str, node: Any) -> Optional[Any]:
        """
        Only custom AnimalAI mapping tags can have an id.
        """

        if isinstance(node, tags.AnimalAITag) and isinstance(node, tags.WithId):
            if node.get_id() == item_id:
                return node

        # If not an AnimalAI tag it can't have an id (previous conditions).
        # If not an AnimalAI tag, but still a custom tag,
        # ... its children can't have an id either (!Proc tags, special cases such as !R).
        if not isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomTag):
            return None

        # These are exactly the ones we're trying to resolve now. They can't depend on each other.
        if isinstance(node, util.MutablePlaceholder):
            return None

        # Guaranteed static node now (no !Proc tags)
        handler = get_node_handler(node)
        children = handler.children(cast(Any, node))
        return next((node for child in children if (node := ProcIf.__find_item(item_id, child)) is not None), None)


HANDLERS: List[Type[NodeHandler]] = [
    PlainSequence,
    PlainMapping,
    PlainScalar,
    AnimalAIScalar,
    AnimalAIMapping,
    AnimalAISequence,
    ProcList,
    ProcListLabelled,
    ProcColor,
    ProcVector3Scaled,
    ProcRepeatChoice,
    ProcRestrictCombinations,
    ProcIf,
]


def get_node_handler(node: Any) -> Type[NodeHandler]:
    for handler in HANDLERS:
        if handler.can_handle(node):
            return handler
    raise ValueError(f"Could not find a node class for {node}")
