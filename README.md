# Procedural Generation Companion

An AnimalAI companion tool for procedural generation of task variations.

This repo provides both a format for specifying a task template, which defines which fields can vary and how they should do so, and a script to read such a template and programmatically generate all possible variations, or a random subset thereof.

## Usage

TODO: Outdated

Run `python procgen.py path/to/file.yaml`.

It will automatically look for a file called `path/to/file.template.yaml`, and then generate and save all variations in the directory `path/to/file_variations/`.

## Functionality

A template is associated with an existing task definition .yaml file, which provides the values for fields that remain static.

### Skip generating any variations for a field of a mapping

### Skip generating any variations for a list element

### Select variations of a field from a list of options

Status: no examples, not implemented.

### Select variations of a mapping from a list of options

Status: no examples, not implemented.

`!ProcList` does not support nested `!Proc`-tags.

### Select variations of a field from a range

Status: no examples, not implemented.

### Condition the selection of variations on the values of other fields

`!ProcIf` will cause over counting.

Status: no examples, not implemented.

### Generate random colors

Status: no examples, not implemented

This is a short-hand, as this is needed a lot.

### Generate the same variation for a list of mappings

E.g. 7 walls need to vary their color, but it must always be the same color. Same thing goes for angles.

### Varying all dimensions of a Vec3 at the same time

Status: no examples, not implemented

### Restricting variations

Status: no examples, not implemented

E.g. 7 walls need to vary their color, and it does not always need to be the same color, but we only want 20 different combinations in total.

### Specifying tags that should be included in the filename

Status: no examples, not implemented.

Tags will be associated with the first `id` up the node tree.

TODO: Tags are currently not removed yet, this breaks the AnimalAI.

## Assumptions

- In an `!Item`, the lists of positions, sizes, rotations, and colors are of the same length.
- All lists in the companion file are of the same length as the corresponding list in the task definition. List elements that nod need to be varied are marked with a simple `pass`. See <#functionality> for more details.
- A `!ProcGenIf` occurs later than the field it references.
