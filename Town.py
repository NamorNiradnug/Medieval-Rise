from bisect import insort, bisect
from random import randint
from typing import Any, Set, Tuple

from PyQt5.Qt import QPoint, QPointF, QSize, QWheelEvent
from PyQt5.QtGui import QPainter

from TownObjects import (ISOMETRIC_HEIGHT1, ISOMETRIC_HEIGHT2, ISOMETRIC_WIDTH,
                         Block, BuildingType, BuildingTypes, Grounds, BuildingGroups, getImage,
                         RoadType, RoadTypes)


def isometric(x: float, y: float) -> QPointF:
    """Convert rectangular coordinates to isometric."""

    # (iso_x + iso_y) * ISOMETRIC_HEIGHT1 = y
    # (iso_x - iso_y) * ISOMETRIC_WIDTH = x
    return QPointF(((y / ISOMETRIC_HEIGHT1) + (x / ISOMETRIC_WIDTH)),
                   ((y / ISOMETRIC_HEIGHT1) - (x / ISOMETRIC_WIDTH))) / 2


def isPointInRect(point: QPoint, rect: Tuple[QPoint, QSize]) -> bool:
    """Checking the position of a point relative to a rectangle."""

    return (
            rect[0].x() <= point.x() <= rect[0].x() + rect[1].width()
            and rect[0].y() <= point.y() <= rect[0].y() + rect[1].height()
    )


class Chunk:
    """Store data of blocks in 16 by 16 square."""

    def __init__(self, x: int, y: int):
        self.x = x * 16
        self.y = y * 16
        # Generate a 16x16x3 matrix.
        self.is_empty = True
        self.blocks = tuple(tuple([None] * 5 for _ in range(16)) for _ in range(16))
        self.grounds = tuple([Grounds.grass for _ in range(16)] for _ in range(16))
        self.masks = tuple([None] * 16 for _ in range(16))
        self.roads = tuple([None for _ in range(16)] for _ in range(16))
        self.citizens = tuple(tuple([] for _ in range(16)) for _ in range(16))

    def draw(self, painter: QPainter, x: int, y: int, projecting_opacity: float, builded_opacity: float = 1) -> None:
        """Draw chunk."""

        if not (0 <= projecting_opacity <= 1):
            raise AttributeError("Opacity must be between 0 and 1.")

        for i in range(16):
            for j in range(16):

                painter.setOpacity(1)
                self.grounds[i][j].draw((self.x + i - self.y - j) * ISOMETRIC_WIDTH - x, (self.x + self.y + i + j) *
                                        ISOMETRIC_HEIGHT1 - y, painter)

                # Draw road
                painter.setOpacity(1)
                if self.roads[i][j] is not None:
                    if type(self.roads[i][j]) == ProjectedRoad:
                        painter.setOpacity(projecting_opacity)
                    self.roads[i][j].draw(painter, x, y)

                # Draw mask
                painter.setOpacity(builded_opacity)
                if self.masks[i][j] is not None:
                   self.masks[i][j].draw(x, y, painter) 

                # Draw citizens
                painter.setOpacity(1)
                for citizen in self.citizens[i][j]:
                    citizen.draw(painter, x, y)

                # Draw blocks
                for z in range(5):
                    painter.setOpacity(builded_opacity)
                    building = self.blocks[i][j][z]
                    if building is not None:
                        if type(building) == ProjectedBuilding:
                            painter.setOpacity(projecting_opacity)
                        block, angle, variant = building.getBlock(i + self.x, j + self.y, z)
                        block.draw((self.x + i - self.y - j) * ISOMETRIC_WIDTH - x, (self.x + self.y + i + j) *
                                   ISOMETRIC_HEIGHT1 - z * ISOMETRIC_HEIGHT2 - y, angle, painter, variant)


class TownObjectType:
    """Store data of some town object type."""

    def __init__(self):
        pass


def turnMatrix(blocks: Tuple[Tuple[Any]], angle: int) -> Tuple[Tuple[Any]]:
    """Turn matrix of Blocks on changed angle (in degrees)"""

    # blocks is a matrix, so its height is the length of blocks[0]
    height = len(blocks[0])

    if angle == 0:
        return blocks
    elif angle == 90:
        return tuple(tuple(blocks[-j - 1][i] for j in range(len(blocks))) for i in range(height))
    elif angle == 180:
        return tuple(tuple(blocks[-i - 1][-j - 1] for j in range(height))
                     for i in range(len(blocks)))
    else:
        return tuple(tuple(blocks[j][-i - 1] for j in range(len(blocks))) for i in range(height))


