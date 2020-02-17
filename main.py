from types import FunctionType
from threading import Thread, Event

from PyQt5.QtCore import QRect, QSize, QPoint, QRectF, Qt
from PyQt5.QtGui import (QPainter, QIcon, QImage, QPixmap,
                         QMouseEvent, QCloseEvent, QPaintEvent,
                         QWheelEvent, QKeyEvent)
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
        self.check_thead = Interval(1 / 40, self.checkForMoving)
        self.draw_thread.start()
        self.check_thead.start()

        self.town = town

        self.last_pos = None
        self.builded_number = 0

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

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_B and self.builded_number <= 81:
            Town.Building(4 * self.builded_number, 1, (self.builded_number * 90) % 360,
                          self.town, Town.building_type2)
            self.builded_number += 1
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showMaximized()
            else:
                self.showFullScreen()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())
        painter.end()

    def checkForMoving(self) -> None:
        cursor_pos = self.cursor().pos()
        if self.last_pos is None and (self.isMaximized() or self.isFullScreen()) and \
                not isPointInRect(cursor_pos, (QPoint(20, 20), self.size() - QSize(40, 40))):
            self.town.cam_x += (cursor_pos.x() - self.size().width() // 2) / 40
            self.town.cam_y += (cursor_pos.y() -
                                self.size().height() // 2) / 34


if __name__ == '__main__':
    app = QApplication([])
    town = Town.Town()
    frame = Frame(town)
    frame.setWindowTitle('Town')
    frame.setWindowIcon(QIcon(QPixmap(getImage('block90'))))
    frame.showFullScreen()
    app.exec_()
