from PyQt5.Qt import QImage, QPoint, QSize, QWheelEvent
from PyQt5.QtGui import QPainter, QPen

from resources_manager import getImage


class Block:
    def __init__(self, name: str):
        self.sides = {i: getImage(name + str(i)) for i in range(0, 360, 90)}

    def draw(self, x: float, y: float, angle: int, painter: QPainter) -> None:
        painter.drawImage(x - 55, y - 64, self.sides[angle])


class BlocksManager:
    """Store all blocks.
        Use Blocks.block_name to get Block(block_name)."""

    blocks = {name: Block(name) for name in ('block', )}

    def __getattr__(self, item):
        if item in self.blocks:
            return self.blocks[item]
        raise AttributeError('Block "' + item + '" does not exist.')


Blocks = BlocksManager()


class Ground:
    def __init__(self, name: str):
        self.image = getImage(name)

    def draw(self, x: float, y: float, painter: QPainter) -> None:
        painter.drawImage(x - 55, y, self.image)


class GroundsManager:
    """Store all grounds.
        Use Grounds.ground_name to get Ground(ground_name)."""

    grounds = {name: Ground(name) for name in ('grass', )}

    def __getattr__(self, item):
        if item in self.grounds:
            return self.grounds[item]
        raise AttributeError('Ground "' + item + '" does not exist.')


Grounds = GroundsManager()


class Chunk:
    """Store data of blocks in 16 by 16 square"""

    def __init__(self, x: int, y: int):
        self.x = x * 16
        self.y = y * 16
        # Generate matrix 16 by 16 by 3.
        self.blocks = tuple([tuple([[None, None, None]
                                    for j in range(16)]) for i in range(16)])
        self.grounds = tuple([[Grounds.grass for j in range(16)]
                              for i in range(16)])

    def draw(self, painter: QPainter, x: float, y: float) -> None:
        # Draw all grounds.
        for i in range(16):
            for j in range(16):
                self.grounds[i][j].draw((self.x + i - self.y - j) * 55 - x,
                                        (self.x + self.y + i + j) * 32 - y, painter)

        # Draw all blocks in chunk sorted by x, y, z
        for i in range(16):
            for j in range(16):
                for z in range(3):
                    building = self.blocks[i][j][z]
                    if building is not None:
                        block, angle = building.getBlock(i + self.x,
                                                         j + self.y, z)
                        block.draw((self.x + i - self.y - j) * 55 - x,
                                   (self.x + self.y + i + j) * 32 - z * 64 - y, angle, painter)


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


def turnBlocks(blocks: (((Block, ...), ...), ...), angle: int) -> (((Block, ...), ...), ...):

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


building_type1 = BuildingType((((Blocks.block,),),))
building_type2 = BuildingType(
    (((Blocks.block, Blocks.block), (Blocks.block,)),)
)


class TownObject:
    def __init__(self, x: int, y: int, angle: int, town, object_type: TownObjectType):
        if angle not in {0, 90, 180, 270}:
            raise AttributeError('Angle must be 0, 90, 180 or 270, not', angle)

        self.x = x
        self.y = y
        self.angle = angle
        self.town = town


class Building(TownObject):
    def __init__(self, x: int, y: int, angle: int, town, building_type: BuildingType):
        super().__init__(x, y, angle, town, building_type)
        self.building_type = building_type

        self.blocks = turnBlocks(self.building_type.blocks, angle)

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
        return self.blocks[x - self.x][y - self.y][z], self.angle


class ProjectedBuilding:
    """Building which player's projecting to build."""

    def __init__(self, building_type: BuildingType):
        self.building_type = building_type

    def draw(self, hx: int, hy: int, angle: int, cam_x: float, cam_y: float,
             painter: QPainter) -> None:
        blocks = turnBlocks(self.building_type.blocks, angle)
        height = len(blocks[0])

        old_painter_opacity = painter.opacity()
        painter.setOpacity(.7)

        for block_y in range(height):
            for block_x in range(len(blocks)):
                for block_z in range(len(blocks[block_x][block_y])):
                    block = blocks[block_x][block_y][block_z]
                    if block is not None:
                        block.draw((hx + block_x - block_y - hy) * 55 - cam_x,
                                   (hx + hy + block_x + block_y) * 32
                                   - block_z * 64 - cam_y,
                                   angle, painter)

        painter.setOpacity(old_painter_opacity)

    def build(self, x: int, y: int, angle: int, town) -> None:
        # x // 55 = town_x - town_y
        # y // 32 = town_x + town_y
        pass

    def destroy(self) -> None:
        del self


class Town:
    def __init__(self):
        self.cam_x = 0.0  # |
        self.cam_y = 0.0  # | - position of camera.
        self.cam_z = 2.0  # |
        self.scale = .5
        # Generate 256 initial chunks.
        self.buildings = []
        self.chunks = [[Chunk(i, j) for j in range(16)] for i in range(16)]

    def addBlock(self, x: int, y: int, z: int, building: Building) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = building

    def removeBlock(self, x: int, y: int, z: int) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = None

    def draw(self, painter: QPainter, size: QSize) -> None:
        x = self.cam_x - (self.cam_z * size.width()) // 2
        y = self.cam_y - (self.cam_z * size.height()) // 2

        painter.scale(self.scale, self.scale)
        for chunks in self.chunks:
            for chunk in chunks:
                if -880 < ((chunk.x - chunk.y) * 55 - x) < size.width() * self.cam_z + 880 and \
                   -1024 < ((chunk.x + chunk.y) * 32 - y) < size.height() * self.cam_z:
                    chunk.draw(painter, x, y)
        painter.scale(self.cam_z, self.cam_z)

    def scaleByEvent(self, event: QWheelEvent) -> None:
        delta = - event.angleDelta().y() / (self.scale * 480)
        if .5 <= self.cam_z + delta <= 2.5:
            self.cam_z += delta
            self.scale = 1 / self.cam_z

    def translate(self, delta: QPoint) -> None:
        self.cam_x -= delta.x() * self.cam_z
        self.cam_y -= delta.y() * self.cam_z
