from typing import *
from pathlib import Path
from dataclasses import dataclass
import argparse
import functools
import operator
import random
from copy import deepcopy

import yaml

import procgen_companion.tags as tags
import procgen_companion.util as util


def run():
    # Read arguments
    parser = argparse.ArgumentParser(
        prog="procgen-companion",
        description="Procedurally generate variations of an AnimalAI task definition based on a template file."
    )
    parser.add_argument('file_path', type=Path)
    parser.add_argument('-t', '--template-path', type=Path)
    parser.add_argument('-m', '--max', type=int, default=10000)
    parser.add_argument('-s', '--seed', type=int, default=1234)
    args = parser.parse_args()

    # Start procgen
    procgen(Args(**vars(args)))


@dataclass
class Args:
    file_path: Path
    template_path: Optional[Path]
    max: int
    seed: int


def procgen(args: Args):

    # Handle faulty paths explicitly
    if not args.file_path.exists():
        raise FileNotFoundError(args.file_path)
    if args.template_path is not None and not args.template_path.exists():
        raise FileNotFoundError(args.template_path)

    # Look for template file with the same name as the default
    template_path = args.template_path or args.file_path.with_suffix(".template.yaml")
    if not template_path.exists():
        print("Could not find a corresponding .template.yaml file")
        raise FileNotFoundError(template_path)

    # Add constructors and representers for the custom YAML tags
    for tag in tags.GET_ANIMAL_AI_TAGS() + tags.GET_PROC_GEN_TAGS():
        tag_name: str = f"!{tag.tag}"  # type: ignore
        yaml.SafeLoader.add_constructor(tag_name, tag.construct)
        yaml.SafeDumper.add_representer(tag, tag.represent) # type: ignore

    # Add custom list representer for collapsing lists of scalars
    yaml.SafeDumper.add_representer(list, custom_list_representer)

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
    
    template: tags.ArenaConfig = yaml.load(template_path.read_text(), Loader=yaml.SafeLoader)

    count = countrec(template)
    if count > args.max:
        print(f"Too many variations. Stopping. "
              f"The total number of possible variations is {count}, "
              f"while the maximum is {args.max}, unless manually set with '--max'. "
              f"Try reducing choices.")
        print(explain_countrec(template))
        return

    print(f"Generating possible combinations: {count}")
    print(explain_countrec(template))

    # Test
    yaml.dump(template, open("tmp/example.yaml", "w"), Dumper=yaml.SafeDumper, default_flow_style=False)

    output_dir = Path(f"tmp/{args.file_path.stem}_generations/")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate sample based variations
    for i, variation in enumerate([samplerec(template) for _ in range(10)]):
        # TODO: Second pass to fix if's

        print(f"Variation {i+1}/10")
        print(f"Variation {i+1}/{count}")
        filename = f"{args.file_path.stem}_{i+1:05d}.yaml"
        with open(output_dir / filename, "w") as f:
            yaml.dump(variation, f, default_flow_style=False, Dumper=yaml.SafeDumper)

PROC_GEN_TAGS = tuple(tags.GET_PROC_GEN_TAGS())
SCALARS = (str, int, float)

def samplerec(node: Any) -> Any:
    if not isinstance(node, PROC_GEN_TAGS):
        if isinstance(node, list):
            return [samplerec(child) for child in node]
        elif isinstance(node, dict):
            return {k: samplerec(v) for k, v in node.items()}
        elif isinstance(node, SCALARS):
            return node
        elif isinstance(node, tags.CustomMappingTag):
            for k, v in node.__dict__.items():
                setattr(node,k, samplerec(v))
            return node
        elif isinstance(node, tags.CustomSequenceTag):
            for i, child in enumerate(node):
                node[i] = samplerec(child)
            return node
        elif isinstance(node, tags.CustomScalarTag):
            return node
    else:
        if isinstance(node, tags.ProcColor):
            return to_color(random.choice(util.COLORS))
        elif isinstance(node, tags.ProcIf):
            # TODO: Really implement
            return samplerec(node.then) if random.random() < 0.5 else samplerec(node.else_)
        elif isinstance(node, tags.ProcList):
            return random.choice(node.options)
        elif isinstance(node, tags.ProcRepeatChoice):
            choice = samplerec(node.value)
            return [deepcopy(choice) for _ in range(node.amount - 1)] + [choice]
        elif isinstance(node, tags.ProcRestrictCombinations):
            return samplerec(node.item)
        elif isinstance(node, tags.ProcVector3Scaled):
            scales = util.linspace(node.range[0], node.range[1], node.amount, endpoint=True)
            scale = random.choice(scales)
            return scale_vector3(node.base, scale)
        else:
            raise TypeError(f"Programmer error. Unknown tag: {node}")

