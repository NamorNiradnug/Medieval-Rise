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
        self.choosen_building_angle = None
        self.mode = 'town'

    def setSize(self, size: QSize) -> None:
        self.resize(size.width(), size.height())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()
        self.check_thead.cancel()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.last_pos = event.pos()

    def wheelEvent(self, event: QWheelEvent):
        self.town.scaleByEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.last_pos:
            delta = event.pos() - self.last_pos
            self.town.translate(delta)
            self.last_pos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.last_pos = None

    def keyReleaseEvent(self, event: QKeyEvent):
        event_key = event.key()

        if event_key == Qt.Key_B:
            self.mode = 'town_builder'
            self.choosen_building = Town.ProjectedBuilding(Town.building_type2)
            self.choosen_building_angle = 0

        if event_key == Qt.Key_Right:
            if self.mode == 'town_builder':
                self.choosen_building_angle = (
                    self.choosen_building_angle + 90) % 360

        if event_key == Qt.Key_Left:
            if self.mode == 'town_builder':
                self.choosen_building_angle = (
                    self.choosen_building_angle - 90) % 360

        if event_key == Qt.Key_D:
            if self.mode == 'town_builder':
                self.choosen_building.destroy()
                self.choosen_building = None
                self.mode = 'town'

        if event_key == Qt.Key_Escape:
            if self.isFullScreen():
                self.showMaximized()
            else:
                self.showFullScreen()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())

        if self.mode == 'town_builder' and self.choosen_building:
            # TODO not take global cursor position
            cursor_pos = self.cursor().pos()
            self.choosen_building.draw(cursor_pos.x(), cursor_pos.y(), self.choosen_building_angle,
                                       painter)

        painter.end()

    def mousePositionEvent(self) -> None:
        cursor_pos = self.cursor().pos()

        if self.last_pos is None and (self.isMaximized() or self.isFullScreen()) and \
                not isPointInRect(cursor_pos, (QPoint(20, 20), self.size() - QSize(40, 40))):
            self.town.cam_x += (cursor_pos.x() - self.size().width() // 2) / 40
            self.town.cam_y += (cursor_pos.y() -
                                self.size().height() // 2) / 34


if __name__ == '__main__':
    app = QApplication([])
    town = Town.Town()
    Town.Building(1, 1, 0, town, Town.building_type2)
    frame = Frame(town)
    frame.setWindowTitle('Town')
    frame.setWindowIcon(QIcon(QPixmap(getImage('block90'))))
    frame.show()
    app.exec_()
