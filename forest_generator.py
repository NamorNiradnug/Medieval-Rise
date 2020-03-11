from math import ceil
from random import randint, choice, gauss
from types import FunctionType

from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QIcon
from PyQt5.QtWidgets import QApplication, QLabel

from resources_manager import getImage


class Forest:
    """Stores a forest center and its type."""

    forest_types = ["spruce", "oak", "birch"]

    def __init__(self, center: (int, int), tree_type: str):
        if tree_type not in self.forest_types:
            raise AttributeError(
                str(tree_type)
                + " is not forest type: they are "
                + ", ".join(self.forest_types)
                + "."
            )
        self.center = center
        self.tree_type = tree_type


class ForestMap:
    def __init__(
        self,
        width: float,
        height: float,
        trees: [(int, int), ...],
        forests: [Forest, ...],
    ):
        self.trees_data = tuple(sorted(trees))
        self.forests = forests
        self.width = width
        self.height = height

    def draw(self, painter: QPainter, scale: float = 10) -> None:
        colors = {
            "oak": QColor("#7E2E0F"),
            "birch": QColor("white"),
            "spruce": QColor("darkgreen"),
        }
        pen = QPen()
        pen.setWidth(0.75 * scale)
        for tree in self.trees_data:
            pen.setColor(colors[nearestForest(tree, self.forests)[0].tree_type])
            painter.setPen(pen)
            painter.drawPoint(tree[0] * scale, tree[1] * scale)


def manhattanMetric(point1: (float, float), point2: (float, float)) -> float:
    return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])


def euclideanMetric(point1: (float, float), point2: (float, float)) -> float:
    return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[0]) ** 2) ** 0.5


def nearestForest(
    point: (float, float),
    forests: [Forest, ...],
    metrics: FunctionType = manhattanMetric,
) -> (Forest, float):
    min_dist = metrics(point, forests[0].center)
    number = 0
    for i in range(1, len(forests)):
        dist = metrics(point, forests[i].center)
        if dist < min_dist:
            min_dist = dist
            number = i
    return forests[number], min_dist


def generateForestMap(width: float, height: float, density: float = 8) -> ForestMap:
    forests = generateForests(width, height)
    trees = []
    sigma = 1 / density
    # Generate 0 or 1 tree in every 2 by 2 square.
    for x in range(0, ceil(width), 2):
        for y in range(0, ceil(height), 2):
            forest, distance = nearestForest((x + 1, y + 1), forests)
            if abs(gauss(0, sigma)) < 1 / (distance + 0.7):
                trees.append((x + gauss(1, 0.9) + 0.1, y + gauss(1, 0.9) + 0.1))
    return ForestMap(int(width), int(height), trees, forests)


def generateForests(width: float, height: float) -> [Forest, ...]:
    # Generate 1 Forest in every 16 by 16 square.
    forests = []
    for i in range(ceil(width / 16)):
        for j in range(ceil(height / 16)):
            forests.append(
                Forest(
                    (
                        randint(16 * i + 1, 16 * i + 15),
                        randint(16 * j + 1, 16 * j + 15),
                    ),
                    choice(Forest.forest_types),
                )
            )
    return forests


def drawGrass(painter: QPainter, width: float, height: float) -> None:
    grass_pixmap = QPixmap(getImage("grass_noline"))
    painter.drawTiledPixmap(0, 0, width, height, grass_pixmap)
    painter.drawTiledPixmap(
        -grass_pixmap.width() / 2,
        -grass_pixmap.height() / 2,
        width + grass_pixmap.width(),
        height + grass_pixmap.height(),
        grass_pixmap,
    )


def showForestMap(forest_map: ForestMap, scale: float = 10) -> None:
    app = QApplication([])
    frame = QLabel()
    frame.setWindowTitle("Forest")
    frame.setWindowIcon(QIcon(QPixmap(getImage("spruce"))))
    pixmap = QPixmap(forest_map.width * scale, forest_map.height * scale)
    painter = QPainter(pixmap)
    drawGrass(painter, forest_map.width * scale, forest_map.height * scale)
    forest_map.draw(painter, scale)
    pen = QPen(QColor("red"))
    pen.setWidth(scale / 2)
    painter.setPen(pen)
    for forest in forest_map.forests:
        painter.drawPoint(forest.center[0] * scale, forest.center[1] * scale)
    painter.end()
    frame.setPixmap(pixmap)
    frame.showMaximized()
    app.exec_()
