from types import FunctionType
from threading import Thread, Event

from PyQt5.QtCore import QRect, QSize, QPoint, QRectF, Qt
from PyQt5.QtGui import (QPainter, QIcon, QImage, QPixmap,
                         QMouseEvent, QCloseEvent, QPaintEvent)
from PyQt5.QtWidgets import QApplication, QMainWindow

import town
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
    def __init__(self, med_town: town.Town, size: QSize = QSize(640, 480)):
        super().__init__()
        self.setSize(size)

        self.draw_thread = Interval(1 / 60, self.update)
        self.draw_thread.start()

        self.town = med_town

        self.press_pos = None

    def setSize(self, size: QSize) -> None:
        QMainWindow.setGeometry(self, QRect(QApplication.desktop().screenGeometry().center()
                                            - QPoint(size.width(), size.height()) / 2, size))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.draw_thread.cancel()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.press_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        print('moving')
        if self.press_pos:
            delta = event.pos() - self.press_pos
            print(delta.x(), delta.y())
            self.town.cam_x += delta.x()
            self.town.cam_y += delta.y()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.press_pos = None

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        geom = self.geometry()

        grass = QPixmap(getImage("grass"))
        painter.drawTiledPixmap(
            QRectF(0, 0, geom.width(), geom.height()), grass)
        painter.drawTiledPixmap(QRectF(-grass.width() / 2, -grass.height() / 2,
                                       geom.width() + grass.width(), geom.height() + grass.height()),
                                grass)

        self.town.draw(painter, self.size())


if __name__ == '__main__':
    app = QApplication([])
    med_town = town.Town()
    frame = Frame(med_town, QSize(1200, 900))
    frame.setWindowTitle('Town')
    frame.setWindowIcon(QIcon(QPixmap(getImage('empty_block'))))
    town.Building(32, 64, 0, med_town, town.building_type1)
    town.Building(64, 64, 270, med_town, town.building_type2)
    frame.show()
    app.exec_()
