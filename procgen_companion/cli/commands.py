import os
import sys
from typing import *
from pathlib import Path

import tqdm
import yaml
import csv

import procgen_companion.core as pg
import procgen_companion.tags as tags
import procgen_companion.errors as errors
import procgen_companion.cli.args as c


def generate_or_sample(args: Union[c.Generate, c.Sample]):
    try:
        _generate_or_sample(args)
    except errors.ProcGenError as e:
        print(e)
        sys.exit(1)


def _generate_or_sample(args: Union[c.Generate, c.Sample]):

    if not args.path.exists():
        raise FileNotFoundError(args.path)

    if not args.path.is_file():
        raise ValueError("Path argument must point to a file but does not." +
                         "Did you pass a directory and mean to use a bulk command?")

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
    default_output_dir = Path(f"./variations_{args.path.stem}/")
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

    consume_variations(iterator, amount, output_dir, prefix="")


def count_bulk(args: c.CountBulk):
    for template_path in iterdir(args.path, args.ignore_dirs, args.ignore_hidden):
        try:
            template = pg.read(template_path)
            n_variations = pg.count_recursive(template)
            explanation = pg.explain_count_recursive(template)

            tpath_formatted = truncate_middle(str(template_path), width=32, placeholder="...")
            tpath_formatted = tpath_formatted.ljust(32)
            nvars_formatted = truncate_middle(str(n_variations), width=8, placeholder="...")
            nvars_formatted = nvars_formatted.rjust(8)
            print(f"{tpath_formatted}\t{nvars_formatted}\t{explanation}")
        except Exception as e:
            print(f"Error while processing {template_path}:")
            raise e


def sample_bulk(args: c.SampleBulk):
    # Directory of directories (one for each template)
    output_dir_base = args.output or Path(f"./variations_{args.path.stem}/")
    output_dir_base.mkdir(parents=True, exist_ok=True)

    log = open(output_dir_base / "log.csv", "w")

    for template_path in iterdir(args.path, args.ignore_dirs, args.ignore_hidden):
        output_dir = output_dir_base / template_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # Progress bar prefix
        tpath_f = truncate_middle(str(template_path), width=48, placeholder="...")
        pb_prefix = f"{tpath_f} (?)".ljust(48 + 8 + len(" ()"))

        try:
            template = pg.read(template_path)

            # Add extra info to the progress bar prefix
            nvars = pg.count_recursive(pg.read(template_path))
            nvars_f = truncate_middle(str(nvars), width=8, placeholder="...")
            pb_prefix = f"{tpath_f} ({nvars_f})".ljust(48 + 8 + len(" ()"))

            iterator = pg.generate('sample', template, args.amount)
            consume_variations(iterator, args.amount, output_dir, "", pb_prefix=pb_prefix)

            csv.writer(log).writerow([
                template_path,
                f"Success. Sampled {args.amount} from {nvars} possible variations."])

        except Exception as e:
            # Write error to file for easier debugging
            with open(output_dir / "error.txt", "w") as f:
                f.write(str(e))

            # Continue for "expected errors"
            if isinstance(e, errors.ProcGenError):
                print(f"{pb_prefix}: Error ({e.user_label})")
                csv.writer(log).writerow([template_path, f"Error ({e.user_label})"])

            # Break for unexpected errors
            else:
                print(f"Unexpected error while processing {template_path}:")
                csv.writer(log).writerow([template_path, "Unexpected error"])
                # raise e

    log.close()


def consume_variations(iterator, amount, output_dir, prefix, pb_prefix: Optional[str] = None):
    # Consume iterator over variations
    meta_file = open(output_dir / "meta.csv", "w")
    for i, (variation, meta) in tqdm.tqdm(enumerate(iterator), total=amount, desc=pb_prefix):
        filename = format_filename(prefix, i, meta.labels)
        csv.writer(meta_file).writerow([filename] + meta.labels)
        with open(output_dir / filename, "w") as f:
            yaml.dump(variation, f, default_flow_style=False, Dumper=yaml.SafeDumper)

    meta_file.close()


def iterdir(path: Path, ignore_dirs: Union[List[str], List[Path]], ignore_hidden: bool) -> Iterator[Path]:
    ignore_dirs = [Path(d) for d in ignore_dirs]

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_dir():
        raise ValueError("Path must be a directory but is not. Is the use of `bulk` a mistake?")

    for dir, _subdirs, files in os.walk(path, topdown=True):
        # Exclude ignored directories
        # https://stackoverflow.com/questions/19859840/excluding-directories-in-os-walk
        if ignore_dirs:
            _subdirs[:] = [d for d in _subdirs if Path(d) not in ignore_dirs]

        if ignore_hidden:
            files[:] = [f for f in files if not f.startswith(".")]
            _subdirs[:] = [d for d in _subdirs if not d.startswith(".")]

        for template_path in [Path(dir) / filename for filename in files]:
            yield template_path


def format_filename(prefix: str, variation_idx: int, labels: list[str]):
    label = f"_{'_'.join(labels)}" if labels else ""
    prefix = f"{prefix}_" if prefix else ""
    return f"{prefix}{variation_idx:05d}{label}.yaml"


def truncate_middle(s: str, width: int, placeholder="..."):
    # https://www.xormedia.com/string-truncate-middle-with-ellipsis/
    if len(s) <= width:
        return s
    n_2 = width // 2 - len(placeholder)
    n_1 = width - n_2 - len(placeholder)
    return f"{s[:n_1]}{placeholder}{s[-n_2:]}"
