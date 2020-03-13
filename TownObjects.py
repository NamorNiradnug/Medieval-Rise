from json import load
from random import choice
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtGui import QPainter

from resources_manager import getImage

ISOMETRIC_WIDTH = 64    # |
ISOMETRIC_HEIGHT1 = 64  # | textures parameters
ISOMETRIC_HEIGHT2 = 79  # |

BLOCKS_DATA = load(open("blocks.json"))


def matrixHeight(matrix: Tuple[Tuple[Any]]) -> int:
    return max([len(blocks_y) for blocks_y in matrix])


class Block:
    """Store data of block."""

    def __init__(self, name: str):
        self.name = name

        sides = ("NORTH", "WEST", "SOUTH", "EAST")
        self.variants = {
            i: {
                j * 90: (
                    getImage(f"{BLOCKS_DATA[name][i][sides[(4 - j) % 4]]}_left"),
                    getImage(f"{BLOCKS_DATA[name][i][sides[(5 - j) % 4]]}_right"),
                )
                for j in range(4)
            }
            for i in BLOCKS_DATA[name]
        }

    def __repr__(self):
        return f"Block {self.name}"

    def __str__(self):
        return f"Block {self.name}"

    def draw(self, x: float, y: float, angle: int, painter: QPainter, variant: str) -> None:
        if variant not in self.variants:
            raise AttributeError(f"Block called {self.name} has not variant {variant}.")

        painter.drawImage(x - ISOMETRIC_WIDTH, y - ISOMETRIC_HEIGHT2, self.variants[variant][angle][0])
        painter.drawImage(x, y - ISOMETRIC_HEIGHT2, self.variants[variant][angle][1])


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

    grounds = {name: Ground(name) for name in ("grass",)}

    def __getattr__(self, item):
        if item in self.grounds:
            return self.grounds[item]
        raise AttributeError(f'Ground "{item}" does not exist.')


Grounds = GroundsManager()


class BuildingGroups:
    """Store data of groups of Buildings."""
    default = 0
    forts = 1
    distances = {0: 5, 1: 2}


class BuildingType:
    """Store information about some building type."""

    def __init__(self, blocks: Dict[str, List[List[List[str]]]], group: str):
        self.group = eval(f'BuildingGroups.{group}')
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

    def drawDefault(self, fx: int, fy: int, painter: QPainter) -> None:
        blocks = self.blocks[self.default_variant]
        for block_x in range(len(blocks)):
            for block_y in range(len(blocks[block_x])):
                for z in range(len(blocks[block_x][block_y])):
                    if blocks[block_x][block_y][z] is not None:
                        blocks[block_x][block_y][z].draw(
                            (block_x - block_y) * ISOMETRIC_WIDTH + fx,
                            (block_x + block_y) * (ISOMETRIC_HEIGHT1 / 2) - z * ISOMETRIC_HEIGHT2 + fy,
                            0, painter, self.default_blocks[block_x][block_y][z]
                        )


BUILDING_TYPES_DATA = load(open("building_types.json"))


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


BuildingTypes = BuildingTypeManager()
