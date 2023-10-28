from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os

import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui



## Create a subclass of GraphicsObject.
## The only required methods are paint() and boundingRect() 
## (see QGraphicsItem documentation)
class Candlestick(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  ## data must have fields: time, open, close, min, max
        self.generatePicture()
    
    def updateData(self, data):
        self.data = data
        self.generatePicture()

    def generatePicture(self):
        ## pre-computing a QPicture object allows paint() to run much more quickly, 
        ## rather than re-drawing the shapes every time.
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        w = (self.data[1][0] - self.data[0][0]) / 3.
        for (t, open, close, min, max) in self.data:
            p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
            if open > close:
                p.setBrush(pg.mkBrush('r'))
            else:
                p.setBrush(pg.mkBrush('g'))
            p.drawRect(QtCore.QRectF(t-w, open, w*2, close-open))
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        ## boundingRect _must_ indicate the entire area that will be drawn on
        ## or else we will get artifacts and possibly crashing.
        ## (in this case, QPicture does all the work of computing the bouning rect for us)
        return QtCore.QRectF(self.picture.boundingRect())
    


class QuickChart(QWidget):

    requestSymbols = pyqtSignal(int)
    requestData    = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)


        self.data = [  ## fields are (time, open, close, min, max).
                (1., 10, 13, 5, 15),
                (2., 13, 17, 9, 20),
                (3., 17, 14, 11, 23),
                (4., 14, 15, 5, 19),
                (5., 15, 9, 8, 22),
                (6., 9, 15, 8, 16),
            ]
        self.item = Candlestick(self.data)
        self.plt = pg.plot()
        self.plt.addItem(self.item)
        l = QVBoxLayout()

        h = QHBoxLayout()
        self.symbols = []
        self.symbolSelector = QComboBox()
        self.symbolSelector.currentIndexChanged.connect(self.symbolChanged, Qt.DirectConnection)
        self.repopulate_selector()

        self.tfSelector = QComboBox()
        self.tfSelector.addItem('30min')
        self.tfSelector.addItem('1h')
        self.tfSelector.addItem('Daily')

        h.addWidget(self.symbolSelector)
        h.addWidget(self.tfSelector)


        l.addLayout(h)
        l.addWidget(self.plt)
        self.setLayout(l)

        self.setWindowTitle("Quick Chart")

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        
        self.width = int(self.screenWidth*.8)
        self.height = int(self.screenHeight*.7)
        self.resize(self.width, self.height)
        self.move(int(self.screenWidth/2. - self.width/2.), int(self.screenHeight/2. - self.height/2.))

    def dataReceived(self, data):
        self.item.updateData(data)
        # self.item = Candlestick(data)
        # self.plt = pg.plot()
        # self.plt.addItem(self.item)

    def symbolChanged(self, i):
        if i >= 0:
            symbol = self.symbols[i]
            self.requestData.emit(symbol, '')


    def selectionchange(self,i):
        print("Items in the list are :")

    def getSymbols(self, symbols):
        self.symbols = [symbol for symbol in symbols]
        self.repopulate_selector()

    def repopulate_selector(self):
        self.symbolSelector.clear()
        for symbol in self.symbols: self.symbolSelector.addItem(symbol)

    def show(self):
        self.requestSymbols.emit(1)
        super().show()











# plt.setWindowTitle('pyqtgraph example: customGraphicsItem')

