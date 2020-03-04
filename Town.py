from PyQt5.Qt import QImage, QPoint, QPointF, QSize, QWheelEvent
from PyQt5.QtGui import QPainter, QPen

from resources_manager import getImage

from json import load
from random import choice

ISOMETRIC_WIDTH = 64
ISOMETRIC_HEIGHT1 = 64
ISOMETRIC_HEIGHT2 = 79

BLOCKS_DATA = load(open('blocks.json'))


def isometric(x: float, y: float) -> QPointF:
    # (iso_x + iso_y) * (ISOMETRIC_HEIGHT1 / 2) = x
    # (iso_x - iso_y) * ISOMETRIC_WIDTH = y
    return QPointF(((y / (ISOMETRIC_HEIGHT1 / 2)) + (x / ISOMETRIC_WIDTH)),
                   ((y / (ISOMETRIC_HEIGHT1 / 2)) - (x / ISOMETRIC_WIDTH))) / 2


class Block:
    def __init__(self, name: str):
        sides = ("NORTH", "WEST", "SOUTH", "EAST")
        self.variants = {int(i): {j * 90: (getImage(f'{BLOCKS_DATA[name][i][sides[(4 - j) % 4]]}_left'),
                                           getImage(f'{BLOCKS_DATA[name][i][sides[(5 - j) % 4]]}_right'))
                                  for j in range(4)} for i in BLOCKS_DATA[name]}

    def draw(self, x: float, y: float, angle: int, painter: QPainter, variant: int = 0) -> None:
        painter.drawImage(x - ISOMETRIC_WIDTH, y -
                          ISOMETRIC_HEIGHT2, self.variants[variant][angle][0])
        painter.drawImage(x, y - ISOMETRIC_HEIGHT2,
                          self.variants[variant][angle][1])


class BlocksManager:
    """Store all blocks.
        Use Blocks.block_name to get Block(block_name)."""

    blocks = {name: Block(name) for name in BLOCKS_DATA}

    def __getattr__(self, item):
        if item in self.blocks:
            return self.blocks[item]
        raise AttributeError(f'Block "{item}" does not exist.')


Blocks = BlocksManager()


class Ground:
    def __init__(self, name: str):
        self.image = getImage(name)

    def draw(self, x: float, y: float, painter: QPainter) -> None:
        painter.drawImage(x - ISOMETRIC_WIDTH, y, self.image)


class GroundsManager:
    """Store all grounds.
        Use Grounds.ground_name to get Ground(ground_name)."""

    grounds = {name: Ground(name) for name in ('grass', )}

    def __getattr__(self, item):
        if item in self.grounds:
            return self.grounds[item]
        raise AttributeError(f'Ground "{item}" does not exist.')


Grounds = GroundsManager()


class Chunk:
    """Store data of blocks in 16 by 16 square"""

    def __init__(self, x: int, y: int):
        self.x = x * 16
        self.y = y * 16
        # Generate matrix 16 by 16 by 3.
        self.is_empty = True
        self.blocks = tuple([tuple([[None] * 4
                                    for j in range(16)]) for i in range(16)])
        self.grounds = tuple([[Grounds.grass for j in range(16)]
                              for i in range(16)])

    def draw(self, painter: QPainter, x: float, y: float) -> None:
        # Draw all grounds.
        for i in range(16):
            for j in range(16):
                self.grounds[i][j].draw((self.x + i - self.y - j) * ISOMETRIC_WIDTH - x,
                                        (self.x + self.y + i + j) * (ISOMETRIC_HEIGHT1 / 2) - y, painter)

        if self.is_empty:
            return

        # Draw all blocks in chunk sorted by x, y, z
        for i in range(16):
            for j in range(16):
                for z in range(3):
                    building = self.blocks[i][j][z]
                    if building is not None:
                        block, angle, variant = building.getBlock(i + self.x,
                                                                  j + self.y, z)
                        block.draw((self.x + i - self.y - j) * ISOMETRIC_WIDTH - x,
                                   (self.x + self.y + i + j) *
                                   (ISOMETRIC_HEIGHT1 / 2) -
                                   z * ISOMETRIC_HEIGHT2 - y,
                                   angle, painter, variant)


