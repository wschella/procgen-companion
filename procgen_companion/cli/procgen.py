import argparse
import csv
from typing import *
from pathlib import Path

import yaml
import tqdm

import procgen_companion.tags as tags
import procgen_companion.core as pg
from procgen_companion.cli.args import Args


def run():
    args = Args.from_cli()

    pg.init(args.seed)

    if not args.path.exists():
        raise FileNotFoundError(args.path)

    if not args.path.is_file():
        raise ValueError("Path must be a file. Do you mean to use `procgen-bulk`?")

    template: tags.ArenaConfig = pg.read(args.path)

    n_variations = pg.count_recursive(template)
    print(f"Total possible variations: {n_variations}")
    print(pg.explain_count_recursive(template))

    if n_variations > args.max and (args.sample is None and args.head is None):
        print(f"Too many variations. Stopping. "
              f"The total number of possible variations is {n_variations}, "
              f"while the maximum is {args.max}. "
              f"Try reducing choices, increasing --max, or using --head.")
        print(pg.explain_count_recursive(template))
        return

    # Prepare output directory
    output_dir = Path(f"tmp/{args.path.stem}_variations/") if args.output is None else args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy the template to the output directory
    if not args.prevent_template_copy:
        yaml.dump(template, open(output_dir / "template.yaml", "w"),
                  default_flow_style=False, Dumper=yaml.SafeDumper)

    # Create iterator over variations
    if args.sample is not None:
        assert args.head is None, "Cannot use both --head and --sample"
        amount = min(n_variations, args.sample, args.max)
        iterator = pg.generate('sample', template, amount)
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
