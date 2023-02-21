from typing import *


class Meta():
    # List of labels that should be added to the filename
    labels: list[str]

    # Choices made in the !Proc statements
    # Keys are the paths to the !Proc statements, values are the choices made.
    # choices: dict[str, str]

    def __init__(self):
        self.labels = []
        # self.choices = {}

    def add_label(self, label: Optional[str] = None):
        if label is not None:
            self.labels.append(label)
        # self.choices[path] = choice
