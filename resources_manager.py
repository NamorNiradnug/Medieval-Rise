import json
import os
import sys

from PyQt5.Qt import QImage


imageResources = {}

try:
    wd = sys._MEIPASS
except AttributeError:
    wd = os.getcwd()


def getImage(name: str, get_null: bool = False) -> QImage:
    """PNG image called name in assets."""

    if name in imageResources:
        return imageResources[name]
    else:
        resource = QImage(os.path.join(wd, "assets", name + ".png"))
        if resource.isNull():
            if not get_null:
                raise ValueError(f"Resource {name}.png doesn't exist")
        else:
            imageResources[name] = resource
        return resource


def getJSON(name: str) -> dict:
    """Converted JSON file called name in data."""
    
    with open(os.path.join(wd, "data", name + ".json")) as f:
        return json.load(f)
