from typing import *


class Meta():
    # List of labels that should be added to the filename
    labels: list[str]

    def __init__(self, labels: Optional[list[str]] = None):
        self.labels = labels if labels is not None else []

    def add_label(self, label: Optional[str] = None):
        if label is not None:
            self.labels.append(label)