def scale_vector3(vector: tags.Vector3, scale: float) -> tags.Vector3:
    return tags.Vector3(x=vector.x * scale, y=vector.y * scale, z=vector.z * scale)

def to_color(color: Tuple[int, int, int]) -> tags.RGB:
    return tags.RGB(r=color[0],g=color[1], b=color[2])

def countrec(node: Any):

    if not isinstance(node, PROC_GEN_TAGS):
        children = children_of(node)
        return functools.reduce(
            operator.mul,
            (countrec(child) for child in children), 
            1)
    
    if isinstance(node, tags.ProcIf):
        # !ProcIf does not increase the number of variations. It only some values in existing ones.
        return 1
    elif isinstance(node, tags.ProcRepeatChoice):
        return countrec(node.value) # Take over the number of variations in the choice to be repeated
    elif isinstance(node, tags.ProcList):
        return len(node.options)
    elif isinstance(node, tags.ProcColor):
        return node.amount
    elif isinstance(node, tags.ProcRestrictCombinations):
        return node.amount
    elif isinstance(node, tags.ProcVector3Scaled):
        return node.amount
    else:
        raise TypeError(f"Programmer error. Unknown type {type(node)} {node}.")

def explain_countrec(node: Any):
    if not isinstance(node, PROC_GEN_TAGS):
        children = children_of(node)
        explanations = [explain_countrec(child) for child in children]
        return " x ".join(explanation for explanation in explanations if explanation)

    if isinstance(node, tags.ProcColor):
        return f"{node.amount}#Colors"
    elif isinstance(node, tags.ProcIf):
        return f"{1}#If"
    elif isinstance(node, tags.ProcList):
        return f"{len(node.options)}#ListOptions"
    elif isinstance(node, tags.ProcRepeatChoice):
        return f"{countrec(node.value)}#RepeatChoice"
    elif isinstance(node, tags.ProcRestrictCombinations):
        return f"{node.amount}#RestrictCombinations"
    elif isinstance(node, tags.ProcVector3Scaled):
        return f"{node.amount}#Vector3Scaled"
    else:
        raise TypeError(f"Programmer error. Unknown type {type(node)} {node}.")

def children_of(node: Any) -> List[Any]:
    """
    Assumes the the input not is not a ProcGen tag.
    """
    if isinstance(node, list):
        return node
    elif isinstance(node, dict):
        return list(node.values())
    elif isinstance(node, SCALARS):
        return []
    elif isinstance(node, tags.CustomMappingTag):
        return list(node.__dict__.values())
    elif isinstance(node, tags.CustomSequenceTag):
        return list(node)
    elif isinstance(node, tags.CustomScalarTag):
        return []
    else:
        raise TypeError(f"Programmer error. Unknown type {type(node)} {node}.")


# Variations
# - Leaf nodes
#   -> return self
# - Non-leaf nodes, # lets assume two children
# We must know many elements there are, to know when we are done? Or return None instead.
#  Generate all combinations of children
#  - Generate the first variant of each child
#  -
def custom_list_representer(dumper, data):
    if not all(isinstance(item, (str, int, float)) for item in data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)
    else:
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

if __name__ == "__main__":
    run()