class TownObjectType:
    """Store data of some town object type."""

    def __init__(self):
        pass


def matrixHeight(matrix: ((object, ...), ...)) -> int:
    return max([len(blocks_y) for blocks_y in matrix])


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: (((Block, ...), ...), ...)):
        height = matrixHeight(blocks)
        # convert blocks to rectangular matrix
        self.blocks = tuple([blocks_y + ((None,), ) * (height - len(blocks_y))
                             for blocks_y in blocks])


class BuildingTypeManager:

    building_types = {'building_type1': BuildingType((((Blocks.home_door, Blocks.roof),),)),
                      'building_type2': BuildingType(
        (((Blocks.home_door, Blocks.home, Blocks.roof),
          (Blocks.home, Blocks.roof)),)
    )
    }

    sorted_names = sorted(building_types)

    def getByNumber(self, number: int) -> BuildingType:
        return self.__getattr__(self.sorted_names[number])

    def __getattr__(self, item: str):
        if item not in self.building_types:
            raise AttributeError(f'Building type "{item}" does not exests.')

        return self.building_types[item]


BuildingTypes = BuildingTypeManager()


def turnBlocks(blocks: (((Block, ...), ...), ...), angle: int) -> (((Block, ...), ...), ...):
    """Turn matrix of Blocks (with angle 0 degrees) on angle (in degrees)"""

    # blocks is rectangular matrix, so its height is len of blocks[0]
    height = len(blocks[0])

    if angle == 0:
        return blocks
    elif angle == 90:
        # blocks[i][j] is building_type.blocks[j][i]
        return tuple([tuple([blocks[j][i] for j in range(len(blocks))])
                      for i in range(height)])
    elif angle == 180:
        return tuple([blocks[i][::-1]
                      for i in range(len(blocks))])[::-1]
    else:
        return tuple([tuple([blocks[-j - 1][-i - 1] for j in range(len(blocks))])
                      for i in range(height)])


class TownObject:
    def __init__(self, x: int, y: int, angle: int, town, object_type: TownObjectType):
        if angle not in {0, 90, 180, 270}:
            raise AttributeError('Angle must be 0, 90, 180 or 270, not', angle)

        self.x = x
        self.y = y
        self.angle = angle
        self.town = town


class Building(TownObject):
    def __init__(self, x: int, y: int, angle: int, town, building_type: BuildingType, blocks_variants: (((int, ...), ...), ...)):
        super().__init__(x, y, angle, town, building_type)
        self.building_type = building_type

        self.blocks = turnBlocks(self.building_type.blocks, angle)
        self.blocks_variants = blocks_variants

        town.buildings.append(self)
        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    if self.blocks[block_x][block_y][block_z] is not None:
                        town.addBlock(x + block_x, y +
                                      block_y, block_z, self)

    def destroy(self) -> None:
        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    self.town.removeBlock(
                        self.x + block_x, self.y + block_y, block_z)
        self.town.buildings.remove(self)
        del self

    def getBlock(self, x: int, y: int, z: int) -> (Block, int):
        return (self.blocks[x - self.x][y - self.y][z], self.angle,
                self.blocks_variants[x - self.x][y - self.y][z])


