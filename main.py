#!/usr/bin/env python3
from enum import Enum
from threading import Event, Thread
from types import FunctionType

from PyQt5.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PyQt5.QtGui import (QCloseEvent, QIcon, QImage, QKeyEvent, QMouseEvent,
                         QPainter, QPaintEvent, QPixmap, QWheelEvent)
from PyQt5.QtWidgets import QApplication, QMainWindow

import Town

from resources_manager import getImage


def isPointInRect(point: QPoint, rect: (QPoint, QSize)) -> bool:
    return rect[0].x() <= point.x() <= rect[0].x() + rect[1].width() and \
        rect[0].y() <= point.y() <= rect[0].y() + rect[1].height()


class Interval(Thread):
    def __init__(self, interval: float, func: FunctionType):
        Thread.__init__(self)
        self.stopped = Event()
        self.interval = interval
        self.func = func

    def run(self):
        while not self.stopped.wait(self.interval):
            self.func()

    def cancel(self):
        self.stopped.set()


class Modes(Enum):
    """Modes for Frame."""
    Town = 0
    TownBuilder = 1


class Frame(QMainWindow):
    def __init__(self, town: Town.Town, size: QSize = QSize(640, 480)):
        super().__init__()
        self.setSize(size)
        self.setMouseTracking(True)

        self.draw_thread = Interval(1 / 60, self.update)
        self.check_thead = Interval(1 / 40, self.mousePositionEvent)
        self.draw_thread.start()
        self.check_thead.start()

        self.town = town

        self.last_pos = self.cursor().pos()
        self.last_button = Qt.NoButton
        self.choosen_building = None
        self.choosen_btype = 0
        self.mode = Modes.Town

    def buildProjectedBuilding(self):
        if self.town.isBlocksEmpty(
                round(self.choosen_building.isometric.x()),
                round(self.choosen_building.isometric.y()),
                self.choosen_building.blocks):
            self.choosen_building.build()
            self.choosen_building = None
            self.mode = Modes.Town

    def setSize(self, size: QSize) -> None:
        self.resize(size.width(), size.height())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.check_thead.cancel()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.last_button = event.button()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.town.scaleByEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = event.pos() - self.last_pos

        if self.last_button == Qt.RightButton:
            self.town.translate(delta)

        self.last_pos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self.mode == Modes.TownBuilder:
                self.buildProjectedBuilding()

        self.last_button = Qt.NoButton

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        event_key = event.key()

        # Enter...
        if event_key == Qt.Key_Enter - 1:
            if self.mode == Modes.TownBuilder:
                self.buildProjectedBuilding()

        if event_key == Qt.Key_B:
            self.mode = Modes.TownBuilder
            self.choosen_building = Town.ProjectedBuilding(
                self.town, Town.BuildingTypes.getByNumber(0))
            self.cursor().setPos(self.width() / 2, self.height() / 2)

        if event_key == Qt.Key_Up:
            if self.mode == Modes.TownBuilder:
                self.choosen_btype = (
                    self.choosen_btype + 1) % len(Town.BuildingTypes.sorted_names)
                self.choosen_building.setBuildingType(Town.BuildingTypes.getByNumber(
                    self.choosen_btype))

        if event_key == Qt.Key_Down:
            if self.mode == Modes.TownBuilder:
                self.choosen_btype = (
                    self.choosen_btype - 1) % len(Town.BuildingTypes.sorted_names)
                self.choosen_building.setBuildingType(Town.BuildingTypes.getByNumber(
                    self.choosen_btype))

        if event_key == Qt.Key_Right:
            if self.mode == Modes.TownBuilder:
                self.choosen_building.turn(90)

        if event_key == Qt.Key_Left:
            if self.mode == Modes.TownBuilder:
                self.choosen_building.turn(-90)

        if event_key == Qt.Key_Escape:
            if self.mode == Modes.TownBuilder:
                self.choosen_building.destroy()
                self.choosen_building = None
                self.mode = Modes.Town

            if self.mode == Modes.Town:
                # open pause menu
                pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())

        if self.mode == Modes.TownBuilder:
            cursor_pos = (self.cursor().pos() - QPoint(self.width(), self.height()) /
                          2) * self.town.cam_z + QPoint(self.town.cam_x, self.town.cam_y)
            self.choosen_building.isometric = Town.isometric(
                cursor_pos.x(), cursor_pos.y())
            self.choosen_building.draw(painter, self.size())

        painter.end()

    def mousePositionEvent(self) -> None:
        cursor_pos = self.cursor().pos()

        if self.last_button == Qt.NoButton and \
                not isPointInRect(cursor_pos, (QPoint(20, 20), self.size() - QSize(40, 40))):
            delta = QPoint((cursor_pos.x() - self.size().width() // 2) / 40,
                           (cursor_pos.y() - self.size().height() // 2) / 34)
            self.town.translate(-delta)


if __name__ == '__main__':
    app = QApplication([])
    town = Town.Town()
    Town.Building(1, 5, 0, town, Town.BuildingTypes.building_type2)
    frame = Frame(town)
    frame.setWindowTitle('Medieval Rise')
    frame.showFullScreen()
    app.exec_()
