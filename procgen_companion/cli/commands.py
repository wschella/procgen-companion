import os
import sys
from typing import *
from pathlib import Path

import tqdm
import yaml
import csv

import procgen_companion.core as pg
import procgen_companion.tags as tags
import procgen_companion.cli.args as c


def generate_or_sample(args: Union[c.Generate, c.Sample]):

    if not args.path.exists():
        raise FileNotFoundError(args.path)

    if not args.path.is_file():
        raise ValueError("Path must be a file. Do you mean to use `procgen-bulk`?")

    template: tags.ArenaConfig = pg.read(args.path)

    n_variations = pg.count_recursive(template)
    print(f"Total possible variations: {n_variations}")
    print(pg.explain_count_recursive(template))

    if isinstance(args, c.Generate):
        if n_variations > args.max and args.head is None:
            print(f"Too many variations. Stopping. "
                  f"The total number of possible variations is {n_variations}, "
                  f"while the maximum is {args.max}. "
                  f"Try reducing choices, increasing --max, or using --head.")
            print(pg.explain_count_recursive(template))
            sys.exit(1)

    # Prepare output directory
    default_output_dir = Path(f"tmp/{args.path.stem}_variations/")
    output_dir = default_output_dir if args.output is None else args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy the template to the output directory
    if not args.prevent_template_copy:
        yaml.dump(template, open(output_dir / "template.yaml", "w"),
                  default_flow_style=False, Dumper=yaml.SafeDumper)

    # Create iterator over variations
    if isinstance(args, c.Sample):
        amount = args.amount  # TODO: If more than n_variations, warn
        iterator = pg.generate('sample', template, args.amount)
    else:
        head = args.head if args.head is not None else n_variations
        amount = min(n_variations, head, args.max)
        iterator = pg.generate('exhaustive', template, amount)

    # Consume iterator over variations
    meta_file = open(output_dir / "meta.csv", "w")
    for i, (variation, meta) in tqdm.tqdm(enumerate(iterator), total=amount):
        filename = pg.format_filename(args.path, i, meta.labels)
        csv.writer(meta_file).writerow([filename] + meta.labels)
        with open(output_dir / filename, "w") as f:
            yaml.dump(variation, f, default_flow_style=False, Dumper=yaml.SafeDumper)

    meta_file.close()


def count_bulk(args: c.CountBulk):
    if not args.path.exists():
        raise FileNotFoundError(args.path)

    if not args.path.is_dir():
        raise ValueError(
            "Path must be a directory. Do you mean to use regular `procgen` instead of `procgen-bulk`?")

    for dir, _subdirs, files in os.walk(args.path, topdown=True):
        # Exclude ignored directories
        # https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
        if args.ignore_dirs:
            _subdirs[:] = [d for d in _subdirs if d not in args.ignore_dirs]

        for template_path in [Path(dir) / filename for filename in files]:
            try:
                template = pg.read(template_path)

                n_variations = pg.count_recursive(template)
                explanation = pg.explain_count_recursive(template)

                print(f"{template_path}\t{n_variations}\t{explanation}")
            except Exception as e:
                print(f"Error while processing {template_path}:")
                raise e
