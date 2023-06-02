import argparse
import os
from typing import *
from pathlib import Path

import tqdm

import procgen_companion.core as pg
from procgen_companion.cli.args import BulkArgs


def run():
    args = BulkArgs.from_cli()

    pg.init(args.seed)

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

        for template in [Path(dir) / filename for filename in files]:
            try:
                handle_template(args, template)
            except Exception as e:
                e.add_note(f"Error while processing {template}")
                raise e


def handle_template(args: BulkArgs, path: Path):
    template = pg.read(path)

    n_variations = pg.count_recursive(template)
    explanation = pg.explain_count_recursive(template)

    print(f"{path}\t{n_variations}\t{explanation}")
