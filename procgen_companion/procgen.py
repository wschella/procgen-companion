import argparse
import random
import csv
import os
from typing import *
from pathlib import Path
from dataclasses import dataclass

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
    parser.add_argument('--prevent-template-copy', action=argparse.BooleanOptionalAction)
    parser.add_argument('--head', type=int)
    parser.add_argument('--sample', type=int)
    parser.add_argument('-r', '--recursive', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    # Start procgen
    procgen_wrapper(Args(**vars(args)))


@dataclass
class Args:
    path: Path
    max: int
    seed: int
    prevent_template_copy: bool = False
    output: Optional[Path] = None
    head: Optional[int] = None
    sample: Optional[int] = None
    recursive: bool = False


def procgen_wrapper(args: Args):

    if not args.path.exists():
        raise FileNotFoundError(args.path)

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
    random.seed(args.seed)

    # Normal template file
    if not args.path.is_dir():
        procgen(args)

    # If supplied path is a directory, recurse through it
    # TODO: Should be a separate command, we might want to skip files already having variations,
    # delete variations, catch errors, etc.
    else:
        if not args.recursive:
            raise ValueError("Cannot process directories without --recursive")

        for dir, _subdirs, files in os.walk(args.path):
            # Skip *_variations directory, won't contain templates.
            # TODO: Make this configurable in some way
            if dir.endswith("variations"):
                continue
            for template in [Path(dir) / filename for filename in files]:
                print(f"Processing {template}")
                new_args: Dict[str, Any] = vars(args) | {"path": template}

                try:
                    procgen_wrapper(Args(**new_args))
                except Exception as e:
                    e.add_note(f"Template: {template}.")
                    raise e


def procgen(args: Args):
    template: tags.ArenaConfig = yaml.load(args.path.read_text(), Loader=yaml.SafeLoader)
    template_meta = template.get_proc_meta() or tags.TemplateMeta.default()
    template.del_proc_meta()  # We don't want to save this in the output

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
        template.proc_meta = template_meta.to_dict()
        del template.proc_meta
        yaml.dump(template, open(output_dir / "template.yaml", "w"),
                  default_flow_style=False, Dumper=yaml.SafeDumper)

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
        # We need a second pass to fix !ProcIf's and !ProcIfLabels, since they
        # need to access the final variations.
        # We can't use yaml.dump's implicit pass, as id's are already removed from tags then.

        # Fill in !ProcIf's MutablePlaceholders
        def fill_placeholder(node: Any) -> Any:
            if not isinstance(node, util.MutablePlaceholder):
                return True  # Continue walk.
            _value, label = node.fill(variation)
            meta.add_label(label)
            return False  # Stop walking this branch.
        walk_tree(variation, fill_placeholder)

        # Fill in !ProcIfLabels's
        _ = [resolve_proc_if_labels(pil, variation, meta) for pil in template_meta.proc_labels]

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


def resolve_proc_if_labels(pil: tags.ProcIfLabels, variation: Any, meta: Meta):
    assert len(pil.labels) == len(pil.cases)
    variables = pil.value if isinstance(pil.value, list) else [pil.value]
    idx, values = handlers.ConditionResolver.resolve(variables, pil.cases, variation)

    # No matches
    if idx == -1:
        if pil.default is None:
            msg = f"Could not find a matching case for {variables} = {values} in {pil.cases} and there is no default."
            raise ValueError(msg)
        meta.add_label(pil.default)
        return

    meta.add_label(pil.labels[idx])


if __name__ == "__main__":
    run()
