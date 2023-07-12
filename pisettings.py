from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
import json


class PortfolioItemSettings(QWidget):

    save_settings = pyqtSignal(object)

    def __init__(self, symbol, exchange, portfolio, parent=None):
        super().__init__(parent)

        self.symbol = symbol
        self.exchange = exchange
        self.portfolio = deepcopy(portfolio)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 300
        self.height = 600
        self.colWidth = 80

        w = QWidget()
        l = QVBoxLayout()
        self.setLayout(l)

        self.title = QLabel(symbol.upper())
        self.title.setStyleSheet('QLabel{color:#f39c12; font-size: 18px; font-weight: bold; margin-bottom: 3px; margin-right: 0px;}')
        self.title.setAlignment(Qt.AlignRight)

        self.title_exchange = QLabel(exchange.upper())
        self.title_exchange.setStyleSheet('QLabel{color:#888888; font-size: 14px; font-weight: normal; margin-bottom: 3px; margin-right: 3px;}')
        self.title_exchange.setAlignment(Qt.AlignRight)

        self.title_layout = QHBoxLayout()
        self.title_layout.addStretch()
        self.title_layout.setContentsMargins(0,0,0,0)
        self.title_layout.addWidget(self.title)
        self.title_layout.addWidget(self.title_exchange)

        l.addLayout(self.title_layout)

        scroll = QScrollArea(w)
        l.addWidget(scroll)
        scroll.setWidgetResizable(True)
        scrollContent = QWidget(scroll)
        scrollLayout = QVBoxLayout(scrollContent)
        scrollLayout.setAlignment(Qt.AlignTop)
        scrollContent.setLayout(scrollLayout)
        _w = QWidget()
        _l = QGridLayout()
        _l.setHorizontalSpacing(15)
        _l.setVerticalSpacing(10)
        _w.setLayout(_l)
        scrollLayout.addWidget(_w)
        scroll.setWidget(scrollContent)

        # _l.addWidget(__w, 0, 0, 1, 1, alignment=Qt.AlignCenter|Qt.AlignTop)
        # _l.addWidget(line, 1, 0, 1, 1, alignment=Qt.AlignCenter|Qt.AlignTop)
        # l.addWidget(addButton, alignment=Qt.AlignRight)

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/2. - self.height/2.)

        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)

        self.setWindowTitle("{} - Settings".format(self.symbol))


        self.pos_size = QLabel('Position size')

        self.pos_size_value = QSpinBox()
        self.pos_size_value.setRange(1,1000000)
        self.pos_size_value.setMaximum(1000000)
        self.pos_size_value.setValue( self.portfolio[self.symbol]['pos_size'] )
        self.pos_size_value.setPrefix("$ ")

        _l.addWidget(self.pos_size, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.pos_size_value, 1, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)

        row = 2
        self.checkboxes = []
        for name, state in self.portfolio[self.symbol]['permissions'].items():
            name_title = QLabel(name)
            name_value = QCheckBox()
            name_value.setChecked( state )
            self.checkboxes.append(name_value)
            _l.addWidget(name_title, row, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
            _l.addWidget(name_value, row, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
            row += 1

        saveButton = QPushButton('Save')
        saveButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        saveButton.setEnabled(True)
        saveButton.setFixedSize(100,30)
        saveButton.clicked.connect(self.save, Qt.DirectConnection)

        btnPannel = QHBoxLayout()
        btnPannel.setContentsMargins(0, 15, 0, 0)
        btnPannel.addWidget(saveButton)
        btnPannel.setAlignment(Qt.AlignRight)

        l.addLayout(btnPannel)

        self.show()

    def save(self):
        permissions, n = {}, 0
        for name, state in self.portfolio[self.symbol]['permissions'].items():
            permissions[name] = self.checkboxes[n].isChecked()
            n += 1
        settings = {}
        settings['permissions'] = permissions
        settings['pos_size'] = int(self.pos_size_value.value())
        self.portfolio[self.symbol] = settings
        self.save_settings.emit(self.portfolio)
        self.close()
