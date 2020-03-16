import json

from PyQt5.Qt import QImage


imageResources = {}


def getImage(name: str) -> QImage:
    if name in imageResources:
        return imageResources[name]
    else:
        resource = QImage(f"assets/{name}.png")
        if resource.isNull():
            raise ValueError(f"Resource {name}.png doesn't exist")
        imageResources[name] = resource
        return resource


def getJSON(name: str) -> dict:
    with open(f'data/{name}.json') as f:
        return json.load(f)
