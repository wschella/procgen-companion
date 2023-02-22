import argparse
import random
import csv
from typing import *
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy

import yaml
import tqdm

import procgen_companion.tags as tags
import procgen_companion.handlers as handlers
import procgen_companion.util as util
from procgen_companion.meta import Meta


def run():
    # Read arguments
    parser = argparse.ArgumentParser(
        prog="procgen-companion",
        description="Procedurally generate variations of an AnimalAI task definition based on a template file."
    )
    parser.add_argument('path', type=Path)
    parser.add_argument('-m', '--max', type=int, default=10000)
    parser.add_argument('-s', '--seed', type=int, default=1234)
    parser.add_argument('-o', '--output', type=Path)
    parser.add_argument('--prevent-template-copy', type=bool, default=False)
    parser.add_argument('--head', type=int)
    parser.add_argument('--sample', type=int)
    args = parser.parse_args()

    # Start procgen
    procgen(Args(**vars(args)))


@dataclass
class Args:
    path: Path
    max: int
    seed: int
    prevent_template_copy: bool = False
    output: Optional[Path] = None
    head: Optional[int] = None
    sample: Optional[int] = None


def procgen(args: Args):

    if not args.path.exists():
        raise FileNotFoundError(args.path)

    # Add constructors and representers for the custom YAML tags
    for tag in tags.GET_ANIMAL_AI_TAGS() + tags.GET_PROC_GEN_TAGS():
        tag_name: str = f"!{tag.tag}"  # type: ignore
        yaml.SafeLoader.add_constructor(tag_name, tag.construct)
        yaml.SafeDumper.add_representer(tag, tag.represent)  # type: ignore

    # Add custom representer for MutablePlaceholder
    yaml.SafeDumper.add_representer(
        util.MutablePlaceholder, util.MutablePlaceholder.represent)  # type: ignore

    # Add custom list representer for collapsing lists of scalars
    yaml.SafeDumper.add_representer(list, util.custom_list_representer)

    # Set Python random seed for hopefully deterministic generation
    random.seed(args.seed)

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

    template: tags.ArenaConfig = yaml.load(args.path.read_text(), Loader=yaml.SafeLoader)

    n_variations = count_recursive(template)
    print(f"Total possible variations: {n_variations}")
    print(explain_count_recursive(template))

    if n_variations > args.max and (args.sample is None and args.head is None):
        print(f"Too many variations. Stopping. "
              f"The total number of possible variations is {n_variations}, "
              f"while the maximum is {args.max}. "
              f"Try reducing choices, increasing --max, or using --head.")
        print(explain_count_recursive(template))
        return

    # Prepare output directory
    output_dir = Path(f"tmp/{args.path.stem}_variations/") if args.output is None else args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy the template to the output directory
    if not args.prevent_template_copy:
        yaml.dump(template, open(output_dir / "template.yaml", "w"),
                  default_flow_style=False, Dumper=yaml.SafeDumper)

    # Sample or iterate over all possible variations
    if args.sample is not None:
        assert args.head is None, "Cannot use both --head and --sample"
        amount = min(n_variations, args.sample, args.max)
        iterator = (sample_recursive(template) for _ in range(amount))
    else:
        head = args.head if args.head is not None else n_variations
        amount = min(n_variations, head, args.max)
        # full_iterator = iterate_variations_recursive_root(template)
        full_iterator = iterate_variations_recursive(template)
        iterator = (next(full_iterator) for _ in range(amount))

    # Generate all requested variations
    meta_file = open(output_dir / "meta.csv", "w")
    for i, (variation, meta) in tqdm.tqdm(enumerate(iterator), total=amount):
        # We need a second pass to fix !ProcIf's, as they need to access the final variations.
        # We can't use yaml.dump's implicit pass, as id's are already removed from tags then.

        def fill_placeholder(node: Any) -> Any:
            if not isinstance(node, util.MutablePlaceholder):
                return True  # Continue walk.
            _value, label = node.fill(variation)
            meta.add_label(label)
            return False  # Stop walking this branch.
        walk_tree(variation, fill_placeholder)

        # TODO: We could only have the MutablePlaceholder have 1 lambda by overriding deepcopy behaviour.
        # we can populate it at the same time as we populate the dict of variables.
        # Should review all deepcopy behaviour? don't know if yaml.dump mutates anything tho.
        # We shouldn't optimise too early tho. Likely bottlenecked by OS file creation anyway.

        # Save variation to file
        labels = f"_{'_'.join(meta.labels)}" if meta.labels else ""
        filename = f"{args.path.stem}_{i+1:05d}{labels}.yaml"
        csv.writer(meta_file).writerow([filename] + meta.labels)
        with open(output_dir / filename, "w") as f:
            yaml.dump(variation, f, default_flow_style=False, Dumper=yaml.SafeDumper)

    meta_file.close()


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
    """
    Generate a string explaining where the number of variations comes from.
    For example output is: 6#ProcList x 5#ProcColor x 4#ProcVector3Scaled,
    which generates 6 * 5 * 4 = 120 variations.
    """
    handler = handlers.get_node_handler(node)
    if issubclass(handler, handlers.StaticNodeHandler):
        children = handler.children(node)
        explanations = [explain_count_recursive(child) for child in children]
        return " x ".join(explanation for explanation in explanations if explanation)
    elif issubclass(handler, handlers.ProcGenNodeHandler):
        if issubclass(handler, handlers.ProcIf):
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


if __name__ == "__main__":
    run()
