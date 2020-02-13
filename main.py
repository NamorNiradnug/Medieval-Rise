from types import FunctionType
from threading import Thread, Event

from PyQt5.QtCore import QRect, QSize, QPoint, QRectF, Qt
from PyQt5.QtGui import (QPainter, QIcon, QImage, QPixmap,
                         QMouseEvent, QCloseEvent, QPaintEvent, QWheelEvent)
from PyQt5.QtWidgets import QApplication, QMainWindow

import Town
from resources_manager import getImage


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

        self.draw_thread = Interval(1 / 60, self.update)
        self.draw_thread.start()

        self.town = town

        self.last_pos = None

    def setSize(self, size: QSize) -> None:
        QMainWindow.setGeometry(self, QRect(QApplication.desktop().screenGeometry().center()
                                            - QPoint(size.width(), size.height()) / 2, size))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()

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

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.town.draw(painter, self.size())
        painter.end()


if __name__ == '__main__':
    app = QApplication([])
    town = Town.Town()
    frame = Frame(town)
    frame.show()
    frame.setWindowTitle('Town')
    frame.setWindowIcon(QIcon(QPixmap(getImage('block90'))))
    for i in range(5):
        for j in range(5):
            Town.Building(3 * i, 3 * j, (i * 90) %
                          360, town, Town.building_type2)
    frame.show()
    app.exec_()
