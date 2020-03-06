from resources_manager import getImage

from PyQt5.QtGui import QPainter

from json import load
from random import choice


ISOMETRIC_WIDTH = 64    # |
ISOMETRIC_HEIGHT1 = 64  # | textures parameters
ISOMETRIC_HEIGHT2 = 79  # |

BLOCKS_DATA = load(open('blocks.json'))


def matrixHeight(matrix: ((object, ...), ...)) -> int:
    return max([len(blocks_y) for blocks_y in matrix])


class Block:
    """Store data of block."""

    def __init__(self, name: str):
        sides = ("NORTH", "WEST", "SOUTH", "EAST")
        self.variants = {i: {j * 90: (getImage(f'{BLOCKS_DATA[name][i][sides[(4 - j) % 4]]}_left'),
                                      getImage(f'{BLOCKS_DATA[name][i][sides[(5 - j) % 4]]}_right'))
                             for j in range(4)} for i in BLOCKS_DATA[name]}

    def draw(self, x: float, y: float, angle: int, painter: QPainter, variant: str) -> None:
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
    """Store data of ground."""

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


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: {str: (((Block, ...), ...), ...)}, possible_variants: {str: ((((str, ...), ...), ...), ...)} = None):
        self.blocks = {}
        self.possible_variants = possible_variants
        if possible_variants is None:
            pass
            # TODO !!!!!!
        for variant in blocks:
            height = matrixHeight(blocks[variant])
            # convert blocks to rectangular matrix
            self.blocks[variant] = tuple([blocks_y + ((None,), ) * (height - len(blocks_y))
                                          for blocks_y in blocks[variant]])

    def generateVariant(self) -> (str, (((str, ...), ...), ...)):
        btype_variant = choice(list(self.blocks))
        return btype_variant, tuple(
            tuple(
                tuple(choice(self.possible_variants[btype_variant][x][y][z]) if block else None
                      for block in self.blocks[btype_variant][x][y])
                for y in range(matrixHeight(self.blocks[btype_variant])))
            for x in range(len(self.blocks[btype_variant])))


loaded_bt_data = load(open('building_types.json'))
BUILDING_TYPES_DATA = loaded_bt_data.copy()

for item in loaded_bt_data:
    for variant in loaded_bt_data[item]['blocks']:
        for x in range(len(loaded_bt_data[item]['blocks'][variant])):
            for y in range(len(loaded_bt_data[item]['blocks'][variant][x])):
                for z in range(len(loaded_bt_data[item]['blocks'][variant][x][y])):
                    data = loaded_bt_data[item]['blocks'][variant][x][y][z]
                    BUILDING_TYPES_DATA[item]['blocks'][variant][x][y][z] = \
                        Blocks.__getattr__(
                            loaded_bt_data[item]['blocks'][variant][x][y][z])


class BuildingTypeManager:
    """Store all BuildingTypes.
       Use BuildingTypes.bt_name to get BuildingType called 'bt_name'.
       Use BuildingType.getByNumber(num) to get BuildingType with number 'num'."""

    building_types = {item: BuildingType({
        variant:
            tuple((
                tuple((
                    tuple(block_y) for block_y in blocks_x
                )) for blocks_x in BUILDING_TYPES_DATA[item]['blocks'][variant]
            )) for variant in BUILDING_TYPES_DATA[item]['blocks']
    }) for item in BUILDING_TYPES_DATA}
    sorted_names = sorted(building_types)

    def getByNumber(self, number: int) -> BuildingType:
        return self.__getattr__(self.sorted_names[number])

    def __getattr__(self, item: str):
        if item not in self.building_types:
            raise AttributeError(f'Building type "{item}" does not exests.')

        return self.building_types[item]


BuildingTypes = BuildingTypeManager()
