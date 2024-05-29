import argparse
from typing import Optional, Union, List, Literal
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SharedOptions:
    seed: int = 1234
    output: Optional[Path] = None
    copy_template: bool = True


@dataclass
class SharedBulkOptions:
    ignore_dirs: List[Path] = field(default_factory=list)
    ignore_hidden: bool = True
    flatten: bool = False


@dataclass
class _Sample:
    path: Path
    amount: int


@dataclass
class Sample(SharedOptions, _Sample):
    pass


@dataclass
class _Generate:
    path: Path
    max: int
    head: Optional[int] = None


@dataclass
class Generate(SharedOptions, _Generate):
    pass


@dataclass
class _SampleBulk:
    path: Path
    amount: int


@dataclass
class SampleBulk(SharedOptions, SharedBulkOptions, _SampleBulk):
    pass


@dataclass
class _GenerateBulk:
    path: Path


@dataclass
class GenerateBulk(SharedOptions, SharedBulkOptions, _GenerateBulk):
    pass


@dataclass
class _CountBulk:
    path: Path


@dataclass
class CountBulk(SharedOptions, SharedBulkOptions, _CountBulk):
    pass


Command = Union[Sample, Generate, SampleBulk, GenerateBulk, CountBulk]
CommandName = Literal["sample", "gen", "sample-bulk", "gen-bulk", "count-bulk"]
COMMAND_MAP = {
    "sample": Sample,
    "gen": Generate,
    "sample-bulk": SampleBulk,
    "gen-bulk": GenerateBulk,
    "count-bulk": CountBulk,
}
COMMAND_NAMES: List[str] = list(COMMAND_MAP.keys())


@dataclass
class Args:
    command: Command

    @staticmethod
    def from_cli() -> "Args":
        parser = argparse.ArgumentParser(
            prog="procgen-companion",
            description="Procedurally generate variations of an AnimalAI based on a task template.",
        )

        subparsers = parser.add_subparsers(dest="command", required=True)

        sample = subparsers.add_parser(
            "sample", help="Sample variations of a task definition."
        )
        sample.add_argument("path", type=Path)
        sample.add_argument(
            "amount", type=int, default=100, help="Number of variations to sample."
        )

        gen = subparsers.add_parser(
            "gen", help="Generate variations of a task definition."
        )
        gen.add_argument("path", type=Path)
        gen.add_argument("-m", "--max", type=int, default=10000)
        gen.add_argument("--head", type=int)

        sample_bulk = subparsers.add_parser(
            "sample-bulk", help="Sample variations of multiple task definitions."
        )
        sample_bulk.add_argument("path", type=Path)
        sample_bulk.add_argument(
            "amount", type=int, default=100, help="Number of variations to sample."
        )

        gen_bulk = subparsers.add_parser(
            "gen-bulk", help="Generate variations of multiple task definitions."
        )
        gen_bulk.add_argument("path", type=Path)

        count_bulk = subparsers.add_parser(
            "count-bulk",
            help="Count the number of variations of multiple task definitions.",
        )
        count_bulk.add_argument("path", type=Path)

        # Add shared options for all commands
        for p in [sample, gen, sample_bulk, gen_bulk, count_bulk]:
            group = p.add_argument_group("options")
            group.add_argument(
                "-s",
                "--seed",
                type=int,
                default=1234,
                help="Seed for random number generation.",
            )
            group.add_argument(
                "-o",
                "--output",
                type=Path,
                help="Output directory to save generate variations in.",
            )
            group.add_argument(
                "--copy-template",
                action=argparse.BooleanOptionalAction,
                help="Prevent copying the template to the output directory.",
                default=True,
            )

        # Add shared options for bulk commands
        for p in [sample_bulk, gen_bulk, count_bulk]:
            group = p.add_argument_group("bulk options")
            group.add_argument(
                "-i",
                "--ignore-dirs",
                nargs="+",
                default=[],
                type=Path,
                help="Directories to ignore.",
            )
            group.add_argument(
                "--no-ignore-hidden",
                action="store_false",
                dest="ignore_hidden",
                help="Do not ignore hidden folders.",
            )
            group.add_argument(
                "--flatten",
                action="store_true",
                help="Flatten the directory structure of the source into a list of files (as opposed to mimicking the structure). Note, if you have identically named files, they will overwrite each other.",
            )

        args_raw = vars(parser.parse_args())
        command_name: CommandName = args_raw.pop("command")
        command = COMMAND_MAP[command_name]
        return Args(command=command(**args_raw))
