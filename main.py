#!/usr/bin/env python3
from enum import Enum
from threading import Event, Thread
from types import FunctionType

from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPixmap, QWheelEvent, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow

import Town


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


def transparentCursor() -> QCursor:
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    return QCursor(pix)


class Frame(QMainWindow):
    def __init__(self, town: Town.Town):
        super().__init__()
        self.setMouseTracking(True)

        self.town = town

        self.last_pos = self.cursor().pos()
        self.last_button = Qt.NoButton
        self.chosen_building = None
        self.chosen_btype = 0
        self.mode = Modes.Town

        self.draw_thread = Interval(1 / 60, self.update)
        self.check_thread = Interval(1 / 40, self.mousePositionEvent)
        self.draw_thread.start()
        self.check_thread.start()

    def buildProjectedBuilding(self):
        self.chosen_building.build()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.check_thread.cancel()

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

        if event_key == Qt.Key_B:
            self.mode = Modes.TownBuilder
            self.chosen_building = Town.ProjectedBuilding(
                self.town, Town.BuildingTypes.getByNumber(self.chosen_btype)
            )
            self.cursor().setPos(self.width() / 2, self.height() / 2)
            self.setCursor(transparentCursor())

        if event_key == Qt.Key_Up:
            if self.mode == Modes.TownBuilder:
                self.chosen_btype = (self.chosen_btype + 1) % len(Town.BuildingTypes.sorted_names)
                self.chosen_building.setBuildingType(Town.BuildingTypes.getByNumber(self.chosen_btype))

        if event_key == Qt.Key_Down:
            if self.mode == Modes.TownBuilder:
                self.chosen_btype = (self.chosen_btype - 1) % len(Town.BuildingTypes.sorted_names)
                self.chosen_building.setBuildingType(Town.BuildingTypes.getByNumber(self.chosen_btype))

        if event_key == Qt.Key_Right:
            if self.mode == Modes.TownBuilder:
                self.chosen_building.turn(90)

        if event_key == Qt.Key_Left:
            if self.mode == Modes.TownBuilder:
                self.chosen_building.turn(-90)

        if event_key == Qt.Key_Escape:
            if self.mode == Modes.TownBuilder:
                self.chosen_building.destroy()
                self.chosen_building = None
                self.mode = Modes.Town
                self.setCursor(QCursor())

            if self.mode == Modes.Town:
                # open pause menu
                pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())

        if self.mode == Modes.TownBuilder:
            cursor_pos = (
                self.cursor().pos() - QPoint(self.width(), self.height()) / 2) * self.town.cam_z +\
                QPoint(self.town.cam_x, self.town.cam_y)
            self.chosen_building.isometric = Town.isometric(cursor_pos.x(), cursor_pos.y())
            self.chosen_building.draw(painter, self.size())
            Town.BuildingTypes.getByNumber(self.chosen_btype).drawDefault(self.width() - 125, 250, painter)

        painter.end()

    def mousePositionEvent(self) -> None:
        cursor_pos = self.cursor().pos()

        if self.last_button == Qt.NoButton \
           and not Town.isPointInRect(cursor_pos, (QPoint(10, 10), self.size() - QSize(20, 20))):
            delta = QPoint((cursor_pos.x() - self.size().width() // 2) / 40,
                           (cursor_pos.y() - self.size().height() // 2) / 34)
            self.town.translate(-delta)


if __name__ == "__main__":
    app = QApplication([])
    town = Town.Town()
    frame = Frame(town)
    frame.setWindowTitle("Medieval Rise")
    frame.showFullScreen()
    app.exec_()
