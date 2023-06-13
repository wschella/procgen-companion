import random
from typing import *
from pathlib import Path

import yaml

import procgen_companion.tags as tags
import procgen_companion.handlers as handlers
import procgen_companion.util as util
from procgen_companion.meta import Meta


def init(seed: int):
    # Add constructors and representers for the custom YAML tags
    for tag in tags.GET_ANIMAL_AI_TAGS() + tags.GET_PROC_GEN_TAGS() + tags.GET_SPECIAL_TAGS():
        tag_name: str = f"!{tag.tag}"  # type: ignore
        yaml.SafeLoader.add_constructor(tag_name, tag.construct)
        yaml.SafeDumper.add_representer(tag, tag.represent)  # type: ignore

    # Add custom representer for MutablePlaceholder
    yaml.SafeDumper.add_representer(
        util.MutablePlaceholder, util.MutablePlaceholder.represent)  # type: ignore

    # Add custom list representer for collapsing lists of scalars
    yaml.SafeDumper.add_representer(list, util.custom_list_representer)

    # Set Python random seed for hopefully deterministic generation
    random.seed(seed)


def read(path: Path) -> tags.ArenaConfig:
    return yaml.load(path.read_text(), Loader=yaml.SafeLoader)


def generate(
    mode: Literal['sample', 'exhaustive'],
    template: tags.ArenaConfig,
    amount: int,
):
    # Design notes:
    # - The ProcIf needs acces to the global state
    # - Tags in filenames probably need to update some global state?
    # - There are leaf nodes & non-leaf nodes
    # - There are YAML mappings, list, and scalars.
    #   - These are represented as pure Python objects.
    #   - They can still contain, AnimalAI tags or ProcGen tags inside.
    # - There are AnimalAI tags
    #   - These get parsed into the custom tags we have defined.
    # - There are ProcGen tags.
    # - We need following functionalities with possibly different behaviour per node:
    #   - Counting the number of variations
    #   - Iterating through variations in order
    #   - Sampling a random variation
    #   - Returning a list of children
    # - Python product consumes the full iterable before returning the first element.

    template_meta = template.get_proc_meta() or tags.TemplateMeta.default()
    template.del_proc_meta()  # We don't want to save this in the output

    if mode == 'sample':
        variations = (sample_recursive(template) for _ in range(amount))
    elif mode == 'exhaustive':
        full_iterator = iterate_variations_recursive(template)
        variations = (next(full_iterator) for _ in range(amount))
    else:
        raise ValueError(f"Programmer Error: Unknown mode `{mode}`")

    # Generate all requested variations

    for (variation, meta) in variations:
        # We need a second pass to fix !ProcIf's and !ProcIfLabels, since they
        # need to access the final variations.
        # We can't use yaml.dump's implicit pass, as id's are already removed from tags then.

        # Fill in !ProcIf's MutablePlaceholders
        def fill_placeholder(node: Any) -> Any:
            if not isinstance(node, util.MutablePlaceholder):
                return True  # Continue walk.

            if node.is_filled():
                # This can occur when a !ProcIf refers to another !ProcIf
                # which causes the dependencies to already be filled.
                _value, label = node.value, node.label
            else:
                _value, label = node.fill(variation)

            meta.add_label(label)
            return False  # Stop walking this branch.
        walk_tree(variation, fill_placeholder)

        # Fill in !ProcIfLabels's
        _ = [handlers.ProcIfLabels.resolve(pil, variation, meta)
             for pil in template_meta.proc_labels]

        yield variation, meta


def iterate_variations_recursive(node: Any) -> Iterator[Tuple[Any, Meta]]:
    handler = handlers.get_node_handler(node)
    return handler.iterate(node, iterate_variations_recursive)


def sample_recursive(node: Any) -> Tuple[Any, Meta]:
    handler = handlers.get_node_handler(node)
    return handler.sample(node, sample_recursive)


def count_recursive(node: Any):
    handler = handlers.get_node_handler(node)
    return handler.count(node, count_recursive)


def explain_count_recursive(node: Any):
    exp = _explain_count_recursive(node)
    if exp == "":
        return "No variations"
    return exp


def _explain_count_recursive(node: Any):
    """
    Generate a string explaining where the number of variations comes from.
    For example output is: 6#ProcList x 5#ProcColor x 4#ProcVector3Scaled,
    which generates 6 * 5 * 4 = 120 variations.
    """
    handler = handlers.get_node_handler(node)
    if issubclass(handler, handlers.StaticNodeHandler):
        children = handler.children(node)
        explanations = [_explain_count_recursive(child) for child in children]
        return " x ".join(explanation for explanation in explanations if explanation)
    elif issubclass(handler, handlers.ProcGenNodeHandler):
        if issubclass(handler, (handlers.ProcIf, handlers.ProcIfLabels)):
            return ""
        return f"{handler.count(node, count_recursive)}#{node.tag}"
    else:
        raise TypeError(f"Programmer error. Unknown type {type(handler)} {handler}.")


def walk_tree(node: Any, callback: Callable[[Any], bool]):
    """
    Recursively walk the tree, calling the callback on each node.
    """
    continue_ = callback(node)
    if continue_:
        handler = handlers.get_node_handler(node)
        util.consume(walk_tree(child, callback) for child in handler.children(node))
