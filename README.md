# Procedural Generation Companion

**NOTE: Work-in-progress. Not ready yet**

An AnimalAI companion tool for procedural generation of task variations.

This repo provides a format for specifying a _task template_, a specification of all the possible variations of a task, plus a command line tool to read such a template and programmatically generate the specified variations.

## To Do's

- [ ] Check first if template is valid YAML and give a dedicated error message. Also give dedicated messages for common problems, e.g. if it contains tabs.
- [ ] Check common misspellings like !Proclist, !Profif, !Prociff
- [ ] Check common mistakes
  - [ ] pass_mark is a list
  - [ ] forgetting proc_meta (but having proc_labels)

## Usage

Run `procgen path/to/template.yaml`.

The tool will then procedurally generate all possible task variations and save them in the directory `path/to/file_variations/`.

A procgen-template is structured like an AnimalAI .yaml file, but one can make use of certain special tags like `!ProcList`, `!ProcColor`, `!ProcIf` that define the allowed variations of a field's value. The procgen-companion tool will then generate all possible combinations of these fields, and output a .yaml file usable by the AnimalAI environment for each combination.

As an example, take following .yaml file. It is not a valid AnimalAI config, but that doesn't matter right now:

```yaml
# example.template.yaml
field1: !ProcList [0, 120]
field2: !ProcList [90, 180]
```

If we run `procgen example.template.yaml`, four new files will be created:

```yaml
# example_variations/example_1.yaml
field1: 0
field2: 90

# example_variations/example_2.yaml
field1: 0
field2: 180

# example_variations/example_3.yaml
field1: 120
field2: 90

# example_variations/example_4.yaml
field1: 120
field2: 180
```

The template used will also be copied `example_variations/template.yaml`.

Every valid AnimalAI .yaml file is also a valid procgen-companion template.
All the fields you don't want to procedurally generate will be ignored and copied.

It is also possible to take a random sample instead of generating all possible combinations. Use `procgen --sample <amount> path/to/template.yaml` instead then, with `<amount>` being an integer representing the number of samples you want.

## Tags

All tags used in procgen-companion start with `!Proc`.

### Select variations from a list of options

With `!ProcList`, you define all the possible options a value can take. The items of the list can be any kind of valid yaml, i.e. lists, tags, mappings (see below).
But `!ProcList` does not support nested `!Proc`-tags, i.e. the items of the list can not be `!Proc`-tags.

```yaml
# Define three possible options for a scalar field value.
!ProcList [0, 90, 180]
```

```yaml
# Define three possible options for a mapping
!ProcList [
  !Vector3 { x: 10, y: 0, z: 1 },
  !Vector3 { x: 20, y: 1, z: 5 },
  !Vector3 { x: 20, y: 1, z: 10 },
]

# Exactly the same as above, just with different notation.
!ProcList
- !Vector3 { x: 10, y: 0, z: 1 }
- !Vector3 { x: 20, y: 1, z: 5 }
- !Vector3 { x: 20, y: 1, z: 10 }
```

You can also perfectly do this instead:

```yaml
!Vector3 { x: !ProcList [2, 4, 6], y: 1, z: !ProcList [5, 10, 15] }
```

This defines 3x3=9 possible variations: `!Vector3 {x: 2, y: 1, z: 5}`, `!Vector3 {x: 2, y: 1, z: 10}`, `!Vector3 {x: 2, y: 1, z: 15}`, and the same for `x: 4` and `x: 6`.

### Generate random colors

This will generate a new color each time, until 10 different ones have been picked. The colors will be picked from a fixed list of colors. If the amount specified here is larger than the list of colors we use, we will throw an error so you can fix it or ask us to create more colors.

```yaml
!ProcColor 5
```

### Varying all dimensions of a Vec3 at the same time

A common use case is varying all dimensions of a Vec3 at the same time, e.g. scaling the vector with a single scalar number.

The base `!Vector3` will not be included in the possible options. If you want that, just include `1` as a scale factor.

```yaml
!ProcVector3Scaled
base: !Vector3 { x: 2, y: 1, z: 1 }
scales: [1, 2, 3, 4]
```

The `base` is an optional argument. If it is not present, the unit vector will be assumed, i.e. `!Vector3 { x: 1, y: 1, z: 1}`. The following is thus also valid:

```yaml
!ProcVector3Scaled
scales: [1, 2, 3, 4]
```

### Make the same choice for a list of values

You can use `!ProcRepeatChoice` when for example three walls need to vary their color, but it must always be the same color, i.e. they must vary at the same time. This tag will produce a list of values, each of them identical.
The `value` field can contain any valid yaml including (nested) `!Proc`-tags, as that is what is designed for. Any choice made in the `!Proc` tags will be copied.
It is allowed for the `value` field to not contain any `!Proc` tags. Everything works just the same.