class ProjectedBuilding:
    """Building which player's projecting to build."""

    # TODO more comfortable chosing of type.

    def __init__(self, town, building_type: BuildingType):
        self._building_type = building_type
        self.blocks = building_type.blocks
        self._blocks_variants = None
        self.generateVariants()
        self.blocks_variants = self._blocks_variants
        self.town = town
        self.isometric = isometric(town.cam_x, town.cam_y)
        self._angle = 0

    def draw(self, painter: QPainter, screen_size: QSize) -> None:
        height = len(self.blocks[0])
        iso_x = round(self.isometric.x())
        iso_y = round(self.isometric.y())
        painter.scale(self.town.scale, self.town.scale)
        painter.setOpacity(.9)

        for block_y in range(height):
            for block_x in range(len(self.blocks)):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    block = self.blocks[block_x][block_y][block_z]
                    if block is not None:
                        block.draw((iso_x + block_x - block_y - iso_y) * ISOMETRIC_WIDTH - self.town.cam_x +
                                   self.town.cam_z * screen_size.width() / 2,
                                   (iso_x + iso_y + block_x + block_y) * (ISOMETRIC_HEIGHT1 / 2) - self.town.cam_y -
                                   block_z * ISOMETRIC_HEIGHT2 + screen_size.height() * self.town.cam_z / 2,
                                   self._angle, painter, self.blocks_variants[block_x][block_y][block_z])

    def getAngle(self):
        return self._angle

    def build(self) -> None:
        Building(round(self.isometric.x()), round(self.isometric.y()),
                 self._angle, self.town, self._building_type, self.blocks_variants)
        self.destroy()

    def destroy(self) -> None:
        del self

    def generateVariants(self):
        self._blocks_variants = tuple([
            tuple([
                tuple([choice(list(block.variants)) if block else None
                       for block in self._building_type.blocks[x][y]])
                for y in range(matrixHeight(self._building_type.blocks))])
            for x in range(len(self._building_type.blocks))])

    def setBuildingType(self, building_type: BuildingType) -> None:
        self._building_type = building_type
        self.blocks = turnBlocks(self._building_type.blocks, self._angle)
        self.generateVariants()
        self.blocks_variants = turnBlocks(self._blocks_variants, self._angle)

    def turn(self, delta_angle: int) -> None:
        if delta_angle not in {90, -90}:
            raise AttributeError(
                f'Buildings can turn on 90 or -90 degrees, not {delta_angle}')

        self._angle = (self._angle + delta_angle) % 360
        self.blocks = turnBlocks(self._building_type.blocks, self._angle)
        self.blocks_variants = turnBlocks(self._blocks_variants, self._angle)


class Town:
    def __init__(self):
        self.cam_x = 0.0  # |
        self.cam_y = 0.0  # | - position of camera.
        self.cam_z = 1.0  # |
        self.scale = 1.0

        self.buildings = []
        # Generate 256 initial chunks.
        self.chunks = [[Chunk(i, j) for j in range(16)] for i in range(16)]

    def addBlock(self, x: int, y: int, z: int, building: Building) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = building
        self.chunks[x // 16][y // 16].is_empty = False

    def draw(self, painter: QPainter, size: QSize) -> None:
        x = self.cam_x - (self.cam_z * size.width()) // 2
        y = self.cam_y - (self.cam_z * size.height()) // 2

        painter.scale(self.scale, self.scale)
        for chunks in self.chunks:
            for chunk in chunks:
                if -16 * ISOMETRIC_WIDTH < ((chunk.x - chunk.y) * ISOMETRIC_WIDTH - x) < size.width() * self.cam_z + 16 * ISOMETRIC_WIDTH and \
                   -32 * ISOMETRIC_HEIGHT1 / 2 < ((chunk.x + chunk.y) * (ISOMETRIC_HEIGHT1 / 2) - y) < size.height() * self.cam_z:
                    chunk.draw(painter, x, y)
        painter.scale(self.cam_z, self.cam_z)

    def isBlocksEmpty(self, iso_x: int, iso_y: int, blocks: (((Block, ...), ...), ...)) -> bool:
        for y in range(len(blocks[0])):
            for x in range(len(blocks)):
                for z in range(len(blocks[x][y])):
                    if blocks[x][y][z] is not None and not self.isBlockEmpty(x + iso_x, y + iso_y, z):
                        return False
        return True

    def isBlockEmpty(self, x: int, y: int, z: int) -> bool:
        return self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] is None

    def removeBlock(self, x: int, y: int, z: int) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = None
        self.chunks[x // 16][y // 16].is_empty = (self.chunks[x // 16][y // 16].blocks
                                                  == tuple([tuple([[None] * 4 for j in range(16)]) for i in range(16)]))

    def scaleByEvent(self, event: QWheelEvent) -> None:
        delta = - event.angleDelta().y() / (self.scale * 480)
        if .5 <= self.cam_z + delta <= 3:
            self.cam_z += delta
            self.scale = 1 / self.cam_z

    # TODO saving of Town

    def translate(self, delta: QPoint) -> None:
        self.cam_x -= delta.x() * self.cam_z
        self.cam_y -= delta.y() * self.cam_z
