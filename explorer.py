from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QFileDialog)
from PyQt5.QtGui import QKeySequence, QColor, QBrush
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
import json

import csv


class Explorer(QWidget):

    requestData = pyqtSignal()

    def __init__(self, symbols, preset_data, parent=None):
        super().__init__(parent)

        self.symbols = symbols
        self.preset_data = preset_data

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 970
        self.colWidth = 80
        self.wsRatio = .8

        self.headerTitles = list(self.preset_data.keys())

        l = QVBoxLayout()
        self.setLayout(l)

        self.header = QHBoxLayout()
        self.header.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        self.header.setSpacing(15)

        self.symbol = QLabel(self.symbols[0] if len(self.symbols) > 0 else '')
        self.symbol.setStyleSheet('QLabel{color: #f39c12; font-weight: bold; font-size: 18px; min-width: 75px; text-align: center;}')
        self.symbol.setAlignment(Qt.AlignCenter|Qt.AlignVCenter)

        self.showBtn = QPushButton('Load')
        # self.showBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        # self.showBtn.setFixedSize(135, 28)
        self.showBtn.setFixedSize(100, 28)
        self.showBtn.clicked.connect(self.request_data)
        self.initiated = False

        self.exportBtn = QPushButton('Export')
        self.exportBtn.setFixedSize(100, 28)
        self.exportBtn.clicked.connect(self.export)

        self.prevBtn = QPushButton('Prev')
        self.prevBtn.setFixedSize(100, 28)
        self.prevBtn.clicked.connect(self.previous)

        self.nextBtn = QPushButton('Next')
        self.nextBtn.setFixedSize(100, 28)
        self.nextBtn.clicked.connect(self.next)

        self.status = QLabel('')
        self.status.setAlignment(Qt.AlignCenter|Qt.AlignVCenter)

        self.header.addWidget(self.prevBtn)
        self.header.addWidget(self.symbol)
        self.header.addWidget(self.nextBtn)
        self.header.addWidget(self.showBtn)
        self.header.addWidget(self.exportBtn)
        self.header.addWidget(self.status)

        l.addLayout(self.header)

        self.table = QTableWidget()
        # self.table.setRowCount(1)
        self.table.setColumnCount(len(self.headerTitles)+2)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(['Time', 'Close']+self.headerTitles)

        l.addWidget(self.table)

        self.closeButton = QPushButton('Close')
        self.closeButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.closeButton.setEnabled(True)
        self.closeButton.setFixedSize(100,30)
        self.closeButton.clicked.connect(self.close, Qt.DirectConnection)

        self.btnPannel = QHBoxLayout()
        self.btnPannel.addWidget(self.closeButton)
        self.btnPannel.setAlignment(Qt.AlignRight)

        l.addLayout(self.btnPannel)


        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()

        self.resize(int(self.wsRatio*self.screenWidth), int(self.wsRatio*self.screenHeight))
        self.move(int((1.-self.wsRatio)*self.screenWidth/2.),  int((1.-self.wsRatio)*self.screenHeight/2.))

        self.setWindowTitle("Data Explorer")


    def refresh(self):
        if len(self.symbols) > 0:
            try:
                activeSymbol = str(self.symbol.text())
                n = self.symbols.index(activeSymbol)
                self.table.setRowCount(0)
                for i in range(len(self.closes[n])):
                    self.table.insertRow(i)
                    self.table.setItem(i, 0, QTableWidgetItem(self.datetimes[n][(i+1)*-1]))
                    self.table.setItem(i, 1, QTableWidgetItem(str(self.closes[n][(i+1)*-1])))
                    for p in range(2, len(self.headerTitles)+2):
                        value = self.signals[n][(i+1)*-1][p-2]
                        self.table.setItem(i, p, QTableWidgetItem( value ))
                        if value == 'buy':
                            self.table.item(i, p).setBackground(QColor(0,230,118))
                            self.table.item(i, p).setForeground(QBrush(QColor(100, 100, 100)))
                        if value == 'sell': self.table.item(i, p).setBackground(QColor(255,82,82))

            except: pass
        self.enable_buttons()
        self.status.setText('')

    def disable_buttons(self):
        self.prevBtn.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.nextBtn.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.exportBtn.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.showBtn.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.prevBtn.setEnabled(False)
        self.nextBtn.setEnabled(False)
        self.exportBtn.setEnabled(False)
        self.showBtn.setEnabled(False)

    def enable_buttons(self):
        self.prevBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee}")
        self.nextBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee}")
        self.exportBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee}")
        self.showBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee}")
        self.prevBtn.setEnabled(True)
        self.nextBtn.setEnabled(True)
        self.exportBtn.setEnabled(True)
        self.showBtn.setEnabled(True)

    def previous(self):
        if len(self.symbols) > 0:
            activeSymbol = str(self.symbol.text())
            n = self.symbols.index(activeSymbol)
            n -= 1
            if n < 0: n = len(self.symbols) - 1
            self.symbol.setText(self.symbols[n])
            self.request_data()

    def next(self):
        if len(self.symbols) > 0:
            activeSymbol = str(self.symbol.text())
            n = self.symbols.index(activeSymbol)
            n += 1
            if n >= len(self.symbols): n = 0
            self.symbol.setText(self.symbols[n])
            self.request_data()

    def export(self):
        if len(self.symbols) > 0:
            activeSymbol = str(self.symbol.text())
            n = self.symbols.index(activeSymbol)
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            fileName, _ = QFileDialog.getSaveFileName(self,
                "Export {}".format(activeSymbol), "{}.csv".format(activeSymbol), "CSV Files(*.csv)", options = options)
            if fileName:
                header = ['Time', 'Close']+self.headerTitles
                data = []
                for i in range(len(self.closes[n])):
                    d = []
                    d.append(self.datetimes[n][(i+1)*-1])
                    d.append(self.closes[n][(i+1)*-1])
                    for a in range(len(self.headerTitles)):
                        d.append( self.signals[n][(i+1)*-1][a] )
                    data.append(d)
                with open(fileName, 'w', encoding='UTF8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(data)



    def request_data(self):
        if not self.initiated:
            self.showBtn.setText('Refresh')
            self.initiated = True
        self.disable_buttons()
        self.status.setText('Working...')
        self.requestData.emit()

    def data_received(self, datetimes, closes, signals):
        self.datetimes = datetimes
        self.closes = closes
        self.signals = signals
        self.refresh()