```yaml
colors: !ProcRepeatChoice
  amount: 3 # The amount of repetitions, i.e. the number of elements in the resulting list.
  value: !ProcColor 5 # The amount of different values a list item can take.

# One possible realization of the possible 5 would like like this:
colors:
  - !RGB {r: 128, g: 128, b: 128 }
  - !RGB {r: 128, g: 128, b: 128 }
  - !RGB {r: 128, g: 128, b: 128 }
```

### Restricting variations

You can use `!ProcRestrictCombinations` when you know some part of the yaml file is responsible for many different possibilities, but you want to limit the total, without restricting any of the individual choices.
An example is when seven walls need to vary their color, you don't want it to be the same color, and you only want 25 different combinations in total.
This works by uniformly random sampling all the `!Proc`-tags nested inside.

The `item` field does _not_ need to be a list as is the case right now. It can be anything.

```yaml
!ProcRestrictCombinations
amount: 25 # Number of possible values this tag will generate.
item:
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
  - !ProcColor 10
```

### Condition the selection of variations on the values of other fields

```yaml
!ProcIf
value: [agent.positions.0.x, agents.positions.0.z]
cases: [[1, 5], [1, 7], [3, !R [10, 20]]]
then: [90, 120, 150]
default: 0
```

Depending on the the values the variables take, different values are generated by the `!ProcIf` tag. A `!ProcIf` tag is reactive. It does not increase the number of combinations, only sets the values of some fields in an existing combination.

Conceptually, if the variables in the `value` field are equal to the numbers defined in the `cases` field (or within a range `!R`) then the corresponding value in the `then` field will be selected. If none of the cases match the value of the `default` field is taken. If your cases overlap by accident, the first matching case will be taken.

Here (first case): if x=1 and z=5, then we take 90.
Instead of a single number, you can also specify a range with `!R`.
Here (last case): if x=3 and z between 10 and 20 (inclusive), then we take 150.

- The `value` field can be a string, or a list of strings. Multiple strings indicate there multiple variables we care about. Each string is a reference to a specific field in the generated yaml file (see below).
- The `cases` field is always list. If `value` is a list, `cases` must be a list of lists, and an inner list needs to match the length of `value`. The outer list can be any length, each element represent a "case". It can be of length 1 (representing a single "if", with `default` acting as the "else".)
- The `then` field results is always a list. Its length equals the length of the outer list of the `cases` field.
- The `default` is always a scalar, i.e. a number, a `!Vector3`, etc. It is an optional argument. If it is not provided, the tool will throw an error and stop execution when any variables take on a value that is not in the list of cases.

TODO: On references. Generated yaml file. First part of the dot separated must refer to an AnimalAI mapping (`!ArenaConfig`, `!Arena`, `!Item`, `!Vector3`, ...) with the corresponding `id` field.

```yaml
# With only 1 variable
!ProcIf
value: agent.positions.0.z,
cases: [5, 7, 10]
then: [90, 120, 150]
default: 0

# With only 1 case and 1 variable
!ProcIf
value: agent.positions.0.z,
cases: [5]
then: [180]
default: 0

# With only 1 case, but two variables (one of them in a range)
!ProcIf
value: [agent.positions.0.x, agents.positions.0.z]
cases: [[1, !R [5, 10]]]
then: [180]
default: 0

# With three cases, and no default.
# The tool will throw an error and stop if agent.positions.0.x takes values other than those specified, e.g. 15.
!ProcIf
value: agent.positions.0.x
cases: [1, !R [2, 9], 10]
then: [0, 90, 180]
```

## Labelling filenames

If you want to change the filename depending on some of the generated values, you can use can add a `labels` field to `!ProcIf` and`!ProcVector3Scaled`, or you can use the new `!ProcListLabelled`.

Make sure that your labels are filename friendly (e.g. no colons).

```yaml
!ProcIf
value: [agent.positions.0.x, agents.positions.0.z]
cases: [[1, 5], [1, 7], [3, !R [10, 20]]]
then: [90, 120, 150]
labels: [dist_close, dist_med, dist_far]
default: 0
default_label: dist_default
# Currently no support for a default label yet.

!ProcVector3Scaled
base: !Vector3 { x: 2, y: 1, z: 1 }
scales: [1, 2, 3]
labels: [size_small, size_med, size_large]

!ProcListLabelled
- label: dist_far
  value: !Vector3 { x: 20, y: 0, z: 1 }
- label: dist_medium
  value: !Vector3 { x: 20, y: 1, z: 5 }
- label: dist_close
  value: !Vector3 { x: 20, y: 1, z: 10 }
```

There is also a new special section `proc_meta` in the beginning of the yaml file, which will not be present in the generate AnimalAI config, but allows you to specify independent labels. You have to use `!ProcIfLabels`, which works exactly like `!ProcIf`, but it will have the corresponding `then` value included in the filename.

```yaml
!ArenaConfig
proc_meta:
  proc_labels:
    - !ProcIfLabels
      value: [agent.positions.0.x, agents.positions.0.z]
      cases: [[1, 5], [1, 7], [3, !R [10, 20]]]
      labels: [dist_far, dist_close, dist_medium]
      default: dist_default # Optional
arenas:
  0: !Arena
    items: # ...
```
