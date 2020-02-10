from PyQt5.QtGui import QPainter, QPen
from PyQt5.Qt import QImage, QSize

from resources_manager import getImage


class Block():
    def __init__(self, name: str):
        self.sides = {i: getImage(name + str(i)) for i in range(0, 360, 90)}

    def draw(self, x: float, y: float, zoom: float, angle: int, painter: QPainter) -> None:
        painter.drawImage(x * zoom, y * zoom, self.sides[angle])


class BlocksManager:
    blocks = {name: Block(name) for name in ('block', )}

    def __getattr__(self, item):
        if item in self.blocks:
            return self.blocks[item]
        raise AttributeError('Block "' + item + '" does not exist.')


Blocks = BlocksManager()


class Chunk:
    """Store data of blocks in 16 by 16 square"""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        # Generate matrix 16 by 16 by 3.
        self.blocks = tuple([tuple([[None, None, None]
                                    for j in range(16)]) for i in range(16)])
        self.grounds = tuple([[None for j in range(16)] for i in range(16)])

    def draw(self, painter: QPainter, x: int, y: int, zoom: float = 1) -> None:
        # Draw all blocks & grounds in chunk sorted by x, y, z
        for i in range(16):
            for j in range(16):
                if self.grounds[i][j] is not None:
                    self.grounds[i][j].draw()
                for z in range(3):
                    building = self.blocks[i][j][z]
                    if building is not None:
                        block, angle = building.getBlock(i + 16 * self.x,
                                                         j + 16 * self.y, z)
                        block.draw((self.x + i) * 111 - x, ((self.y + j) * 128 - z * 64 - y),
                                   zoom, angle, painter)


class TownObjectType:
    """Store data of some town object type."""

    def __init__(self):
        pass


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: (((Block, ...), ...), ...)):
        self.blocks = blocks


building_type1 = BuildingType((((Blocks.block,),),))
building_type2 = BuildingType((((Blocks.block, Blocks.block),),))


class TownObject:
    def __init__(self, x: int, y: int, angle: int, town, object_type: TownObjectType):
        self.x = x
        self.y = y
        self.angle = angle
        self.object_type = object_type


class Building(TownObject):
    def __init__(self, x: int, y: int, angle: int, town, building_type: BuildingType):
        super().__init__(x, y, angle, town, building_type)
        self.blocks = self.object_type.blocks
        for block_x in range(len(self.blocks)):
            for block_y in range(len(self.blocks[block_x])):
                for block_z in range(len(self.blocks[block_x][block_y])):
                    town.addBlock(x + block_x, y + block_y, block_z, self)

    def getBlock(self, x: int, y: int, z: int) -> (Block, int):
        return self.blocks[x - self.x][y - self.y][z], self.angle


class Town:
    def __init__(self):
        self.cam_x = 0  # |
        self.cam_y = 0  # | - position of camera.
        self.cam_z = 2  # |
        # Generate 256 initial chunks.
        self.chunks = [[Chunk(i, j) for j in range(16)] for i in range(16)]

    def addBlock(self, x: int, y: int, z: int, building: Building) -> None:
        self.chunks[x // 16][y // 16].blocks[x % 16][y % 16][z] = building

    def draw(self, painter: QPainter, size: QSize) -> None:
        zoom = 1 / self.cam_z
        painter.scale(zoom, zoom)
        for chunks in self.chunks:
            for chunk in chunks:
                if 0 <= chunk.x * 128 * zoom <= size.width() + 128 * zoom and \
                   0 <= chunk.y * 128 * zoom <= size.height() + 128 * zoom:
                    chunk.draw(painter, self.cam_x, self.cam_y)