class TownObject:
    """Object of Town."""

    def __init__(self, x: int, y: int, angle: int, town: 'Town'):
        if angle not in {0, 90, 180, 270}:
            raise AttributeError("Angle must be 0, 90, 180 or 270, not", angle)

        self.x = x
        self.y = y
        self.angle = angle
        self.town = town


class Road(TownObject):
    """Roads. They have to be pretty..."""

    def __init__(self, town: 'Town', x: int, y: int, road_type: RoadType):
        super().__init__(x, y, 0, town)
        self.road_type = road_type
        town.chunks[x // 16][y // 16].roads[x % 16][y % 16] = self

    def draw(self, painter: QPainter, x: int, y: int) -> None:
        textures = self.road_type.textures

        painter.drawImage((self.x - self.y - .5) * ISOMETRIC_WIDTH - x,
                          (self.x + self.y + .5) * ISOMETRIC_HEIGHT1 - y, textures['center'])

        if self.town.getRoad(self.x, self.y - 1) is not None:
            painter.drawImage((self.x - self.y) * ISOMETRIC_WIDTH - x,
                              (self.x + self.y + .25) * ISOMETRIC_HEIGHT1 - y, textures['right-up'])

        if self.town.getRoad(self.x, self.y + 1) is not None:
            painter.drawImage((self.x - self.y - .75) * ISOMETRIC_WIDTH - x,
                              (self.x + self.y + 1) * ISOMETRIC_HEIGHT1 - y, textures['left-down'])

        if self.town.getRoad(self.x - 1, self.y) is not None:
            painter.drawImage((self.x - self.y - .75) * ISOMETRIC_WIDTH - x,
                              (self.x + self.y + .25) * ISOMETRIC_HEIGHT1 - y, textures['left-up'])

        if self.town.getRoad(self.x + 1, self.y) is not None:
            painter.drawImage((self.x - self.y) * ISOMETRIC_WIDTH - x,
                              (self.x + self.y + 1) * ISOMETRIC_HEIGHT1 - y, textures['right-down'])


class ProjectedRoad:
    def __init__(self, town: 'Town', road_type: RoadType = RoadTypes.road):
        self.town = town
        self.road_type = road_type
        coords = isometric(town.cam_x, town.cam_y)
        self.x = round(coords.x())
        self.y = round(coords.y())
        self._addToMap()

    def _delFromMap(self) -> None:
        if self.town.chunks[self.x // 16][self.y // 16].roads[self.x % 16][self.y % 16] is self:
            self.town.chunks[self.x // 16][self.y // 16].roads[self.x % 16][self.y % 16] = None

    def _addToMap(self) -> None:
        if self.town.isBlockEmpty(self.x, self.y, 0, False):
            self.town.chunks[self.x // 16][self.y // 16].roads[self.x % 16][self.y % 16] = self

    def addToMap(self, iso: QPointF) -> None:
        self._delFromMap()
        self.x = round(iso.x())
        self.y = round(iso.y())
        self._addToMap()

    def build(self) -> bool:
        self._delFromMap()
        if self.town.isBlockEmpty(self.x, self.y, 0, False):
            Road(self.town, self.x, self.y, self.road_type)
            return True
        return False

    def destroy(self) -> None:
        self._delFromMap()
        del self

    def draw(self, painter: QPainter, x: int, y: int) -> None:
        Road.draw(self, painter, x, y)


class Building(TownObject):
    """Building class. It only exists. For now."""

    def __init__(self, x: int, y: int, angle: int, town, building_type: BuildingType,
                 blocks_variants: Tuple[Tuple[Tuple[str]]], btype_variant: str):
        super().__init__(x, y, angle, town)
        self.building_type = building_type
        self.btype_variant = btype_variant

        self.blocks = turnMatrix(self.building_type.blocks[btype_variant], angle)
        self.blocks_variants = blocks_variants

        town.buildings.append(self)
        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    if self.blocks[block_x][block_y][block_z] is not None:
                        town.addBlock(x + block_x, y + block_y, block_z, self)

    def destroy(self) -> None:
        """Destroy building."""

        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    self.town.removeBlock(self.x + block_x, self.y + block_y, block_z)
        self.town.buildings.remove(self)
        del self

    def getBlock(self, x: int, y: int, z: int) -> Tuple[Block, int, str]:
        """Data of block on global position x, y, z."""

        return (
            self.blocks[x - self.x][y - self.y][z],
            self.angle,
            self.blocks_variants[x - self.x][y - self.y][z],
        )


class ProjectedBuilding:
    """Building which player's projecting to build."""

    def __init__(self, town: 'Town', building_type: BuildingType = BuildingTypes.getByNumber(0)):
        self._building_type = building_type
        self._angle = 0
        self.blocks = None
        self._btype_variant = None
        self.blocks_variants = None
        self.generateVariants()
        self.town = town
        coords = isometric(town.cam_x, town.cam_y)
        self.x = round(coords.x())
        self.y = round(coords.y())
        self.town.setBuildingMaskForGroup(self.group())

    def _addNewBlocks(self):
        for x in range(len(self.blocks)):
            for y in range(len(self.blocks[0])):
                for z in range(len(self.blocks[x][y])):
                    if self.town.isBlockEmpty(x + self.x, y + self.y, z):
                        self.town.addBlock(x + self.x, y + self.y, z, self)

    def addToMap(self, iso: QPointF) -> None:
        for x in range(len(self.blocks)):
            for y in range(len(self.blocks[0])):
                for z in range(len(self.blocks[x][y])):
                    if self.town.isBlockEmpty(x + self.x, y + self.y, z):
                        self.town.removeBlock(x + self.x, y + self.y, z)
                    if self.town.isBlockEmpty(x + round(iso.x()), y + round(iso.y()), z):
                        self.town.addBlock(x + round(iso.x()), y + round(iso.y()), z, self)

        self.x = round(iso.x())
        self.y = round(iso.y())

    def group(self):
        return self._building_type.group

    def center(self) -> Tuple[int, int]:
        """Center of building."""

        return self.x + len(self.blocks) // 2, self.y + len(self.blocks[0]) // 2

    def doorCheck(self) -> bool:
        for x in range(self.x - 1, self.x + len(self.blocks) + 1):
            for y in range(self.y - 1, self.y + len(self.blocks[0]) + 1):
                if self.town.getBuilding(x, y) is not None:
                    block, angle, variant = self.town.getBuilding(x, y).getBlock(x, y, 0)
                    for mx, my in block.placesThatMustBeEmpty(angle, x, y, variant):
                        if self.town.getBuilding(mx, my) is not None:
                            return False
        return True

    def getBlock(self, x: int, y: int, z: int) -> Tuple[Block, int, str]:
        """Data of block on global position x, y, z."""

        return (
            self.blocks[x - self.x][y - self.y][z],
            self._angle,
            self.blocks_variants[x - self.x][y - self.y][z],
        )

    def build(self) -> bool:
        """Build projecting building."""

        if self.town.isBlocksEmpty(self.x, self.y, self.blocks, False) and self.doorCheck() and \
                self.town.isNearBuildingWithGroup(self.group(), self.center()):
            self._delOldBlocks()
            Building(
                self.x,
                self.y,
                self._angle,
                self.town,
                self._building_type,
                self.blocks_variants,
                self._btype_variant
            )
            self.generateVariants()
            self.town.setBuildingMaskForGroup(self.group())
            return True
        return False

    def destroy(self) -> None:
        """Destroy projecting building."""

        self._delOldBlocks()
        self.town.setBuildingMaskForGroup()
        del self

    def _delOldBlocks(self) -> None:
        for x in range(len(self.blocks)):
            for y in range(len(self.blocks[0])):
                for z in range(len(self.blocks[x][y])):
                    if self.town.isBlockEmpty(x + self.x, y + self.y, z):
                        self.town.removeBlock(x + self.x, y + self.y, z)

    def generateVariants(self) -> None:
        """Generate appearance of projecting building."""

        self._btype_variant, self.blocks_variants = self._building_type.generateVariant()
        self.blocks_variants = turnMatrix(self.blocks_variants, self._angle)
        self.blocks = turnMatrix(self._building_type.blocks[self._btype_variant], self._angle)

    def setBuildingType(self, building_type: BuildingType) -> None:
        """Change building type of projecting buildings."""

        self._delOldBlocks()
        self._building_type = building_type
        self.generateVariants()
        self.town.setBuildingMaskForGroup(self.group())
        self._addNewBlocks()

    def turn(self, delta_angle: int) -> None:
        """Turn projecting building on changed angle"""

        if delta_angle not in {90, -90}:
            raise AttributeError(f"Buildings can turn on 90 or -90 degrees, not {delta_angle}")

        self._delOldBlocks()
        self._angle = (self._angle + delta_angle) % 360
        self.blocks = turnMatrix(self.blocks, delta_angle % 360)
        self.blocks_variants = turnMatrix(self.blocks_variants, delta_angle % 360)
        self._addNewBlocks()


class Town:
    def __init__(self):
        self.cam_x = 0.0  # |
        self.cam_y = 0.0  # | - position of camera.
        self.cam_z = 1.0  # |
        self.scale = 1.0

        self.chosen_building = None
        self.chosen_btype = 0
        self.projecting_road = None

        self.buildings = []
        # Generate 256 initial chunks.
        self.chunks = [[Chunk(i, j) for j in range(16)] for i in range(16)]

    def addBlock(self, x: int, y: int, z: int, building: Building) -> None:
        if 0 <= x <= 255 and 0 <= y <= 255:
            self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = building

    def draw(self, painter: QPainter, size: QSize, projecting_opacity: float, builded_opacity: float = 1) -> None:
        """Draw town on screen with changed size."""

        if not (0 <= projecting_opacity <= 1):
            raise AttributeError(f"Opacity must be between 0 and 1, not {projecting_opacity}.")

        x = int(self.cam_x - (self.cam_z * size.width()) / 2)
        y = int(self.cam_y - (self.cam_z * size.height()) / 2)

        painter.save()
        painter.scale(self.scale, self.scale)
        for chunks in self.chunks:
            for chunk in chunks:
                if self._isChunkVisible(chunk, size):
                    chunk.draw(painter, x, y, projecting_opacity, builded_opacity)

        painter.restore()

    def isBlocksEmpty(self, iso_x: int, iso_y: int, blocks: Tuple[Tuple[Tuple[Block]]],
                      road_is_not_block: bool = True) -> bool:
        for y in range(len(blocks[0])):
            for x in range(len(blocks)):
                for z in range(len(blocks[x][y])):
                    if blocks[x][y][z] is not None and not self.isBlockEmpty(
                            x + iso_x,
                            y + iso_y,
                            z,
                            road_is_not_block
                    ):
                        return False
        return True

    def isBlockEmpty(self, x: int, y: int, z: int, road_is_not_block: bool = True) -> bool:
        """Check for buildings on position x, y, z."""

        if 0 <= x <= 255 and 0 <= y <= 255 and 0 <= z <= 4:
            return (not isinstance(self.getBuilding(x, y, z), Building)) and \
                   (road_is_not_block or z != 0 or not isinstance(self.getRoad(x, y), Road))
        return True

    def _isChunkVisible(self, chunk: Chunk, size: QSize) -> bool:
        x = int(self.cam_x - (self.cam_z * size.width()) / 2)
        y = int(self.cam_y - (self.cam_z * size.height()) / 2)
        return (-16 * ISOMETRIC_WIDTH <= ((chunk.x - chunk.y) * ISOMETRIC_WIDTH - x) <=
                size.width() * self.cam_z + 16 * ISOMETRIC_WIDTH and
                -32 * ISOMETRIC_HEIGHT1 <= ((chunk.x + chunk.y) * ISOMETRIC_HEIGHT1 - y) <=
                size.height() * self.cam_z)

    def isNearBuildingWithGroup(self, group: int, point: Tuple[int, int]) -> bool:
        """Check for buildings in radius equel group max distance."""

        is_group_exist = False
        for building in self.buildings:
            if building.building_type.group == group:
                is_group_exist = True
        if not is_group_exist:
            return True

        radius = BuildingGroups.distances[group]
        for x, y in self.manhattanCircle(point, radius):
            if not self.isBlockEmpty(x, y, 0) and self.getBuilding(x, y).building_type.group == group:
                return True
        return False

    def getBuilding(self, x: int, y: int, z: int = 0) -> Building:
        """Building on position x, y, z."""

        if 0 <= x <= 255 and 0 <= y <= 255 and 0 <= z <= 4:
            return self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z]

    def getRoad(self, x: int, y: int) -> Road:
        if 0 <= x <= 255 and 0 <= y <= 255:
            return self.chunks[x // 16][y // 16].roads[x % 16][y % 16]

    def removeBlock(self, x: int, y: int, z: int) -> None:
        """Remove Building from position x, y, z."""

        if 0 <= x <= 255 and 0 <= y <= 255 and 0 <= z <= 4:
            self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = None

    def scaleByEvent(self, event: QWheelEvent) -> None:
        """Change zoom."""

        delta = -event.angleDelta().y() / (self.scale * 480)
        if 0.5 <= self.cam_z + delta <= 3:
            self.cam_z += delta
            self.scale = 1 / self.cam_z

    def setBuildingMaskForGroup(self, group: str = None) -> None:
        """Add green front light on places building with changed group."""

        for chunks in self.chunks:
            for chunk in chunks:
                chunk.with_mask = set()

        if group is None:
            return

        is_group_exist = False

        radius = BuildingGroups.distances[group]
        for building in self.buildings:
            if building.building_type.group == group:
                is_group_exist = True
                for i in range(building.x, building.x + len(building.blocks)):
                    for j in range(building.y, building.y + len(building.blocks[0])):
                        if self.getBuilding(i, j) is not None:
                            for x, y in self.manhattanCircle((i, j), radius):
                                self.chunks[x // 16][y // 16].with_mask.add((x % 16, y % 16))

        if not is_group_exist:
            for chunks in self.chunks:
                for chunk in chunks:
                    chunk.with_mask = {(i, j) for j in range(16) for i in range(16)}

    # TODO saving

    def tick(self, screen: QSize) -> None:
        for chunks in self.chunks:
            for chunk in chunks:
                if self._isChunkVisible(chunk, screen):
                    for x in range(16):
                        for y in range(16):
                            for citizen in chunk.citizens[x][y]:
                                citizen.step()

    def translate(self, delta: QPoint) -> None:
        """Translate camera."""

        self.cam_x -= delta.x() * self.cam_z
        self.cam_y -= delta.y() * self.cam_z

    @staticmethod
    def manhattanCircle(center: Tuple[int, int], radius: int) -> Set[Tuple[int, int]]:
        """All integer points inside a Manhattan circle with changed center and radius."""

        answer = set()
        for x_abs in range(radius + 1):
            for y_abs in range(radius - x_abs + 1):
                answer.update({
                    (x_abs + center[0], y_abs + center[1]), (x_abs + center[0], -y_abs + center[1]),
                    (-x_abs + center[0], y_abs + center[1]), (-x_abs + center[0], -y_abs + center[1])
                })
        return answer


class Citizen:
    """Citizen of building. He walks."""

    def __init__(self, building: Building):
        self.building = building
        self.x = building.x + len(building.blocks) + .5
        self.y = building.y + len(building.blocks[0]) + .5
        self._addToMap()

    def _addToMap(self) -> None:
        insort(self.building.town.chunks[int(self.x // 16)][int(self.y // 16)].citizens[int(self.x % 16)][
                    int(self.y % 16)], self)

    def _delFromOldPosition(self) -> None:
        pos = self.building.town.chunks[int(self.x // 16)][int(self.y // 16)].citizens[int(self.x % 16)][
                    int(self.y % 16)]
        pos.pop(bisect(pos, self) - 1)

    def __gt__(self, other) -> bool:
        return (self.y, self.x) > (other.y, other.x)

    def draw(self, painter: QPainter, x: int, y: int) -> None:
        painter.drawImage((self.x - self.y) * ISOMETRIC_WIDTH - 22 - x,
                          (self.x + self.y) * ISOMETRIC_HEIGHT1 - 53 - y, getImage("human"))

    def step(self):
        self._delFromOldPosition()
        self.x += randint(0, 1) * .2
        self.y += randint(0, 1) * .2
        self._addToMap()
