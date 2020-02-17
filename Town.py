from PyQt5.QtGui import QPainter, QPen
from PyQt5.Qt import QImage, QSize, QPoint, QWheelEvent

from resources_manager import getImage


class Block:
    def __init__(self, name: str):
        self.sides = {i: getImage(name + str(i)) for i in range(0, 360, 90)}

    def draw(self, x: float, y: float, angle: int, painter: QPainter) -> None:
        painter.drawImage(x - 55, y - 64, self.sides[angle])


class BlocksManager:
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


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: (((Block, ...), ...), ...)):
        self.height = max([len(blocks_y) for blocks_y in blocks])
        # make blocks
        self.blocks = tuple([blocks_y + ((None,), ) * (self.height - len(blocks_y))
                             for blocks_y in blocks])


building_type1 = BuildingType((((Blocks.block,),),))
building_type2 = BuildingType(
    (((Blocks.block,),),
     ((Blocks.block, Blocks.block), (Blocks.block,)))
)


class TownObject:
    def __init__(self, x: int, y: int, angle: int, object_type: TownObjectType):
        self.x = x
        self.y = y
        self.angle = angle
        self.object_type = object_type


class Building(TownObject):
    def __init__(self, x: int, y: int, angle: int, town, building_type: BuildingType):
        super().__init__(x, y, angle, building_type)
        # TODO angle must turn all blocks!
        self.building_type = building_type
        if angle == 0:
            self.blocks = self.building_type.blocks
        elif angle == 180:
            self.blocks = tuple([self.building_type.blocks[i][::-1]
                                 for i in range(len(self.building_type.blocks))])[::-1]
        else:
            self.blocks = tuple([tuple([self.building_type.blocks[j][i] for j in range(self.building_type.height)])
                                 for i in range(len(self.building_type.blocks))])
        town.buildings.append(self)
        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    if self.blocks[block_x][block_y][block_z] is not None:
                        town.addBlock(x + block_x, y + block_y, block_z, self)

    def getBlock(self, x: int, y: int, z: int) -> (Block, int):
        return self.blocks[x - self.x][y - self.y][z], self.angle


class Town:
    def __init__(self):
        self.cam_x = 0  # |
        self.cam_y = 0  # | - position of camera.
        self.cam_z = 2  # |
        self.scale = .5
        # Generate 256 initial chunks.
        self.buildings = []
        self.chunks = [[Chunk(i, j) for j in range(16)] for i in range(16)]

    def addBlock(self, x: int, y: int, z: int, building: Building) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = building

    def draw(self, painter: QPainter, size: QSize) -> None:
        x = self.cam_x - (self.cam_z * size.width()) // 2
        y = self.cam_y - (self.cam_z * size.height()) // 2
        painter.scale(self.scale, self.scale)
        for chunks in self.chunks:
            for chunk in chunks:
                if -880 < ((chunk.x - chunk.y) * 55 - x) < size.width() * self.cam_z + 880 and \
                   -1024 < ((chunk.x + chunk.y) * 32 - y) < size.height() * self.cam_z:
                    chunk.draw(painter, x, y)

    def scaleByEvent(self, event: QWheelEvent) -> None:
        delta = - event.angleDelta().y() / (self.scale * 480)
        if .5 <= self.cam_z + delta <= 2.5:
            self.cam_z += delta
            self.scale = 1 / self.cam_z

    def translate(self, delta: QPoint) -> None:
        self.cam_x -= delta.x() * self.cam_z
        self.cam_y -= delta.y() * self.cam_z
