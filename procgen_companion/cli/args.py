import argparse
from typing import *
from pathlib import Path
from dataclasses import dataclass


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

    @staticmethod
    def from_cli() -> 'Args':
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
        args_raw = parser.parse_args()
        return Args(**vars(args_raw))


@dataclass
class BulkArgs:
    path: Path
    seed: int
    prevent_template_copy: bool = False

    @staticmethod
    def from_cli() -> 'BulkArgs':
        parser = argparse.ArgumentParser(
            prog="procgen-bulk",
            description="Procedurally generate variations of an AnimalAI task definition in bulk."
        )
        parser.add_argument('path', type=Path)
        parser.add_argument('-s', '--seed', type=int, default=1234)
        parser.add_argument('--prevent-template-copy', action=argparse.BooleanOptionalAction)
        args_raw = parser.parse_args()
        return BulkArgs(**vars(args_raw))
