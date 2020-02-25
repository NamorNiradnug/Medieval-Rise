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

        self.last_pos = None
        self.choosen_building = None
        self.mode = 'town'

    def setSize(self, size: QSize) -> None:
        self.resize(size.width(), size.height())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.check_thead.cancel()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self.last_pos = event.pos()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.town.scaleByEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.last_pos:
            delta = event.pos() - self.last_pos
            self.town.translate(delta)
            self.choosen_building.move(-delta)
            self.last_pos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self.last_pos = None

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        event_key = event.key()

        # enter...
        if event_key == 16777220:
            if self.mode == 'town_builder':
                self.choosen_building.build()
                self.choosen_building = None
                self.mode = 'town'

        if event_key == Qt.Key_B:
            self.mode = 'town_builder'
            self.choosen_building = Town.ProjectedBuilding(
                self.town, Town.building_type2)

        if event_key == Qt.Key_Right:
            if self.mode == 'town_builder':
                self.choosen_building.angle = (
                    self.choosen_building.angle + 90) % 360

        if event_key == Qt.Key_Left:
            if self.mode == 'town_builder':
                self.choosen_building.angle = (
                    self.choosen_building.angle - 90) % 360

        if event_key == Qt.Key_Escape:
            if self.mode == 'town_builder':
                self.choosen_building.destroy()
                self.choosen_building = None
                self.mode = 'town'

            if self.mode == 'town':
                # open pause menu
                pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())

        if self.mode == 'town_builder':
            self.choosen_building.draw(painter, self.size())

        painter.end()

    def mousePositionEvent(self) -> None:
        cursor_pos = self.cursor().pos()

        if not self.last_pos and not isPointInRect(cursor_pos, (QPoint(20, 20), self.size() - QSize(40, 40))):
            delta = QPoint((cursor_pos.x() - self.size().width() // 2) / 40,
                           (cursor_pos.y() - self.size().height() // 2) / 34)
            self.town.cam_x += delta.x()
            self.town.cam_y += delta.y()

            if self.mode == 'town_builder':
                self.choosen_building.move(delta)


if __name__ == '__main__':
    app = QApplication([])
    town = Town.Town()
    Town.Building(1, 5, 0, town, Town.building_type2)
    frame = Frame(town)
    frame.setWindowTitle('Town')
    frame.setWindowIcon(QIcon(QPixmap(getImage('block90'))))
    frame.showFullScreen()
    app.exec_()
