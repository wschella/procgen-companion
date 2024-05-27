from pathlib import Path
from typing import Any
from abc import ABC
import textwrap

import yaml


class ProcGenError(ABC, Exception):
    user_label: str


class SourceAnnotatedProcGenError(ProcGenError):

    def __init__(self, error: ProcGenError, template_path: Path):
        self.error = error
        self.template_path = template_path
        self.user_label = error.user_label

    def __str__(self):
        return f"{self.user_label} in {self.template_path}\n" + str(self.error)


class NodeAnnotatedProcGenError(ProcGenError):
    def __init__(self, node: Any, user_label: str, message: str):
        self.node = node
        self.message = message
        self.user_label = user_label

    def __str__(self):
        node_str = yaml.dump(self.node, None, default_flow_style=False, Dumper=yaml.SafeDumper)
        node_str = textwrap.indent(node_str, "  ")
        node_str = \
            f"-----------------------------\n" + \
            f"{node_str}" + \
            f"-----------------------------"
        return f"{node_str}\nError ({self.user_label}): {self.message}"


class BaseProcGenError(ProcGenError):
    def __init__(self, user_label: str, message: str):
        self.user_label = user_label
        self.message = message

    def __str__(self):
        return f"Error ({self.user_label}): {self.message}"
