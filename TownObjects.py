from json import load
from random import choice
from typing import Any, Dict, List, Optional, Set, Tuple

from PyQt5.Qt import QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap

from resources_manager import getImage, getJSON

ISOMETRIC_WIDTH = 64    # |
ISOMETRIC_HEIGHT1 = 32  # | textures parameters
ISOMETRIC_HEIGHT2 = 79  # |

BLOCKS_DATA = getJSON("blocks")
GROUNDS_DATA = getJSON("grounds")
BUILDING_TYPES_DATA = getJSON("building_types")
ROAD_TYPES_DATA = getJSON('roads_types')
GROUPS_DATA = getJSON("buildings_groups")


def matrixHeight(matrix: Tuple[Tuple[Any]]) -> int:
    """Max height of matrix."""

    return max([len(blocks_y) for blocks_y in matrix])


def matrix3DHeight(matrix: Tuple[Tuple[Tuple[Any]]]) -> int:
    return max(max(len(data_ij) for data_ij in data_i) for data_i in matrix)


class Block:
    """Store data of block."""

    def __init__(self, name: str):
        self.name = name

        sides = ("NORTH", "WEST", "SOUTH", "EAST")
        self.variants = {
            variant: {
                angle * 90: (
                    getImage(f"blocks/{BLOCKS_DATA[name][variant].get(sides[(4 - angle) % 4], 'NULL')}_left", True),
                    getImage(f"blocks/{BLOCKS_DATA[name][variant].get(sides[(5 - angle) % 4], 'NULL')}_right", True),
                    getImage(
                        f"blocks/{BLOCKS_DATA[name][variant].get(sides[(6 - angle) % 4], 'NULL')}_right_back", True),
                    getImage(f"blocks/{BLOCKS_DATA[name][variant].get(sides[(7 - angle) % 4], 'NULL')}_left_back", True)
                )
                for angle in range(4)
            }
            for variant in BLOCKS_DATA[name]
        }

        self.empty = {
            variant:
                tuple(sides.index(side) * 90 for side in BLOCKS_DATA[name][variant].get('empty', []))
            for variant in BLOCKS_DATA[name]
        }

    def __repr__(self):
        return f"Block {self.name}"

    def __str__(self):
        return f"Block {self.name}"

    def draw(self, x: int, y: int, angle: int, painter: QPainter, variant: str) -> None:
        if variant not in self.variants:
            raise AttributeError(f"Block called {self.name} has not variant {variant}.")

        painter.drawImage(x - ISOMETRIC_WIDTH, y - ISOMETRIC_HEIGHT2 -
                          ISOMETRIC_HEIGHT1, self.variants[variant][angle][3])
        painter.drawImage(x, y - ISOMETRIC_HEIGHT2 - ISOMETRIC_HEIGHT1, self.variants[variant][angle][2])
        painter.drawImage(x - ISOMETRIC_WIDTH, y - ISOMETRIC_HEIGHT2, self.variants[variant][angle][0])
        painter.drawImage(x, y - ISOMETRIC_HEIGHT2, self.variants[variant][angle][1])

    def placesThatMustBeEmpty(self, angle: int, x: int, y: int, variant: str) -> Set[Tuple[int, int]]:
        answer = set()
        for side in self.empty[variant]:
            side = (side + angle) % 360
            if side == 0:
                answer.add((x, y + 1))
            elif side == 90:
                answer.add((x + 1, y))
            elif side == 180:
                answer.add((x, y - 1))
            else:
                answer.add((x - 1, y))
        return answer


class BlocksManager:
    """Store all blocks.
        Use Blocks.block_name to get Block(block_name)."""

    blocks = {name: Block(name) for name in BLOCKS_DATA}

    def __getattr__(self, item):
        if item in self.blocks:
            return self.blocks[item]
        raise AttributeError(f'Block "{item}" does not exist.')


Blocks = BlocksManager()  # it have to be here because BuildingsTypesManager uses it


