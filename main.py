#!/usr/bin/env python3
from enum import Enum
from threading import Event, Thread
from types import FunctionType

from PyQt5.QtCore import QPoint, QSize, Qt, QRect
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPixmap, QWheelEvent, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow

import Town
from resources_manager import getImage


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

        self.default_cursor = QCursor(QPixmap("assets/cursor.png"))
        self.setCursor(self.default_cursor)

        self.last_pos = self.cursor().pos()
        self.last_button = Qt.NoButton
        self.mode = Modes.Town
        self.scrollAmount = 0
        self.menu_mode = 1
        self.menuAnimation = 0
        self.destroy_pos = None

        self.draw_thread = Interval(1 / 160, self.update)
        self.town_tick_thread = Interval(1 / 20, lambda: town.tick(self.size()))
        self.town_tick_thread.start()
        self.draw_thread.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.town_tick_thread.cancel()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.last_button = event.button()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if Town.isPointInRect(event.pos(), (QPoint(0, self.height() * .8), QSize(self.width(), self.height() * .2))):
            if self.menu_mode == 1:
                types = Town.BuildingTypes
            elif self.menu_mode == 2:
                types = Town.RoadTypes
            delta = event.pixelDelta()
            if delta is None:
                delta = -event.angleDelta().y() / 2
            else:
                delta = -delta.x() / 2
            max_scroll = (3 * len(types.sorted_names) + 1) / 15 * self.height() - self.width()
            if Town.isPointInRect(event.pos(), (QPoint(self.height() / 15, self.height() * .8), QSize(
                    self.width(),
                    self.height() * .2
            ))) and (delta > 0 and max_scroll > self.scrollAmount or delta < 0 and self.scrollAmount > 0):
                self.scrollAmount += delta
                if max_scroll < self.scrollAmount:
                    self.scrollAmount = max_scroll
                elif self.scrollAmount < 0:
                    self.scrollAmount = 0

        else:
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
                    self.scrollAmount = 0
                elif Town.isPointInRect(event.pos(), (
                        QPoint(0, self.height() * 13 / 15 + self.menuAnimation),
                        QSize(self.height() / 15, self.height() / 15)
                )):
                    self.menu_mode = 2
                    self.scrollAmount = 0
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
                            if self.menu_mode == 1:
                                self.town.chosen_btype = i
                                self.town.chosen_building = Town.ProjectedBuilding(
                                    self.town,
                                    Town.BuildingTypes.getByNumber(self.town.chosen_btype)
                                )
                            else:
                                self.town.projecting_road = Town.ProjectingRoad(self.town)
                            self.setCursor(transparentCursor())
                            break
            elif self.mode == Modes.TownBuilder:
                if self.town.chosen_building.build():
                    self.mode = Modes.Town
                    self.setCursor(self.default_cursor)
            elif self.mode == Modes.TownRoadBuilder:
                self.town.projecting_road.build()
            elif self.mode == Modes.Destroy:
                build = self.town.getBuilding(int(self.destroy_pos.x()), int(self.destroy_pos.y()))
                if build:
                    build.destroy()
                    self.mode = Modes.Town
                    self.setCursor(self.default_cursor)

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
            self.setCursor(self.default_cursor)

    def drawButton(self, painter, cursor, rect, tex):
        fix = ""
        add = 4
        if Town.isPointInRect(cursor, (rect.topLeft(), rect.size())) and self.last_button == Qt.LeftButton:
            fix = "pressed_"
            add = 0
            rect.adjust(0, 4, 0, 0)
        painter.drawTiledPixmap(rect.adjusted(10, 10, -10, -10), QPixmap.fromImage(getImage(f"button/body")))

        painter.drawTiledPixmap(
            QRect(rect.x() + 10, rect.y(), rect.width() - 20, 15), QPixmap.fromImage(getImage(f"button/top"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x() + 10, rect.y() + rect.height() - add - 15, rect.width() - 20, add + 15),
            QPixmap.fromImage(getImage(f"button/{fix}bottom"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x(), rect.y() + 10, 15, rect.height() - add - 20),
            QPixmap.fromImage(getImage(f"button/left"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x() + rect.width() - 15, rect.y() + 10, 15, rect.height() - add - 20),
            QPixmap.fromImage(getImage(f"button/right"))
        )

        painter.drawTiledPixmap(
            QRect(rect.x(), rect.y(), 15, 15),
            QPixmap.fromImage(getImage(f"button/top_left"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x() + rect.width() - 15, rect.y(), 15, 15),
            QPixmap.fromImage(getImage(f"button/top_right"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x(), rect.y() + rect.height() - add - 15, 15, add + 15),
            QPixmap.fromImage(getImage(f"button/{fix}bottom_left"))
        )
        painter.drawTiledPixmap(
            QRect(rect.x() + rect.width() - 15, rect.y() + rect.height() - add - 15, 15, add + 15),
            QPixmap.fromImage(getImage(f"button/{fix}bottom_right"))
        )

        painter.drawPixmap(rect.adjusted(3, 3, -3, -add - 3), tex)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        cursor_pos = (self.cursor().pos() - self.frameGeometry().bottomRight() + QPoint(
            self.width(),
            self.height()
        ) / 2) * self.town.cam_z + QPoint(self.town.cam_x, self.town.cam_y)

        if self.mode == Modes.TownBuilder:
            self.town.chosen_building.addToMap(Town.isometric(cursor_pos.x(), cursor_pos.y()))
        elif self.mode == Modes.TownRoadBuilder:
            self.town.projecting_road.addToMap(Town.isometric(cursor_pos.x(), cursor_pos.y()))

        self.town.draw(painter, self.size())

        cursor = QPoint(
            self.cursor().pos().x() - self.pos().x(),
            self.cursor().pos().y() + self.height() - self.frameSize().height() - self.pos().y()
        )
        if self.mode == Modes.Destroy:
            self.destroy_pos = (Town.isometric(cursor_pos.x(), cursor_pos.y()))
            painter.drawImage(QRect(cursor - QPoint(48, 48), QSize(96, 96)), getImage("destroy"))

        if self.mode == Modes.Town and self.menuAnimation > 0:
            self.menuAnimation -= 8
        elif self.mode != Modes.Town and self.menuAnimation < self.height() * .2:
            self.menuAnimation += 8
        painter.drawTiledPixmap(
            QRect(20, self.height() * .8 + self.menuAnimation + 20, self.width() - 40, self.height() * .2 - 40),
            QPixmap.fromImage(getImage("panel/body"))
        )

        painter.drawTiledPixmap(
            QRect(20, self.height() * .8 + self.menuAnimation, self.width() - 40, 25),
            QPixmap.fromImage(getImage("panel/top"))
        )
        painter.drawTiledPixmap(
            QRect(20, self.height() + self.menuAnimation - 25, self.width() - 40, 25),
            QPixmap.fromImage(getImage("panel/bottom"))
        )
        painter.drawTiledPixmap(
            QRect(0, self.height() * .8 + self.menuAnimation + 20, 25, self.height() * .2 - 40),
            QPixmap.fromImage(getImage("panel/left"))
        )
        painter.drawTiledPixmap(
            QRect(self.width() - 25, self.height() * .8 + self.menuAnimation + 20, 25, self.height() * .2 - 40),
            QPixmap.fromImage(getImage("panel/right"))
        )

        painter.drawImage(QRect(0, self.height() * .8 + self.menuAnimation, 25, 25), getImage("panel/top_left"))
        painter.drawImage(
            QRect(self.width() - 25, self.height() * .8 + self.menuAnimation, 25, 25), getImage("panel/top_right")
        )
        painter.drawImage(QRect(0, self.height() + self.menuAnimation - 25, 25, 25), getImage("panel/bottom_left"))
        painter.drawImage(
            QRect(self.width() - 25, self.height() + self.menuAnimation - 25, 25, 25), getImage("panel/bottom_right")
        )
        if self.menu_mode == 1:
            types = Town.BuildingTypes
        elif self.menu_mode == 2:
            types = Town.RoadTypes
        for i in range(len(types.sorted_names)):
            pix = QPixmap(self.height() * .2, self.height() * .2)
            pix.fill(Qt.transparent)
            pain = QPainter(pix)
            pain.save()
            pain.translate(self.height() * .05, self.height() * .05)
            pain.scale(.5, .5)
            types.getByNumber(i).drawDefault(
                self.height() * .1,
                self.height() * .1,
                pain
            )
            pain.restore()
            pain.end()
            self.drawButton(painter, cursor, QRect(
                self.height() * (3 * i + 1) / 15 - self.scrollAmount,
                self.height() * .8 + self.menuAnimation,
                self.height() * .2,
                self.height() * .2
            ), pix)
        self.drawButton(
            painter,
            cursor,
            QRect(0, self.height() * .8 + self.menuAnimation, self.height() / 15, self.height() / 15),
            QPixmap.fromImage(getImage("build"))
        )
        self.drawButton(
            painter,
            cursor,
            QRect(0, self.height() * 13 / 15 + self.menuAnimation, self.height() / 15, self.height() / 15),
            QPixmap.fromImage(getImage("road"))
        )
        self.drawButton(
            painter,
            cursor,
            QRect(0, self.height() * 14 / 15 + self.menuAnimation, self.height() / 15, self.height() / 15),
            QPixmap.fromImage(getImage("destroy"))
        )

        painter.end()


if __name__ == "__main__":
    app = QApplication([])
    town = Town.Town()
    frame = Frame(town)
    frame.setMaximumSize(app.screens()[0].size())
    frame.setWindowTitle("Medieval Rise")
    frame.showMaximized()
    app.exec_()
