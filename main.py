#!/usr/bin/env python3
from enum import Enum
from threading import Event, Thread
from types import FunctionType

from PyQt5.QtCore import QPoint, QSize, Qt, QRect
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPixmap, QWheelEvent, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow

import Town


class Interval(Thread):
    """Periodical thread."""

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
    TownRoadBuilder = 2
    Destroy = 3


def transparentCursor() -> QCursor:
    """Transparent 32x32 cursor."""

    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    return QCursor(pix)


class Frame(QMainWindow):
    """Window showing town."""

    def __init__(self, town: Town.Town):
        super().__init__()
        self.setMouseTracking(True)

        self.town = town

        self.last_pos = self.cursor().pos()
        self.last_button = Qt.NoButton
        self.mode = Modes.Town
        self.scrollAmount = 0
        self.menu_mode = 1
        self.menuAnimation = 0
        self.destroy_pos = None

        self.draw_thread = Interval(1 / 160, self.update)
        self.check_thread = Interval(1 / 40, self.mousePositionEvent)
        self.town_tic_thread = Interval(1 / 20, lambda: town.tick(self.size()))
        self.town_tic_thread.start()
        self.draw_thread.start()
        self.check_thread.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.check_thread.cancel()
        self.town_tic_thread.cancel()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.last_button = event.button()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.town.scaleByEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        delta = event.pos() - self.last_pos

        if self.last_button == Qt.LeftButton and self.mode == Modes.TownRoadBuilder:
            self.town.projecting_road.build()
        elif self.last_button == Qt.RightButton:
            self.town.translate(delta)

        self.last_pos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self.mode == Modes.Town:
                if Town.isPointInRect(event.pos(), (
                        QPoint(0, self.height() * .8 + self.menuAnimation),
                        QSize(self.height() / 15, self.height() / 15)
                )):
                    self.menu_mode = 1
                elif Town.isPointInRect(event.pos(), (
                        QPoint(0, self.height() * 13 / 15 + self.menuAnimation),
                        QSize(self.height() / 15, self.height() / 15)
                )):
                    self.menu_mode = 2
                elif Town.isPointInRect(event.pos(), (
                        QPoint(0, self.height() * 14 / 15 + self.menuAnimation),
                        QSize(self.height() / 15, self.height() / 15)
                )):
                    self.mode = Modes.Destroy
                    self.setCursor(transparentCursor())
                else:
                    if self.menu_mode == 1:
                        types = Town.BuildingTypes
                    elif self.menu_mode == 2:
                        types = Town.RoadTypes
                    for i in range(len(types.sorted_names)):
                        if Town.isPointInRect(event.pos(), (QPoint(
                                self.height() * (3 * i + 1) / 15 - self.scrollAmount,
                                self.height() * .8 + self.menuAnimation
                        ), QSize(self.height() * .2, self.height() * .2))):
                            self.mode = Modes(self.menu_mode)
                            self.town.chosen_btype = i
                            self.town.chosen_building = Town.ProjectedBuilding(
                                self.town,
                                Town.BuildingTypes.getByNumber(self.town.chosen_btype)
                            )
                            self.setCursor(transparentCursor())
                            break
            elif self.mode == Modes.TownBuilder:
                if self.town.chosen_building.build():
                    self.mode = Modes.Town
                    self.setCursor(QCursor())
            elif self.mode == Modes.TownRoadBuilder:
                self.town.projecting_road.build()
            elif self.mode == Modes.Destroy:
                build = self.town.getBuilding(int(self.destroy_pos.x()), int(self.destroy_pos.y()))
                if build:
                    build.destroy()
                    self.mode = Modes.Town
                    self.setCursor(QCursor())

        self.last_button = Qt.NoButton

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        event_key = event.key()

        if event_key == Qt.Key_R:
            if self.mode == Modes.Town:
                self.mode = Modes.TownRoadBuilder
                self.town.projecting_road = Town.ProjectingRoad(self.town)
                self.setCursor(transparentCursor())

        if event_key == Qt.Key_Right:
            if self.mode == Modes.TownBuilder:
                self.town.chosen_building.turn(90)

        if event_key == Qt.Key_Left:
            if self.mode == Modes.TownBuilder:
                self.town.chosen_building.turn(-90)

        if event_key == Qt.Key_Escape:
            if self.mode == Modes.Town:
                pass  # open pause menu
            elif self.mode == Modes.TownBuilder:
                self.town.chosen_building.destroy()
                self.town.chosen_building = None
            elif self.mode == Modes.TownRoadBuilder:
                self.town.projecting_road.destroy()
                self.town.projecting_road = None

            self.mode = Modes.Town
            self.setCursor(QCursor())

    def drawButton(self, painter, rect, tex):
        if Town.isPointInRect(self.cursor().pos() - self.pos(), (rect.topLeft(), rect.size())):
            if self.last_button == Qt.LeftButton:
                painter.fillRect(rect, Qt.red)
                painter.drawRect(rect)
                # painter.drawImage(rect, pressed tex)
            else:
                painter.fillRect(rect, Qt.green)
                painter.drawRect(rect)
                # painter.drawImage(rect, hover tex)
        else:
            painter.fillRect(rect, Qt.blue)
            painter.drawRect(rect)
            # painter.drawImage(rect, tex)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        cursor_pos = (self.cursor().pos() - QPoint(self.width(), self.height()) / 2) \
                     * self.town.cam_z + QPoint(self.town.cam_x, self.town.cam_y)

        if self.mode == Modes.TownBuilder:
            self.town.chosen_building.addToMap(Town.isometric(cursor_pos.x(), cursor_pos.y()))
        elif self.mode == Modes.TownRoadBuilder:
            self.town.projecting_road.addToMap(Town.isometric(cursor_pos.x(), cursor_pos.y()))

        self.town.draw(painter, self.size())

        if self.mode == Modes.Destroy:
            self.destroy_pos = (Town.isometric(cursor_pos.x(), cursor_pos.y()))
            painter.fillRect(QRect(self.cursor().pos() - self.pos() - QPoint(60, 60) / 2, QSize(60, 60)), Qt.red)
            # painter.drawImage(QRect(self.cursor().pos() - self.pos() - icon.bottomRight() / 2, icon.size()), icon)

        if self.mode == Modes.Town and self.menuAnimation > 0:
            self.menuAnimation -= 8
        elif self.mode != Modes.Town and self.menuAnimation < self.height() * .2:
            self.menuAnimation += 8
        painter.fillRect(QRect(0, self.height() * .8 + self.menuAnimation, self.width(), self.height() * .2), Qt.gray)
        if self.menu_mode == 1:
            types = Town.BuildingTypes
        elif self.menu_mode == 2:
            types = Town.RoadTypes
        for i in range(len(types.sorted_names)):
            self.drawButton(painter, QRect(
                self.height() * (3 * i + 1) / 15 - self.scrollAmount,
                self.height() * .8 + self.menuAnimation,
                self.height() * .2,
                self.height() * .2
            ), None)  # button)
            types.getByNumber(i).drawDefault(
                self.height() * (6 * i + 5) / 30 - self.scrollAmount,
                self.height() * .9 + self.menuAnimation,
                painter
            )
        self.drawButton(
            painter,
            QRect(0, self.height() * .8 + self.menuAnimation, self.height() / 15, self.height() / 15),
            None  # build button
        )
        self.drawButton(
            painter,
            QRect(0, self.height() * 13 / 15 + self.menuAnimation, self.height() / 15, self.height() / 15),
            None  # road button
        )
        self.drawButton(
            painter,
            QRect(0, self.height() * 14 / 15 + self.menuAnimation, self.height() / 15, self.height() / 15),
            None  # destroy button
        )

        painter.end()

    def mousePositionEvent(self) -> None:
        """Do something dependent on cursor position."""

        cursor_pos = self.cursor().pos()

        if self.last_button == Qt.NoButton and not Town.isPointInRect(
                cursor_pos,
                (QPoint(10, 10), self.maximumSize() - QSize(20, 20))
        ):
            delta = QPoint(
                (cursor_pos.x() - self.maximumWidth() // 2) / 40,
                (cursor_pos.y() - self.maximumHeight() // 2) / 34
            )
            self.town.translate(-delta)


if __name__ == "__main__":
    app = QApplication([])
    town = Town.Town()
    frame = Frame(town)
    frame.setMaximumSize(app.screens()[0].size())
    frame.setWindowTitle("Medieval Rise")
    frame.showMaximized()
    app.exec_()