class Ground:
    """Store data of ground."""

    def __init__(self, data: Dict[str, str]):
        self.texture = getImage(data['texture'])

    def draw(self, x: float, y: float, painter: QPainter) -> None:
        painter.drawImage(x - ISOMETRIC_WIDTH, y, self.texture)


class GroundsManager:
    """Store all grounds.
        Use Grounds.ground_name to get Ground(ground_name)."""

    grounds = {name: Ground(GROUNDS_DATA[name]) for name in GROUNDS_DATA}

    def __getattr__(self, item) -> Ground:
        if item in self.grounds:
            return self.grounds[item]
        raise AttributeError(f'Ground "{item}" does not exist.')


class BuildingGroups:
    """Store data of groups of Buildings."""
    distances = {group: GROUPS_DATA[group]['max_dist'] for group in GROUPS_DATA}


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: Dict[str, List[List[List[str]]]], group: str):
        self.group = group
        ##################################################################################
        self.blocks = {}
        self.possible_variants = {}

        for variant in blocks:
            self.blocks[variant] = []
            self.possible_variants[variant] = []

            for x in range(len(blocks[variant])):
                self.blocks[variant] += [[]]
                self.possible_variants[variant] += [[]]

                for y in range(len(blocks[variant][x])):
                    self.blocks[variant][x] += [[]]
                    self.possible_variants[variant][x] += [[]]

                    for z in range(len(blocks[variant][x][y])):
                        self.blocks[variant][x][y] += [None]
                        self.possible_variants[variant][x][y] += [None]

                        data = blocks[variant][x][y][z]
                        if "!" in data:
                            data = data.split("!")
                            self.possible_variants[variant][x][y][z] = tuple(
                                set(Blocks.__getattr__(data[0]).variants).difference(
                                    set(data[1].split(";"))
                                )
                            )
                        elif ":" in data:
                            data = data.split(":")
                            self.possible_variants[variant][x][y][z] = tuple(
                                data[1].split(";")
                            )
                        else:
                            data = [data]
                            self.possible_variants[variant][x][y][z] = tuple(
                                Blocks.__getattr__(data[0]).variants
                            )

                        self.blocks[variant][x][y][z] = Blocks.__getattr__(data[0])

                    self.blocks[variant][x][y] = tuple(self.blocks[variant][x][y])
                    self.possible_variants[variant][x][y] = tuple(
                        self.possible_variants[variant][x][y]
                    )

                self.blocks[variant][x] = tuple(self.blocks[variant][x])
                self.possible_variants[variant][x] = tuple(
                    self.possible_variants[variant][x]
                )

            height = matrixHeight(self.blocks[variant])
            # convert blocks to rectangular matrix
            self.blocks[variant] = tuple(
                blocks_y + ((None,),) * (height - len(blocks_y))
                for blocks_y in self.blocks[variant]
            )
            self.possible_variants[variant] = tuple(
                blocks_y + ((None,),) * (height - len(blocks_y))
                for blocks_y in self.possible_variants[variant]
            )
        #######################################################################
        self.default_variant, self.default_blocks = self.generateVariant()

    def generateVariant(self) -> Tuple[Any, Tuple[Tuple[Tuple[Optional[Any]]]]]:
        btype_variant = choice(list(self.blocks))
        return (
            btype_variant,
            tuple(
                tuple(
                    tuple(
                        choice(self.possible_variants[btype_variant][x][y][z])
                        if self.blocks[btype_variant][x][y][z]
                        else None
                        for z in range(len(self.blocks[btype_variant][x][y]))
                    )
                    for y in range(matrixHeight(self.blocks[btype_variant]))
                )
                for x in range(len(self.blocks[btype_variant]))
            )
        )

    def drawDefault(self, size: QSize) -> QPixmap:
        blocks = self.blocks[self.default_variant]
        pix = QPixmap((4 + len(blocks) + len(blocks[0])) * ISOMETRIC_WIDTH,
                      (len(blocks) + len(blocks[0]) + 3) * ISOMETRIC_HEIGHT1 +
                      matrix3DHeight(blocks) * ISOMETRIC_HEIGHT2)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        fx = pix.width() * (2 + len(blocks[0])) / (4 + len(blocks) + len(blocks[0]))
        fy = matrix3DHeight(blocks) * ISOMETRIC_HEIGHT2 + ISOMETRIC_HEIGHT1
        for block_x in range(-1, len(blocks) + 1):
            for block_y in range(-1, len(blocks[0]) + 1):
                Grounds.grass.draw((block_x - block_y) * ISOMETRIC_WIDTH + fx,
                                   (block_x + block_y) * ISOMETRIC_HEIGHT1 + fy, painter)
                if 0 <= block_x < len(blocks) and 0 <= block_y < len(blocks[0]):
                    for z in range(len(blocks[block_x][block_y])):
                        if blocks[block_x][block_y][z] is not None:
                            blocks[block_x][block_y][z].draw(
                                (block_x - block_y) * ISOMETRIC_WIDTH + fx,
                                (block_x + block_y) * ISOMETRIC_HEIGHT1 - z * ISOMETRIC_HEIGHT2 + fy,
                                0, painter, self.default_blocks[block_x][block_y][z]
                            )
        painter.end()
        some_size = size * max(.1 + pix.height() / size.height(), pix.width() / size.width())
        pixmap = QPixmap(some_size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.drawPixmap((some_size.width() - pix.width()) / 2, (some_size.height() - pix.height()) / 2, pix)
        painter.end()
        return pixmap


class BuildingTypeManager:
    """Store all BuildingTypes.
       Use BuildingTypes.bt_name to get BuildingType called 'bt_name'.
       Use BuildingType.getByNumber(num) to get BuildingType with number 'num'."""

    building_types = {
        item: BuildingType(BUILDING_TYPES_DATA[item]["blocks"], BUILDING_TYPES_DATA[item].get('group', 'default'))
        for item in BUILDING_TYPES_DATA
    }

    sorted_names = sorted(building_types)

    def getByNumber(self, number: int) -> BuildingType:
        return self.__getattr__(self.sorted_names[number])

    def __getattr__(self, item: str):
        if item not in self.building_types:
            raise AttributeError(f'Building type "{item}" does not exists.')

        return self.building_types[item]


class RoadType:
    def __init__(self, name: str):
        self.name = name
        self.textures = {'center': getImage(f'{name}_center'),
                         'right-up': getImage(f'{name}_part').mirrored(False, True),
                         'right-down': getImage(f'{name}_part').mirrored(True, True),
                         'left-up': getImage(f'{name}_part'),
                         'left-down': getImage(f'{name}_part').mirrored(True, False)}

    def drawDefault(self, size: QSize) -> QPixmap:
        pix = QPixmap(size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.drawImage(size.width() / 2 - ISOMETRIC_WIDTH / 2,
                          size.height() / 2 - ISOMETRIC_HEIGHT1 / 2,
                          self.textures['center'])
        painter.end()
        return pix


class RoadTypesManager:
    """Store all road types"""

    road_types = {
        item: RoadType(ROAD_TYPES_DATA[item]) for item in ROAD_TYPES_DATA
    }

    sorted_names = sorted(road_types)

    def __getattr__(self, item: str):
        if item not in self.road_types:
            raise AttributeError(f'Road type "{item}" does not exists.')

        return self.road_types[item]

    def getByNumber(self, num: int) -> RoadType:
        return self.__getattr__(self.sorted_names[num])


class Mask:
    """Mask for ground."""

    def __init__(self, name: str):
        self.image = getImage(name)

    def draw(self, x: float, y: float, painter: QPainter) -> None:
        painter.drawImage(x - ISOMETRIC_WIDTH, y,  self.image)


class MasksManager:
    """Store all Masks."""

    masks = {item: Mask(item) for item in ("green", "yellow")}

    def __getattr__(self, item: str) -> Mask:
        return self.masks[item]


RoadTypes = RoadTypesManager()
Masks = MasksManager()
BuildingTypes = BuildingTypeManager()
Grounds = GroundsManager()
