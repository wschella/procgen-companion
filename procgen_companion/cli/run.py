from typing import *

import procgen_companion.core as pg
import procgen_companion.cli.args as c
import procgen_companion.cli.commands as commands
from procgen_companion.cli.args import Args


def run():
    """
    Entry point for the `procgen` command.
    """
    args = Args.from_cli().command
    pg.init(args.seed)

    if isinstance(args, c.GenerateBulk):
        raise NotImplementedError("Bulk generation is not yet implemented.")
    elif isinstance(args, c.SampleBulk):
        commands.sample_bulk(args)
    elif isinstance(args, c.CountBulk):
        commands.count_bulk(args)
    elif isinstance(args, c.Generate):
        commands.generate_or_sample(args)
    elif isinstance(args, c.Sample):
        commands.generate_or_sample(args)
    else:
        raise ValueError(f"Unknown command: {args}")
