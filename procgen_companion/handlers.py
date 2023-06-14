from typing import *
from abc import ABC, abstractmethod
from copy import deepcopy
from textwrap import dedent
import random
import functools
import operator
import math

import procgen_companion.tags as tags
import procgen_companion.util as util
import procgen_companion.errors as errors
from procgen_companion.meta import Meta

NodeType = TypeVar("NodeType")
OutputType = TypeVar("OutputType")

Recursor = Callable[[Any], Any]
Label = Optional[str]
WithMeta = Tuple[OutputType, Meta]


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
    def sample(node: NodeType, sample: Recursor) -> WithMeta[OutputType]:
        pass

    @staticmethod
    @abstractmethod
    def count(node: NodeType, count: Recursor) -> int:
        pass

    @staticmethod
    @abstractmethod
    def iterate(node: NodeType, iterate: Recursor) -> Iterator[WithMeta[OutputType]]:
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
    Marker subclass.
    """


class ProcGenNodeHandler():
    """
    Marker subclass.
    """


def extract_meta(children: Sequence[Tuple[Any, Meta]]) -> Meta:
    children_metas = [value[1] for value in children]
    variation_meta = Meta()
    for meta in children_metas:
        variation_meta.labels.extend(meta.labels)
    return variation_meta


def extract_children(children: Sequence[Tuple[Any, Meta]]) -> List[Any]:
    """
    Extract children from a list of (child, meta) tuples.
    """
    return list(value[0] for value in children)

############################################################################
# Plain nodes
############################################################################


class PlainSequence(NodeHandler[list, list], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, list)

    @staticmethod
    def sample(node: list, sample: Recursor) -> WithMeta[list]:
        children = [sample(child) for child in node]
        return extract_children(children), extract_meta(children)

    @staticmethod
    def count(node: list, count: Recursor) -> int:
        return Util.count(PlainSequence.children(node), count)

    @staticmethod
    def iterate(node: list, iterate: Recursor) -> Iterator[WithMeta[list]]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)
        extract = lambda variation: (extract_children(variation), extract_meta(variation))
        return map(extract, product_generator)

    @staticmethod
    def children(node: list) -> Any:
        return node


class PlainMapping(NodeHandler[dict, dict], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, dict)

    @staticmethod
    def sample(node: dict, sample: Recursor) -> WithMeta[dict]:
        keys = list(node.keys())
        children = [sample(child) for child in node.values()]
        return dict(zip(keys, extract_children(children))), extract_meta(children)

    @staticmethod
    def count(node: dict, count: Recursor) -> int:
        return Util.count(PlainMapping.children(node), count)

    @staticmethod
    def iterate(node: dict, iterate: Recursor) -> Iterator[WithMeta[dict]]:
        # We get the keys() early so they definitely align with the values().
        keys = list(node.keys())

        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node.values()]

        # Each yield of product_generator is a single variation (but only the dict values).
        product_generator = util.product(*child_iterators)

        extract = lambda variation: (
            dict(zip(keys, extract_children(variation))),
            extract_meta(variation))
        return map(extract, product_generator)

    @staticmethod
    def children(node: dict) -> list[Any]:
        return list(node.values())


YAMLScalar = Union[str, int, float, bool]


class PlainScalar(NodeHandler[YAMLScalar, YAMLScalar], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, (str, int, float, bool))

    @staticmethod
    def sample(node: YAMLScalar, sample: Recursor) -> WithMeta[YAMLScalar]:
        return deepcopy(node), Meta()

    @staticmethod
    def count(node: YAMLScalar, count: Recursor) -> int:
        return 1

    @staticmethod
    def iterate(node: YAMLScalar, iterate: Recursor) -> Iterator[WithMeta[YAMLScalar]]:
        return iter([(deepcopy(node), Meta())])

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
    def sample(node: tags.CustomSequenceTag, sample: Recursor) -> WithMeta[tags.CustomSequenceTag]:
        children = [sample(child) for child in node]
        return type(node)(extract_children(children)), extract_meta(children)

    @staticmethod
    def count(node: tags.CustomSequenceTag, count: Recursor) -> int:
        return Util.count(AnimalAISequence.children(node), count)

    @staticmethod
    def iterate(node: tags.CustomSequenceTag, iterate: Recursor) -> Iterator[WithMeta[tags.CustomSequenceTag]]:
        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node]
        product_generator = util.product(*child_iterators)

        extract = lambda variation: (
            type(node)(extract_children(variation)),
            extract_meta(variation))
        return map(extract, product_generator)

    @staticmethod
    def children(node: tags.CustomSequenceTag) -> list[Any]:
        return list(iter(node))


class AnimalAIMapping(NodeHandler[tags.CustomMappingTag, tags.CustomMappingTag], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomMappingTag)

    @staticmethod
    def sample(node: tags.CustomMappingTag, sample: Recursor) -> WithMeta[tags.CustomMappingTag]:
        keys = list(node.__dict__.keys())
        children = [sample(child) for child in node.__dict__.values()]
        return type(node)(**dict(zip(keys, extract_children(children)))), extract_meta(children)

    @staticmethod
    def count(node: tags.CustomMappingTag, count: Recursor) -> int:
        return Util.count(AnimalAIMapping.children(node), count)

    @staticmethod
    def iterate(node: tags.CustomMappingTag, iterate: Recursor) -> Iterator[WithMeta[tags.CustomMappingTag]]:
        # We get the keys() early so they definitely align with the values().
        keys = list(node.__dict__.keys())

        # We need to force early binding of the child here. https://stackoverflow.com/q/7368522/6182278
        child_iterators = [(lambda c=child: iterate(c)) for child in node.__dict__.values()]

        # Each yield of product_generator is a single variant (but only the dict values).
        product_generator = util.product(*child_iterators)

        extract = lambda variation: (
            type(node)(**dict(zip(keys, extract_children(variation)))),
            extract_meta(variation))
        return map(extract, product_generator)

    @staticmethod
    def children(node: tags.CustomMappingTag) -> list[Any]:
        return list(node.__dict__.values())


class AnimalAIScalar(NodeHandler[tags.CustomScalarTag, tags.CustomScalarTag], StaticNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.AnimalAITag) and isinstance(node, tags.CustomScalarTag)

    @staticmethod
    def sample(node: tags.CustomScalarTag, sample: Recursor) -> WithMeta[tags.CustomScalarTag]:
        return deepcopy(node), Meta()

    @staticmethod
    def count(node: tags.CustomScalarTag, count: Recursor) -> int:
        return 1

    @staticmethod
    def iterate(node: tags.CustomScalarTag, iterate: Recursor) -> Iterator[WithMeta[tags.CustomScalarTag]]:
        return iter([(deepcopy(node), Meta())])

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
    def sample(node: tags.ProcList, sample: Recursor) -> WithMeta[Any]:
        return deepcopy(random.choice(node.options)), Meta()

    @staticmethod
    def count(node: tags.ProcList, count: Recursor) -> int:
        return len(node.options)

    @staticmethod
    def iterate(node: tags.ProcList, iterate: Recursor) -> Iterator[Tuple[Any, Meta]]:
        return ((deepcopy(option), Meta()) for option in node.options)

    @staticmethod
    def children(node: tags.ProcList) -> list[Any]:
        return node.options


class ProcListLabelled(NodeHandler[tags.ProcListLabelled, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcListLabelled)

    @staticmethod
    def sample(node: tags.ProcListLabelled, sample: Recursor) -> WithMeta[Any]:
        option: tags.LabelledOption = deepcopy(random.choice(node.options))
        return option["value"], Meta(labels=[option["label"]])

    @staticmethod
    def count(node: tags.ProcListLabelled, count: Recursor) -> int:
        return len(node.options)

    @staticmethod
    def iterate(node: tags.ProcListLabelled, iterate: Recursor) -> Iterator[WithMeta[Any]]:
        return ((deepcopy(option["value"]), Meta(labels=[deepcopy(option["label"])])) for option in node.options)

    @staticmethod
    def children(node: tags.ProcListLabelled) -> list[Any]:
        return node.options


class ProcColor(NodeHandler[tags.ProcColor, tags.RGB], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcColor)

    @staticmethod
    def sample(node: tags.ProcColor, sample: Recursor) -> WithMeta[tags.RGB]:
        return to_rgb(deepcopy(random.choice(util.COLORS))), Meta()

    @staticmethod
    def count(node: tags.ProcColor, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcColor, iterate: Recursor) -> Iterator[WithMeta[tags.RGB]]:
        generator = (to_rgb(deepcopy(color)) for color in util.COLORS)
        return map(lambda v: (v, Meta()), generator)

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
    def sample(node: tags.ProcVector3Scaled, sample: Recursor) -> WithMeta[tags.Vector3]:
        base = deepcopy(node.base) if node.base is not None else tags.Vector3(x=1, y=1, z=1)
        scale_idx = random.randint(0, len(node.scales) - 1)
        scale = node.scales[scale_idx]

        if node.labels is None:
            return scale_vector3(base, scale), Meta()

        assert (len(node.labels) == len(node.scales)), "Labels and scales must be the same length."
        meta = Meta(labels=[node.labels[scale_idx]])
        return scale_vector3(base, scale), meta

    @staticmethod
    def count(node: tags.ProcVector3Scaled, count: Recursor) -> int:
        return len(node.scales)

    @staticmethod
    def iterate(node: tags.ProcVector3Scaled, iterate: Recursor) -> Iterator[WithMeta[tags.Vector3]]:
        base = node.base if node.base is not None else tags.Vector3(x=1, y=1, z=1)
        generator = (scale_vector3(deepcopy(base), scale) for scale in node.scales)

        if node.labels is None:
            return zip(generator, (Meta() for _ in node.scales))

        assert (len(node.labels) == len(node.scales)), "Labels and scales must be the same length."
        return zip(generator, (Meta(labels=[label]) for label in node.labels))

    @staticmethod
    def children(node: tags.ProcVector3Scaled) -> list[Any]:
        base = [node.base] if node.base is not None else []
        return [base] + node.scales


def scale_vector3(vector: tags.Vector3, scale: float) -> tags.Vector3:
    return tags.Vector3(x=vector.x * scale, y=vector.y * scale, z=vector.z * scale)


class ProcRepeatChoice(NodeHandler[tags.ProcRepeatChoice, List[Any]], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRepeatChoice)

    @staticmethod
    def sample(node: tags.ProcRepeatChoice, sample: Recursor) -> WithMeta[List[Any]]:
        choice, meta = sample(node.value)
        return [choice] + [deepcopy(choice) for _ in range(node.amount - 1)], meta

    @staticmethod
    def count(node: tags.ProcRepeatChoice, count: Recursor) -> int:
        return count(node.value)

    @staticmethod
    def iterate(node: tags.ProcRepeatChoice, iterate: Recursor) -> Iterator[Tuple[Any, Meta]]:
        duplicate = lambda var: [var] + [deepcopy(var) for _ in range(node.amount - 1)]
        return ((duplicate(var), meta) for var, meta in iterate(node.value))

    @staticmethod
    def children(node: tags.ProcRepeatChoice) -> list[Any]:
        return [node.amount, node.value]


class ProcRestrictCombinations(NodeHandler[tags.ProcRestrictCombinations, Any], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcRestrictCombinations)

    @staticmethod
    def sample(node: tags.ProcRestrictCombinations, sample: Recursor) -> WithMeta[Any]:
        return sample(node.item)

    @staticmethod
    def count(node: tags.ProcRestrictCombinations, count: Recursor) -> int:
        return node.amount

    @staticmethod
    def iterate(node: tags.ProcRestrictCombinations, iterate: Recursor) -> Iterator[WithMeta[Any]]:
        # This implementation could take the first 'amount' variations...
        # item_iter = iterate(node.item)
        # return (next(item_iter) for _ in range(node.amount))

        # ... but we want to sample instead, as that result in a wider selection of variations.
        from procgen_companion.core import sample_recursive
        return (sample_recursive(node.item) for _ in range(node.amount))

    @staticmethod
    def children(node: tags.ProcRestrictCombinations) -> list[Any]:
        return [node.amount, node.item]


class ProcIf(NodeHandler[tags.ProcIf, util.MutablePlaceholder], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcIf)

    @staticmethod
    def sample(node: tags.ProcIf, sample: Recursor) -> WithMeta[util.MutablePlaceholder]:
        proc_if = lambda root: ProcIf.__resolve_condition(node, root)
        return util.MutablePlaceholder(proc_if), Meta()  # Meta gets filled in second pass.

    @staticmethod
    def count(node: tags.ProcIf, count: Recursor) -> int:
        # !ProcIf does not increase the number of variations.
        # It only sets some values in existing ones.
        return 1

    @staticmethod
    def iterate(node: tags.ProcIf, iterate: Recursor) -> Iterator[WithMeta[util.MutablePlaceholder]]:
        proc_if = lambda root: ProcIf.__resolve_condition(node, root)
        placeholder = util.MutablePlaceholder(proc_if)
        return iter([(placeholder, Meta())])

    @staticmethod
    def children(node: tags.ProcIf) -> list[Any]:
        default = [node.default] if node.default is not None else []
        return [node.value, node.cases, node.then, default]

    @staticmethod
    def __resolve_condition(node: tags.ProcIf, root: Any) -> Tuple[Any, Label]:
        variables = node.value if isinstance(node.value, list) else [node.value]
        labels: list[Any] = node.labels if node.labels else [cast(str, None)] * len(node.cases)
        assert (len(labels) == len(node.cases)), "Labels and cases must be the same length."

        idx, values = ConditionResolver.resolve(variables, node.cases, root)
        if idx == -1:
            # Recast value as given (list or scalar) to avoid confusion.
            values = values if isinstance(node.value, list) else values[0]
            if node.default is None:
                raise errors.NodeAnnotatedProcGenError(
                    node, "MissingCase",
                    f"Could not find a matching case for {node.value} = {values} in `cases` " +
                    f"and there is no default.")
            if node.labels is not None and node.default_label is None:
                raise errors.NodeAnnotatedProcGenError(
                    node, "MissingCase",
                    f"Could not find a matching case for {node.value} = {values} in `cases` " +
                    f"and there is no default label.")

            # Happy path with defaults
            return node.default, node.default_label

        return node.then[idx], labels[idx]


class ProcIfLabels(NodeHandler[tags.ProcIfLabels, util.MutablePlaceholder], ProcGenNodeHandler):
    @staticmethod
    def can_handle(node: Any) -> bool:
        return isinstance(node, tags.ProcIfLabels)

    @staticmethod
    def count(node: tags.ProcIfLabels, count: Recursor) -> int:
        return 1

    @staticmethod
    def sample(node: tags.ProcIfLabels, sample: Recursor) -> WithMeta[util.MutablePlaceholder]:
        raise ValueError(".sample should not be called on ProcIfLabels.")

    @staticmethod
    def iterate(node: tags.ProcIfLabels, iterate: Recursor) -> Iterator[WithMeta[util.MutablePlaceholder]]:
        raise ValueError(".iterate should not be called on ProcIfLabels.")

    @staticmethod
    def children(node: tags.ProcIfLabels) -> list[Any]:
        default = [node.default] if node.default is not None else []
        return [node.value, node.cases, default]

    @staticmethod
    def resolve(node: tags.ProcIfLabels, variation: Any, meta: Meta) -> None:
        assert len(node.labels) == len(node.cases), \
            f"!ProcIfLabels has a different number of cases ({len(node.cases)}) vs. labels ({len(node.labels)}). They should be equal."
        variables = node.value if isinstance(node.value, list) else [node.value]
        idx, values = ConditionResolver.resolve(variables, node.cases, variation)

        # No matches
        if idx == -1:
            if node.default is None:
                raise errors.NodeAnnotatedProcGenError(
                    node, "MissingCase",
                    f"Could not find a matching case for {node.value} = {values} in `cases` " +
                    f"and there is no default.")
            meta.add_label(node.default)
            return

        meta.add_label(node.labels[idx])


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
    ProcIfLabels,
]


def get_node_handler(node: Any) -> Type[NodeHandler]:
    for handler in HANDLERS:
        if handler.can_handle(node):
            return handler
    raise ValueError(f"Could not find a node class for {node}")


class ConditionResolver():
    @staticmethod
    def resolve(variables: list[str], cases: List[Union[Any, tags.Range]], root: Any) -> Tuple[int, list[Any]]:
        values = [ConditionResolver.__find_variable(variable, root) for variable in variables]

        for idx, case in enumerate(cases):
            case = case if isinstance(case, list) else [case]
            if len(case) != len(values):
                msg = dedent(f"""
                Length of case {idx+1} is {len(case)} and does not match with length {len(variables)} of variables.
                Case {idx+1}: {case}
                Variables: {variables}
                """)
                raise ValueError(msg)

            if all(ConditionResolver.__matches(v1, v2) for v1, v2 in zip(values, case)):
                return idx, values

        return -1, values

    @staticmethod
    def __find_variable(variable: str, root: Any) -> Any:
        item_id, *path_ = variable.split(".")
        item = ConditionResolver.__find_item(item_id, root)
        if item is None:
            raise errors.BaseProcGenError(
                "IDNotFound",
                f"Could not find an Item with id '{item_id}', but it is need for a variable ({variable}).\n" +
                f"Did you forget to specify the id in the corresponding Item?")

        # Deal with list indices
        path = [int(key) if key.isdigit() else key for key in path_]

        # All custom tags implement __getitem__, as do dicts and list, as do MutablePlaceholders.
        # Scalars and misspellings will raise an exception that we catch for better error messages.
        try:
            value = item
            for key in path:
                value = value[key]
                if isinstance(value, util.MutablePlaceholder) and not value.is_filled():
                    # When a !ProcIf refers to another !ProcIf, it might not be filled yet when resolving this condition.
                    value.fill(root)
        except Exception as e:
            raise errors.BaseProcGenError(
                "NonExistentVariable",
                f"Could not find variable '{variable}' in Item '{item_id}', " +
                f"but it is referred to in some place (e.g. a !ProcIf).")

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
        generator = (ConditionResolver.__find_item(item_id, child) for child in children)
        return next((node for node in generator if node is not None), None)
