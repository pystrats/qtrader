from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os

import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot


class EquityPlot(QWidget):


    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 600
        self.height = 300
        self.colWidth = 80

        self._equityPlot = pg.PlotWidget()
        l = QVBoxLayout()
        l.addWidget(self._equityPlot)
        self.setLayout(l)

        # self.tradeNumber = [i+1 for i in range(len(self.equity))]

        styles = {'color':'#eeeeee', 'font-size':'14px'}
        self._equityPlot.setLabel('left', 'Cumulative PnL, $', **styles)
        self._equityPlot.setLabel('bottom', 'Trade #', **styles)

        self._equityPlot.setBackground(QColor(44, 62, 80))

        self.setWindowTitle("Account Equity")

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        
        self.width = int(self.screenWidth*.8)
        self.height = int(self.screenHeight*.7)
        self.resize(self.width, self.height)
        # self.setFixedWidth(self.width)
        # self.setFixedHeight(self.height)
        self.move(int(self.screenWidth/2. - self.width/2.), int(self.screenHeight/2. - self.height/2.))

        # scroll = QScrollArea(w)
        # l.addWidget(scroll)
        # scroll.setWidgetResizable(True)
        # scrollContent = QWidget(scroll)
        # scrollLayout = QVBoxLayout(scrollContent)
        # scrollLayout.setAlignment(Qt.AlignTop)
        # scrollContent.setLayout(scrollLayout)
        # _w = QWidget()
        # _l = QGridLayout()
        # _l.setHorizontalSpacing(15)
        # _l.setVerticalSpacing(10)
        # _w.setLayout(_l)
        # scrollLayout.addWidget(_w)
        # scroll.setWidget(scrollContent)

        """

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/2. - self.height/2.)

        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)

        

        self.hint = QLabel('Order ID')
        self.hint.setStyleSheet("QLabel{color: #eeeeee; font-size: 14px;}")

        self.selector = QComboBox()
        self.repopulate_selector()

        self.cancelBtn = QPushButton('Cancel')
        self.cancelBtn.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.cancelBtn.setEnabled(True)
        self.cancelBtn.setFixedSize(100,30)
        self.cancelBtn.clicked.connect(self.cancel, Qt.DirectConnection)

        self.separator = QLabel('')
        self.separator.setStyleSheet("margin-top: 10px;")

        self.abortBtn = QPushButton('Abort')
        self.abortBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.abortBtn.setEnabled(True)
        self.abortBtn.setFixedSize(100,30)
        self.abortBtn.clicked.connect(self.abort, Qt.DirectConnection)

        # _l.addWidget(self.title, 0, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.hint, 0, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self.selector, 0, 1, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        _l.addWidget(self.cancelBtn, 0, 2, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        # _l.addWidget(self.separator, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        _l.addWidget(self.abortBtn, 2, 2, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        """

    def _plot(self, equity):
        pen = pg.mkPen(color=(243, 156, 18), width=2)
        self._equityPlot.clear()
        tradeNumber = [i+1 for i in range(len(equity))]
        self._equityPlot.plot(tradeNumber, [item for item in equity], pen=pen)
