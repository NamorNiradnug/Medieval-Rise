from PyQt5.Qt import QImage


imageResources = {}


def getImage(name: str) -> QImage:
    if name in imageResources:
        return imageResources[name]
    else:
        resource = QImage("assets/" + name + ".png")
        if resource.isNull():
            raise ValueError("Resource doesn't exist")
        imageResources[name] = resource
        return resource