import sys, time, threading, os, random, math
import threading
from datetime import datetime, timedelta
from copy import deepcopy
import dateutil.parser as parser
import json
import numpy as np

import requests

from numba import cuda

from PyQt5.QtWidgets import (QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QHBoxLayout,
            QLineEdit, QInputDialog, QLabel, QTableWidget, QTableWidgetItem, QGridLayout, QMessageBox, QStatusBar, QDesktopWidget,
            QScrollArea, QShortcut, QAbstractButton, QDialogButtonBox, QFrame, QFileDialog, QHeaderView)
from PyQt5.QtGui import QIcon, QIntValidator, QFont, QPalette, QColor, QKeySequence, QCloseEvent, QFontDatabase, QBrush
from PyQt5.QtCore import Qt, pyqtSlot, QObject, QThread, pyqtSignal, QTimer, QTime
from PyQt5.QtWebEngineWidgets import QWebEngineView

import dash
from dash import dcc, html

from connection import Trader, Connection
from chart import Chart
from dashworker import DashWorker
from completer import LineCompleterWidget
from search import SearchWindow
from msgboxes import InfoMessageBox, InfoWidget
from watchlistitem import WatchlistItem
from settings import Settings
from presets import Presets
from downloader import Downloader
from pisettings import PortfolioItemSettings
from explorer import Explorer
import cudafns

from ibapi.contract import Contract
from ibapi.order import Order

import warnings
warnings.filterwarnings("ignore")


class App(QMainWindow):

    closeSignal = pyqtSignal()

    exportTrades = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.title = 'QuantTrader'
        self.left = 10
        self.top = 10
        self.showExitDialogue = True
        self.exitDialogueShown = False
        self.maximizeOnStartup = False
        self.setWindowTitle(self.title)

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()

        self.width = int(self.screenWidth * .8)
        self.height = int(self.screenHeight * .8)

        self.setGeometry(self.left, self.top, self.width, self.height)

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')
        watchlistMenu = mainMenu.addMenu('Portfolio')
        viewMenu = mainMenu.addMenu('View')
        helpMenu = mainMenu.addMenu('Help')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Quit')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)


        settingsButton = QAction(QIcon('exit24.png'), 'Settings', self)
        settingsButton.setShortcut('Ctrl+Shift+S')
        settingsButton.setStatusTip('Settings')
        settingsButton.triggered.connect(self.show_settings)
        fileMenu.addAction(settingsButton)

        tradesExportButton = QAction(QIcon(), 'Export Trades', self)
        tradesExportButton.setShortcut('Ctrl+Shift+T')
        tradesExportButton.setStatusTip('Export Trades')
        tradesExportButton.triggered.connect(self.export_trades)
        fileMenu.addAction(tradesExportButton)

        exportWatchlistButton = QAction(QIcon(), 'Export Portfolio', self)
        exportWatchlistButton.setShortcut('Ctrl+E')
        exportWatchlistButton.setStatusTip('Export Portfolio')
        exportWatchlistButton.triggered.connect(self.export_watchlist)
        watchlistMenu.addAction(exportWatchlistButton)

        importWatchlistButton = QAction(QIcon(), 'Import Portfolio', self)
        importWatchlistButton.setShortcut('Ctrl+I')
        importWatchlistButton.setStatusTip('Import Portfolio')
        importWatchlistButton.triggered.connect(self.import_watchlist)
        watchlistMenu.addAction(importWatchlistButton)

        aboutButton = QAction(QIcon(), 'About', self)
        aboutButton.setShortcut('Ctrl+Shift+A')
        aboutButton.setStatusTip('About')
        aboutButton.triggered.connect(self.show_about_window)
        helpMenu.addAction(aboutButton)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.statusMsgHolderWidget = QWidget()
        self.statusMsgHolder = QHBoxLayout()
        self.statusMsgHolder.setContentsMargins(9, 0, 0, 4)

        self.statusBarConnectionMsg = QLabel('Disconnected', self)
        # self.statusBarConnectionMsg.setStyleSheet("QLabel {margin-left: 5px;}")

        self.connectionCircle = QLabel('', self)
        self.connectionCircle.setStyleSheet("background-color: red; min-width: 17px; height: 17px;")

        self.statusBarDataStatus = QLabel('Data: Not ready', self)
        self.statusBarDataStatusBox = QLabel('', self)
        self.statusBarDataStatusBox.setStyleSheet("background-color: red; min-width: 17px; height: 17px;")

        self.statusBarCompileStatus = QLabel('Kernels: Not compiled', self)
        self.statusBarCompileStatusBox = QLabel('', self)
        self.statusBarCompileStatusBox.setStyleSheet("background-color: red; min-width: 17px; height: 17px;")

        self.statusBarComputeTimeMsg = QLabel('', self)

        self.statusMsgHolder.addWidget(self.statusBarConnectionMsg, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.connectionCircle, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarDataStatus, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarDataStatusBox, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarCompileStatus, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarCompileStatusBox, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarComputeTimeMsg, alignment=Qt.AlignVCenter)
        self.statusMsgHolderWidget.setLayout(self.statusMsgHolder)

        self.status = QLabel('', self)
        self.status.setAlignment(Qt.AlignRight)

        self.statusBar.addWidget(self.statusMsgHolderWidget)
        self.statusBar.addPermanentWidget(self.status)

        self.table_widget = TableWidget(self)
        self.table_widget.connectionEstablished.connect(self.on_connection_changed, Qt.DirectConnection)
        self.table_widget.status_message.connect(self.status_message, Qt.DirectConnection)
        self.table_widget.update_data_status.connect(self.data_status_update, Qt.DirectConnection)
        self.table_widget.update_kernel_status.connect(self.kernel_status_update, Qt.DirectConnection)
        self.table_widget.update_compute_time.connect(self.compute_time_update, Qt.DirectConnection)
        self.table_widget.closeApp.connect(self.close_without_dialogue, Qt.DirectConnection)
        self.exportTrades.connect(self.table_widget.export_trades, Qt.DirectConnection)
        self.setCentralWidget(self.table_widget)

        self.closeSignal.connect(self.close)

        if self.maximizeOnStartup: self.showMaximized()

        # View
        chartButton = QAction(QIcon(), 'Chart Window', self)
        chartButton.setShortcut('Ctrl+Shift+C')
        chartButton.setStatusTip('Open chart window')
        chartButton.triggered.connect(self.table_widget.open_chart_window)
        viewMenu.addAction(chartButton)

        presetsButton = QAction(QIcon(), 'Strategy Presets', self)
        presetsButton.setShortcut('Ctrl+Shift+P')
        presetsButton.setStatusTip('Open strategy presets')
        presetsButton.triggered.connect(self.table_widget.open_presets_window)
        viewMenu.addAction(presetsButton)

        explorerButton = QAction(QIcon(), 'Data Explorer', self)
        explorerButton.setShortcut('Ctrl+Shift+D')
        explorerButton.setStatusTip('Open Data Explorer')
        explorerButton.triggered.connect(self.table_widget.open_explorer_window)
        viewMenu.addAction(explorerButton)

        self.show()

    def export_trades(self):
        self.exportTrades.emit()

    def data_status_update(self, status):
        if status == 'loading':
            self.statusBarDataStatus.setText('Data: Loading')
            self.statusBarDataStatusBox.setStyleSheet("background-color: #f39c12; min-width: 17px; height: 17px;")
        elif status == 'ready':
            self.statusBarDataStatus.setText('Data: Ready')
            self.statusBarDataStatusBox.setStyleSheet("background-color: green; min-width: 17px; height: 17px;")

    def kernel_status_update(self, status):
        if status == 'compiling':
            self.statusBarCompileStatus.setText('Kernels: Compiling')
            self.statusBarCompileStatusBox.setStyleSheet("background-color: #f39c12; min-width: 17px; height: 17px;")
        elif status == 'ready':
            self.statusBarCompileStatus.setText('Kernels: Compiled')
            self.statusBarCompileStatusBox.setStyleSheet("background-color: green; min-width: 17px; height: 17px;")

    def compute_time_update(self, dt, t):
        self.statusBarComputeTimeMsg.setText('{} {} ms'.format(dt, t))


    def show_settings(self):
        self.settingsWindow = Settings()
        self.settingsWindow.success.connect(self.settings_saved, Qt.DirectConnection)
        self.settingsWindow.timeframe_error.connect(self.settings_timeframe_error, Qt.DirectConnection)
        self.settingsWindow.show()

    def settings_saved(self, success):
        if success:
            msgBox = InfoMessageBox('Info', 'Saved')
            # Update program settings
            self.table_widget.read_settings()
        else: msgBox = InfoMessageBox('Error', 'An error occurred. Settings could not be saved.')

    def settings_timeframe_error(self):
        msg = 'Sorry, you can not use only regular hours data in the analysis but trade during extended hours. Please adjust the settings. Settings were not saved.'
        msgBox = InfoMessageBox('Info', msg, error=True)


    def watchlistToJSON(self, watchlist):
        d = {}
        for reqId, item in watchlist.items():
            c = item.contract
            d[c.symbol] = {
                'exchange' : c.exchange,
                'primaryExchange': c.primaryExchange,
                'currency' : c.currency,
                'secType' : c.secType,
                'conId' : c.conId
            }
        return json.dumps(d)



    def export_watchlist(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,
            "Save File", "portfolio.json", "All Files(*);;JSON Files(*.json)", options = options)
        if fileName:
            with open(fileName, 'w') as f:
                f.write(self.watchlistToJSON(self.table_widget.watchlist))
            self.fileName = fileName
            # self.setWindowTitle(str(os.path.basename(fileName)) + " - Notepad Alpha[*]")

    def import_watchlist(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","JSON Files (*.json)", options=options)
        if fileName:
            with open(fileName) as f:
                wl = json.load(f)

                if len(self.table_widget.watchlist) != 0:
                    for reqId in self.table_widget.watchlist:
                        self.table_widget.removeFromWatchlist(reqId)

                self.table_widget.portfolio = {}

                for symbol, details in wl.items():
                    contract = Contract()
                    contract.symbol = symbol.upper()
                    contract.exchange = details['exchange']
                    contract.primaryExchange = details['primaryExchange']
                    contract.currency = details['currency']
                    contract.secType = details['secType']
                    contract.conId = details['conId']
                    contractDescription = SymbolDescripttion(contract)
                    self.table_widget.addToWatchlist(contractDescription)
            self.table_widget.saveWatchlist()


    def status_message(self, message):
        self.status.setText(message)

    def on_connection_changed(self, code):
        if code == 1:
            self.statusBarConnectionMsg.setText("Connected")
            self.connectionCircle.setStyleSheet("background-color: green; min-width: 17px; height: 100%;")
        else:
            self.statusBarConnectionMsg.setText("Disconnected")
            self.connectionCircle.setStyleSheet("background-color: red; min-width: 17px; height: 100%;")

    def closeEvent(self, event):
        if self.showExitDialogue:
            warning = ExitMessageBox()

            yesButton = QPushButton('Proceed')
            yesButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
            yesButton.setFixedSize(100,30)
            noButton  = QPushButton('Abort')
            noButton.setFixedSize(100,30)

            warning.addButton(yesButton, QMessageBox.YesRole)
            warning.addButton(noButton, QMessageBox.NoRole)
            # warning.setIcon(QMessageBox.Question)
            warning.setWindowTitle('Quit')
            warning.setText("Are you sure you want to exit?")
            g = self.frameGeometry()
            warning.reinit(g)
            ret = warning.exec_()
            if ret == 0:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def close_without_dialogue(self):
        self.showExitDialogue = False
        self.close()

    def closeApp(self, code):
        if code == 1:
            self.closeSignal.emit()
        elif code == 0: self.exitDialogueShown = False

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.statusBar().showMessage('Message in statusbar.')

        self.table_widget = TableWidget(self)
        self.setCentralWidget(self.table_widget)

        # button = QPushButton('PyQt5 button', self)
        # button.setToolTip('This is an example button')
        # button.move(100,70)
        # button.clicked.connect(self.on_click)

        self.show()

    # @pyqtSlot()
    # def on_click(self):
    #     print('PyQt5 button click')

    def getText(self):
        text, okPressed = QInputDialog.getText(self, "Get text","Your name:", QLineEdit.Normal, "")
        if okPressed and text != '':
            print(text)

    def show_about_window(self):
        self.about = AboutWindow()
        self.about.show()


class SymbolDescripttion:
    def __init__(self, contract):
        self.contract = contract

class ExitMessageBox(QMessageBox):
    def __init__(self):
        QMessageBox.__init__(self)

    def reinit(self, g):

        grid_layout = self.layout()

        qt_msgboxex_icon_label = self.findChild(QLabel, "qt_msgboxex_icon_label")
        qt_msgboxex_icon_label.deleteLater()

        qt_msgbox_label = self.findChild(QLabel, "qt_msgbox_label")
        qt_msgbox_label.setAlignment(Qt.AlignCenter)
        grid_layout.removeWidget(qt_msgbox_label)

        qt_msgbox_buttonbox = self.findChild(QDialogButtonBox, "qt_msgbox_buttonbox")
        grid_layout.removeWidget(qt_msgbox_buttonbox)

        grid_layout.addWidget(qt_msgbox_label, 0, 0, alignment=Qt.AlignCenter)
        grid_layout.addWidget(qt_msgbox_buttonbox, 1, 0, alignment=Qt.AlignCenter)

        left, top, width, height = g.left(), g.top(), g.width(), g.height()

        self.move(int(left+width/2.-150),int(top+height/2.-62))

    def event(self, e):
        result = QMessageBox.event(self, e)

        self.setMinimumWidth(300)
        self.setMinimumHeight(125)

        return result

class PopUpWindow(QWidget):

    def __init__(self, label):
        super().__init__()
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(''))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        layout = QGridLayout()
        self.label = QLabel(label)
        layout.addWidget(self.label,0,0)
        self.setGeometry(10, 10, 300, 100)
        self.setLayout(layout)
        self.setWindowTitle("Info")


class ExitDialogue(QWidget):

    yes_no_feedback = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.setGeometry(0,0,350,150)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        self.clicked = False
        self.choice = 0

        self.text = QLabel('Are you sure you want to exit?')

        self.buttonPanel = QHBoxLayout()

        self.yesButton = QPushButton("Proceed")
        self.yesButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
        self.yesButton.setFixedSize(100,30)
        self.yesButton.clicked.connect(self.yes)

        self.noButton = QPushButton("Abort")
        self.noButton.setFixedSize(100,30)
        self.noButton.clicked.connect(self.no)

        self.buttonPanel.addWidget(self.noButton, alignment=Qt.AlignCenter)
        self.buttonPanel.addWidget(self.yesButton, alignment=Qt.AlignCenter)

        layout.addWidget(self.text, alignment=Qt.AlignCenter)
        layout.addLayout(self.buttonPanel)

        self.setLayout(layout)
        self.setWindowTitle('Quit')

    def yes(self):
        self.clicked = True
        self.choice = 1
        self.yes_no_feedback.emit(1)
        self.hide()

    def no(self):
        self.clicked = True
        self.yes_no_feedback.emit(0)
        self.hide()


class AboutWindow(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.setGeometry(250,250,500,225)

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        self.title = QLabel("QuantTrader")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font-weight: bold; color: #eeeeee; font-size: 18px;}")
        layout.addWidget(self.title)

        self.version = QLabel("Version: 1.0.000")
        self.version.setAlignment(Qt.AlignCenter)
        self.version.setStyleSheet("QLabel {color: #eeeeee; font-size: 15px;}")
        layout.addWidget(self.version)

        self.releaseDate = QLabel("Release date: Jul 12, 2023")
        self.releaseDate.setAlignment(Qt.AlignCenter)
        self.releaseDate.setStyleSheet("QLabel {color: #eeeeee; font-size: 15px; margin-bottom: 30px;}")
        layout.addWidget(self.releaseDate)

        self.closeButton = QPushButton("Close")
        self.closeButton.setFixedSize(100,30)
        self.closeButton.clicked.connect(self.close)
        layout.addWidget(self.closeButton, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        self.setWindowTitle("About")

    def close(self):
        self.hide()




class SymbolLookupWindow(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        # self.label = QLabel("Symbol Lookup")
        # layout.addWidget(self.label)
        self.setGeometry(10,10,1280,720)

        searchButton = QPushButton("Search")
        searchButton.setFixedSize(100,30)
        layout.addWidget(searchButton)
        # layout.addStretch()

        self.setLayout(layout)
        self.setWindowTitle("Symbol Lookup")



class Worker(QObject, Connection):

    # def __init__(self):
    #     super(QObject, self).__init__()

    finished = pyqtSignal()
    progress = pyqtSignal(int)
    signalEmitted = pyqtSignal()
    connected = pyqtSignal(int)
    emit_error = pyqtSignal(int, str)
    symbolInfo = pyqtSignal(int, object)
    toAutocompleter = pyqtSignal(object)
    amIConnected = pyqtSignal(bool)
    symInfoToChart = pyqtSignal(int, object)
    sendHistDataToChart = pyqtSignal(object)
    tick = pyqtSignal(int, int, float)
    log = pyqtSignal(str)
    transmit_data_to_downloader = pyqtSignal(int, object)
    tell_downloader_data_is_success = pyqtSignal(int, str, str)
    transmit_valid_id = pyqtSignal(int)
    transmit_order_status = pyqtSignal(int, int, float)
    transmit_commission = pyqtSignal(int, float)

    contractRequestOrigin  = 'unknown'
    sourcesByReqId = {}
    histData = {}

    period = 'daily'

    def initiate(self):
        Connection.__init__(self, '127.0.0.1', 7497, 0)
        # super().connect(self.host, self.port, self.clientID)
        # time.sleep(1.5)
        # super().run()

    def run(self):
        if not self.connectionEstablished:
            super().connect(self.host, self.port, self.clientID)
            print("serverVersion: %s connectionTime: %s" % (self.serverVersion(),
                                                          self.twsConnectionTime()))
            # time.sleep(1)
            self.connectionEstablished = True
            self.connected.emit(1)
            super().run()

            # try:
            #     super().connect(self.host, self.port, self.clientID)
            #     print("serverVersion: %s connectionTime: %s" % (self.serverVersion(),
            #                                                   self.twsConnectionTime()))
            #     # time.sleep(1)
            #     self.connectionEstablished = True
            #     self.connected.emit(1)
            #     super().run()
            #     print(super().isConnected())
            # except:
            #     self.connected.emit(0)

    def connectionStatus(self):
        self.amIConnected.emit(self.isConnected())


    # @pyqtSlot()
    def sym_search(self, arg, source):
        if source == 'chart': self.contractRequestOrigin = 'chart'
        try:
            self.reqMatchingSymbols(218, arg)
        except:
            if source == 'chart' : self.symInfoToChart.emit(0, 0)
            else: self.symbolInfo.emit(0, 0)
        # signalEmitted.emit()

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.transmit_valid_id.emit(orderId)


    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=None):
        if errorCode == 502:
            self.emit_error.emit(errorCode, errorString)
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
        errorMsg = '[{}] {}'.format(errorCode, errorString)
        self.log.emit(errorMsg)
        # self.emit_error.emit(int(errorCode), str(errorString))
        # self.emit_error.emit(0, 'message')

    def convert_contract_details_to_dict(self, contractDescriptions):
        response = {}
        for contractDescription in contractDescriptions:
            e = {
                'symbol' : contractDescription.contract.symbol,
                'exchange' : contractDescription.contract.primaryExchange,
                'currency' : contractDescription.contract.currency,
                'secType' : contractDescription.contract.secType,
                'ID' : contractDescription.contract.conId
            }
            response[contractDescription.contract.symbol] = e
        return response


    def symbolSamples(self, reqId, contractDescriptions):
        # super().symbolSamples(reqId, contractDescriptions)
        if self.contractRequestOrigin == 'chart':
            self.symInfoToChart.emit(1, contractDescriptions)
        else: self.symbolInfo.emit(1, contractDescriptions)
        self.contractRequestOrigin = 'unknown'

    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        msg = '[openOrder] ID {} Symbol {} {} {} Commissions {}'.format(orderId, contract.symbol, order.action, order.totalQuantity, round(orderState.commission, 6))
        self.log.emit(msg)
        commission = round(orderState.commission, 6)
        if commission > 0: self.transmit_commission.emit(orderId, commission)

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        msg = '[orderStatus] ID {} Status {} Filled {} Remaining {} VWAP {}'.format(orderId, status, str(filled), str(remaining), str(avgFillPrice))
        self.log.emit(msg)
        self.transmit_order_status.emit( int(orderId), int(remaining), float(avgFillPrice) )

    def cancel_historical_data(self, reqId):
        self.cancelHistoricalData(reqId)

    def downloader_requested_data(self, reqId, endDateTime, RTH_only, contract):
        dataType = "ADJUSTED_LAST"
        if contract.secType == "STK":
            contract.exchange = "SMART"
            contract.currency = "USD"
        if contract.secType == "CASH":
            contract.exchange = "IDEALPRO"
            contract.primaryExchange = ""
            contract.currency = "USD"
            dataType = "AGGTRADES"
        if contract.secType == "CRYPTO":
            contract.exchange = "PAXOS"
            dataType = "AGGTRADES"

        useRTH = 1 if RTH_only else 0

        self.reqHistoricalData(reqId, contract, endDateTime, "3 D", "1 min", dataType, useRTH, 1, False, [])



    def getHistData(self, reqId, contractDescription, period):
        self.sourcesByReqId[reqId] = 'chart'
        self.period = period
        try:
            self.histData[reqId] = {
                'Date' :  [],
                'Open' :  [],
                'High' :  [],
                'Low'  :  [],
                'Close':  [],
                'Volume': []
            }

            # queryTime = datetime.today().strftime("%Y%m%d-%H:%M:%S")
            contract = Contract()
            contractRef = contractDescription.contract

            contract.symbol = contractRef.symbol
            contract.secType = contractRef.secType
            contract.currency = contractRef.currency
            if contract.secType == "STK":
                contract.exchange = "SMART"
                contract.currency = "USD"
            if contractRef.secType == "CASH":
                contract.exchange = "IDEALPRO"
                contract.primaryExchange = ""
                contract.currency = "USD"
            if contractRef.secType == "CRYPTO":
                contract.exchange = "PAXOS"

            reqPeriod = "1 day"
            reqLookback = "1 Y"
            if period == 'weekly':
                reqPeriod = "1 week"
                reqLookback = "5 Y"
            elif period == '1H':
                reqPeriod = "1 hour"
                reqLookback = "25 D"
            elif period == '30min':
                reqPeriod = "30 mins"
                reqLookback = "12 D"
            elif period == '5min':
                reqPeriod = "5 mins"
                reqLookback = "2 D"

            self.reqHistoricalData(reqId, contract, '', reqLookback, reqPeriod, "MIDPOINT", 1, 1, False, [])
        except: msgBox = InfoMessageBox('Error', 'Historical data request failed')

    def historicalData(self, reqId:int, bar):
        # print("HistoricalData. ReqId:", reqId, "BarData.",
        # type(bar.date),
        # type(bar.open),
        # type(bar.high),
        # type(bar.close),
        # type(bar.volume)
        # )
        if reqId in self.sourcesByReqId.keys():
            dtFormat = '%Y%m%d' if self.period in ['daily', 'weekly'] else '%Y%m%d %H:%M:%S'
            if self.period in ['30min', '5min']: dtFormat = '%Y%m%d %H:%M:%S.%f'
            dt = bar.date if self.period in ['daily', 'weekly'] else bar.date[:17]
            self.histData[reqId]['Date'].append( parser.parse(dt) )
            self.histData[reqId]['Open'].append(bar.open)
            self.histData[reqId]['High'].append(bar.high)
            self.histData[reqId]['Low'].append(bar.low)
            self.histData[reqId]['Close'].append(bar.close)
            self.histData[reqId]['Volume'].append(bar.volume)
        else:
            self.transmit_data_to_downloader.emit(reqId, bar)


    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        if reqId in self.sourcesByReqId.keys():
            self.sendHistDataToChart.emit(self.histData[reqId])
        else: self.tell_downloader_data_is_success.emit(reqId, start, end)
        # print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)


    def subscribeToStreamingData(self, reqId:int, contractDescription):
        contract = Contract()
        contractRef = contractDescription.contract

        contract.symbol = contractRef.symbol
        contract.secType = contractRef.secType
        contract.currency = contractRef.currency
        if contract.secType == "STK":
            contract.exchange = "SMART"
            contract.currency = "USD"
        if contractRef.secType == "CASH":
            contract.exchange = "IDEALPRO"
            contract.primaryExchange = ""
            contract.currency = "USD"
        if contractRef.secType == "CRYPTO":
            contract.exchange = "PAXOS"

        self.reqMktData(reqId, contract, "", False, False, [])

    def cancelStreamingData(self, regId:int):
        self.cancelMktData(regId)

    def tickPrice(self, reqId, tickType, price: float, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        # print("TickPrice. TickerId:", reqId, "tickType:", tickType,
        #             "Price:", price, "CanAutoExecute:", attrib.canAutoExecute,
        #             "PastLimit:", attrib.pastLimit)
        self.tick.emit(reqId, tickType, price)
        # if tickType == TickTypeEnum.BID or tickType == TickTypeEnum.ASK:
        #     print("PreOpen:", attrib.preOpen)
        # else:
        #     print()



class TableWidget(QWidget):

    symInfoRequested = pyqtSignal(str, int)
    connectionEstablished = pyqtSignal(int)
    status_message = pyqtSignal(str)
    sendMktStateToWatchlist = pyqtSignal(int)
    update_data_status = pyqtSignal(str)
    update_kernel_status = pyqtSignal(str)
    update_compute_time = pyqtSignal(str, int)
    tell_downloader_to_stop = pyqtSignal()
    data_to_explorer = pyqtSignal(object, object, object)
    transmit_order = pyqtSignal(int, object, object)
    closeApp = pyqtSignal()

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.debug = False
        self.useTimeAPI = False
        self.show_gauge_panel = False

        self.REQUEST_LIMIT_PER_SECOND = 25
        self.MIN_DATAPOINTS_REQUIRED = 6000  # 2680
        self.HISTORY_EXCESS_TO_LOAD_PERCENT = 30
        self.MAX_HISTORY_DEPTH_REALTIME = self.MIN_DATAPOINTS_REQUIRED * 1.5
        self.MAX_ATTEMPTS_TO_FETCH_TIMEZONE = 20
        self.histDataRequestId = 1000000
        self.symbols = []
        self.explorerReady = False
        self.explorerInitiated = False
        self.histDataRequestsActive = []
        self.logActive = True

        self.CUDA_DEVICE_ID = 0
        self.THREADS_PER_BLOCK = 128
        self.MIN_DATAPOINTS = cudafns.MIN_DATAPOINTS


        self.isConnected = False
        self.isExecuting = False
        self.worker = None
        self.searchLastRequested = time.time()
        self.searchQuery = ''
        self.streamingDataReqId = 2000000
        self.config_path = '{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'config' )
        self.settings = {}
        self.read_settings()

        self.TIMEFRAME = int(self.settings['strategy']['timeframe'])
        self.MIN_1MIN_HISTORY_BARS_REQUIRED = self.TIMEFRAME * self.MIN_DATAPOINTS_REQUIRED * int((100 + int(self.settings['strategy']['hist_excess']))/100.)
        self.historicalDataReady = False
        self.lastHistoricalDataRequest = None
        self.MAX_HISTORICAL_DATA_TIMEOUT_SECONDS = 240

        self.timeframe_marks_ready = False
        self.last_tint = -1
        self.initialRun = True

        self.maxT = 10*10
        self.positionsCLosedToday = False
        self.orderID = 3000000
        self.activeOrders = []
        self.pending_orders = {}

        # c1 = {}
        # c1.contract = Contract()
        # cc1.contract.symbol = 'AAPL'
        # c1.contract.primaryExchange = 'NYSE'
        # c2 = {}
        # c2 = Contract()
        # c2.symbol = 'MSFT'
        # c2.primaryExchange = 'NASDAQ'
        self.todaysHolidayKnown = False
        self.holidays = {}
        self.readHolidaysFile()
        self.lastKnownDay = -1
        self.sessionToday = {
            'premarketOpen' : 40000,
            'premarketClose' : 93000,
            'marketOpen' : 93000,
            'marketClose' : 160000,
            'aftermarketOpen' : 160000,
            'aftermarketClose' : 200000
        }
        self.todaysHolidayName = ''
        self.isHoliday = False
        self.holidayName = ''
        self.closedAllDay = False
        self.watchlist = {}
        self.watchlistItems = {}
        self.preset_data = {}
        self.load_presets()
        self.portfolio = {}
        self.loadPortfolio()
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.layout = QGridLayout(self)
        self.loadPositions()

        if self.show_gauge_panel:
            self.gaugePanel = QWidget()
            self.gaugePanelLayout = QVBoxLayout()
            self.browser = QWebEngineView()
            self.gaugePanelLayout.addWidget(self.browser)
            self.gaugePanel.setLayout(self.gaugePanelLayout)
            self.gaugePanel.setMaximumHeight(160)
            self.gaugePanel.setFixedWidth(1120)
            self.gaugePanelHTML = ''
            with open(self.dir+'/html/gauge.html', 'r') as file:
                html = file.read()
                self.gaugePanelHTML = html
            self.browser.setHtml(self.gaugePanelHTML.replace(
                "gaugeReading", "25"
            ).replace(
                "risk_value", "1250"
            ))

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()


        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.posTab = QWidget()
        self.tradesTab = QWidget()
        self.trades = []
        self.tabs.resize(300,200)



        # Add tabs
        self.tabs.addTab(self.tab1,"Dashboard")
        self.tabs.addTab(self.posTab, "Positions")
        self.tabs.addTab(self.tradesTab, "Trades")
        self.tabs.addTab(self.tab2,"Pending Liquidations")
        self.tabs.addTab(self.tab3,"Log")

        # Create first tab


        self.tab1.wrapper = QVBoxLayout(self)
        self.tab1.setLayout(self.tab1.wrapper)

        self.tab1.scroll = QScrollArea(self.tab1)
        self.tab1.wrapper.addWidget(self.tab1.scroll)
        self.tab1.scroll.setWidgetResizable(True)
        self.tab1.scrollContent = QWidget(self.tab1.scroll)

        self.tab1.scrollLayout = QVBoxLayout(self.tab1.scrollContent)
        self.tab1.scrollContent.setLayout(self.tab1.scrollLayout)
        self.tab1.w = QWidget()
        self.tab1.layout = QGridLayout()
        self.tab1.layout.setAlignment(Qt.AlignTop)
        self.tab1.w.setLayout(self.tab1.layout)
        self.tab1.scrollLayout.addWidget(self.tab1.w)
        self.tab1.scroll.setWidget(self.tab1.scrollContent)






        self.symbolSerachText = QLineEdit()
        # self.symbolSerachText.setValidator(QIntValidator())
        self.symbolSerachText.setMaxLength(30)
        self.symbolSerachText.setAlignment(Qt.AlignLeft)
        # self.symbolSerachText.setFont(QFont("Arial",12))
        self.symbolSerachText.setFixedSize(250,28)
        # self.symbolSerachText.setPlaceholderText("Symbol or company name")
        self.symbolSerachText.setTextMargins(10, 1, 10, 1)

        self.defaultButtonWidth = 100
        self.defaultButtonHeight = 25

        self.searchButton = QPushButton("Search")
        # self.searchButton.move(10,10)
        # self.searchButton.setGeometry(20, 15, 50, 10)
        self.searchButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.searchButton.clicked.connect(self.search_button_clicked)

        self.connectButton = QPushButton("Connect")
        self.connectButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.connectButton.clicked.connect(self.establish_connection)
        self.disable_connect_button()

        self.startButton = QPushButton("Start")
        self.startButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.startButton.clicked.connect(self.start)
        self.disable_start_button()

        self.stopButton = QPushButton("Stop")
        self.stopButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.stopButton.clicked.connect(self.stop)
        self.disable_stop_button()

        self.buttonPanel = QHBoxLayout()
        self.buttonPanel.addWidget(self.connectButton)
        self.buttonPanel.addWidget(self.startButton)
        self.buttonPanel.addWidget(self.stopButton)

        # self.watchlistLabel = QLabel('Watchlist')
        # self.watchlistLabel.setStyleSheet("QLabel {color: #eeeeee; font-weight: normal; font-size: 12px;}")

        self.watchlistWidget = QWidget()
        self.watchlistLayout = QVBoxLayout()
        self.watchlistLayout.setAlignment(Qt.AlignTop)
        # self.watchlistLayout.addStretch()
        self.refreshWatchlistLayout()
        self.watchlistWidget.setLayout(self.watchlistLayout)
        self.loadWatchlist()
        self.get_symbols()

        self.connectionLabel = QLabel("Status: disconnected")
        self.connectionLabel.setAlignment(Qt.AlignRight)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.showTime)
        self.timer.start(1000)

        self.clock = QWidget()
        # self.clock.setFixedHeight(28)
        self.clockLayout = QHBoxLayout()
        self.clockLayout.setAlignment(Qt.AlignTop)
        self.clockLayout.setContentsMargins(0, 15, 0, 0)
        self.clockTxt = QLabel('')
        self.clockTime = QLabel('')
        self.clockLayout.addWidget(self.clockTxt)
        self.clockLayout.addWidget(self.clockTime)
        self.clock.setLayout(self.clockLayout)

        self.mktStatusWidget = QWidget()
        self.mktStatusTable = QGridLayout()
        self.mktStatusTable.setContentsMargins(0, 5, 0, 0)
        # self.mktStatusWidget.setFixedHeight(28)
        self.mktStatusLayout = QHBoxLayout()
        self.mktStatusLayout.setAlignment(Qt.AlignTop|Qt.AlignRight)
        self.mktStatusLabel = QLabel('')
        self.mktStatus = QLabel('')
        self.mktStatusLayout.addWidget(self.mktStatusLabel, alignment=Qt.AlignTop|Qt.AlignRight)
        self.mktStatusTable.addLayout(self.mktStatusLayout, 0, 0, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        self.holidayLayout = QHBoxLayout()
        self.holidayLayout.setAlignment(Qt.AlignTop|Qt.AlignRight)
        self.holidayLabel = QLabel('')
        self.holidayLabel.setStyleSheet("QLabel{color: #aaaaaa;}")
        # self.holidayLayout.addWidget(self.holidayLabel)
        self.mktStatusTable.addWidget(self.holidayLabel, 1, 0, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        # self.mktStatusLayout.addWidget(self.mktStatus, alignment=Qt.AlignTop|Qt.AlignRight)
        self.mktStatusWidget.setLayout(self.mktStatusTable)
        self.mktState = 0
        self.prevMktState = -1



        self.tab1.layout.addLayout(self.buttonPanel, 0, 3, alignment=Qt.AlignRight)
        self.tab1.layout.addWidget(self.symbolSerachText, 0, 0)
        self.tab1.layout.addWidget(self.searchButton, 0, 1)
        self.tab1.layout.addWidget(self.clock, 1, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        self.tab1.layout.addWidget(self.mktStatusWidget, 2, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        if self.show_gauge_panel:
            self.tab1.layout.addWidget(self.gaugePanel, 3, 0, 1, 4, alignment=Qt.AlignCenter|Qt.AlignTop)
        self.tab1.layout.addWidget(self.watchlistWidget, 4, 0, 20, 4, alignment=Qt.AlignTop|Qt.AlignCenter)
        # self.tab1.layout.addWidget(self.connectButton, 0, 8, 1, 3)
        # self.tab1.layout.addWidget(self.startButton, 0, 11, 1, 3)
        # self.tab1.layout.addWidget(self.stopButton, 0, 14, 1, 3, alignment=Qt.AlignRight)
        # self.tab1.layout.setHorizontalSpacing(20)
        # self.tab1.layout.addWidget(self.connectionLabel, 2, 5)



        # self.tab1.layout.addLayout(self.stock, 1, 0, alignment=Qt.AlignLeft)


        self.tab1.setLayout(self.tab1.layout)

        # Second tab ###########################################################
        self.createTable()
        self.tab2.layout = QVBoxLayout()
        self.tab2.layout.addWidget(self.tableWidget)
        self.tab2.setLayout(self.tab2.layout)

        # Positions ############################################################
        self.posTab.wrapper = QVBoxLayout(self)
        self.posTab.setLayout(self.posTab.wrapper)
        self.posTable = QTableWidget()
        self.posTable.setColumnCount(len(self.preset_data.keys()))
        self.posTable.setRowCount(len(self.watchlist.keys()))
        self.posTab.wrapper.addWidget(self.posTable)
        if len(self.watchlist.keys()) > 0:
            self.posTable.setVerticalHeaderLabels([ self.watchlist[key].contract.symbol.upper() for key in list(self.watchlist.keys()) ])
        if len(self.preset_data.keys()) > 0:
            self.posTable.setHorizontalHeaderLabels( list(self.preset_data.keys()) )

        watchlist_keys = []
        for key in list(self.watchlist.keys()):
            watchlist_keys.append(self.watchlist[key].contract.symbol)

        preset_keys = list(self.preset_data.keys())
        for symIX in range(len(self.watchlist.keys())):
            for algoIX in range(len(self.preset_data.keys())):
                value = self.positions[ watchlist_keys[symIX] ]['positions'][ preset_keys[algoIX] ]
                w_item = QTableWidgetItem( str(value) )
                w_item.setTextAlignment(Qt.AlignCenter)
                self.posTable.setItem(symIX, algoIX, w_item)
                if value > 0:
                    self.posTable.item(symIX, algoIX).setBackground(QColor(0,230,118))
                    self.posTable.item(symIX, algoIX).setForeground(QBrush(QColor(100, 100, 100)))

        # Trades ###############################################################
        self.tradesTab.wrapper = QVBoxLayout(self)
        self.tradesTab.setLayout(self.tradesTab.wrapper)
        self.tradesTable = QTableWidget()
        self.tradesTable.setColumnCount(6)
        self.tradesTable.setRowCount(0)
        self.tradesTable.setColumnWidth(0, 320)
        self.tradesTable.verticalHeader().setVisible(False)
        self.tradesTable.setHorizontalHeaderLabels( ['Time', 'Symbol', 'Algorithm', 'Action', 'Qty', 'VWAP'] )
        self.tradesTab.wrapper.addWidget(self.tradesTable)

        # Log tab ##############################################################
        self.tab3.wrapper = QVBoxLayout(self)
        self.tab3.setLayout(self.tab3.wrapper)

        self.logTable = QTableWidget()
        self.logTable.move(0,0)
        self.logTable.setColumnCount(1)
        self.logTable.horizontalHeader().setVisible(False)
        self.logTable.verticalHeader().setVisible(False)
        self.logTable.setColumnWidth(0, int(self.screenWidth*.8))

        # header = self.logTable.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.Stretch)
        # header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(2, QHeaderView.ResizeToContents)


        self.tab3.wrapper.addWidget(self.logTable)
        # self.tab3.layout.addWidget(self.logTable, alignment=Qt.AlignTop)
        # self.logTable.setItem(1, 0, QTableWidgetItem("text2"))


        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


        self.presets = Presets()
        self.presets.send_presets_to_app.connect(self.new_presets_received, Qt.DirectConnection)


        # Run Dash
        self.dashThread = QThread()
        self.dashWorker = DashWorker()
        self.dashWorker.moveToThread(self.dashThread)
        self.dashThread.started.connect(self.dashWorker.run)
        # self.dashWorker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.dashWorker.finished.connect(self.dashThread.quit)
        self.dashWorker.finished.connect(self.dashWorker.deleteLater)
        self.dashThread.finished.connect(self.dashThread.deleteLater)
        self.dashThread.start()

        # self.dashThread.finished.connect(
        #     lambda: self.enable_connect_button()
        # )
        # self.dashThread.finished.connect(
        #     lambda: self.connectionLabel.setText("Status: disconnected")
        # )

        """
        self.w = LineCompleterWidget()
        self.w.resize(400, self.w.sizeHint().height())
        self.w.show()
        """

        self.chartWindow = Chart()
        self.dashWorker.requestWindowSize.connect(self.chartWindow.get_browser_size, Qt.DirectConnection)
        self.chartWindow.transmitWindowSize.connect(self.dashWorker.update_window_size, Qt.DirectConnection)

        self.chartWindow.resized.connect(self.dashWorker.resized, Qt.DirectConnection)
        # self.chartWindow.button.clicked.connect(self.dashWorker.update_figure, Qt.DirectConnection)

        self.chartWindow.tellDashToChangeState.connect(self.dashWorker.stateChange, Qt.DirectConnection)
        self.chartWindow.sendDataToDash.connect(self.dashWorker.newDataReceived, Qt.DirectConnection)
        self.dashWorker.ready.connect(self.startupRoutine, Qt.DirectConnection)

        self.currentTimeISAheadOfEDT = False
        self.timeDIfferenceWithEDT = 0
        self.timeMultiplier = 1
        self.timeInfoReady = False



    def data_status_update(self, msg):
        self.update_data_status.emit(msg)

    def read_settings(self):
        filename = self.config_path + '/settings.json'
        if os.path.isfile(filename):
            with open(filename) as f:
                self.settings = json.load(f)
        else:
            self.settings = {
                "strategy": {"timeframe": 5, "onlyRTH_history": True, "onlyRTH_trading": True, "trade_all": True, "pos_size": 50},
                "connection": {"port": 4002, "clientId": 1},
                "server": {"address": "000.000.000.000", "key": "", "role": "Client"},
                "common": {"checkUpdates": True, "risk": 300},
                "margin": {"intraday": 50, "overnight": 25}}


    def load_presets(self):
        self.preset_data = {}
        filename = '{}{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/', 'presets.json' )
        if os.path.isfile(filename):
            with open(filename) as f:
                self.preset_data = json.load(f)


    def new_presets_received(self, presets):
        self.preset_data = deepcopy(presets)
        for symbol, settings in self.portfolio.items():
            pending_exclusions = []
            for algo in settings['permissions'].keys():
                if algo not in presets: pending_exclusions.append(algo)
            for algo in pending_exclusions: self.portfolio[symbol]['permissions'].pop(algo, None)
            for algo in self.preset_data.keys():
                if algo not in self.portfolio[symbol]['permissions']:
                    self.portfolio[symbol]['permissions'][algo] = self.settings['strategy']['trade_all']
        self.savePortfolio()


    def log(self, level, msg):
        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        t = t.strftime("%Y-%m-%d %I:%M:%S.%f %p")
        fullMsg = '{} [{}] {}\n'.format(t, level.upper(), msg)
        rowPosition = self.logTable.rowCount()
        self.logTable.insertRow(rowPosition)
        self.logTable.setItem(rowPosition, 0, QTableWidgetItem(fullMsg))
        fileName = self.logInfo if level == 'info' else self.logError
        if not self.debug and self.logActive:
            with open(fileName, 'a+') as f: f.write(fullMsg)

    def update_position_table(self):
        watchlist_keys = []
        for key in list(self.watchlist.keys()):
            watchlist_keys.append(self.watchlist[key].contract.symbol)
        preset_keys = list(self.preset_data.keys())
        for symIX in range(len(self.watchlist.keys())):
            for algoIX in range(len(self.preset_data.keys())):
                value = self.positions[ watchlist_keys[symIX] ]['positions'][ preset_keys[algoIX] ]
                self.posTable.setItem(symIX, algoIX, QTableWidgetItem( str(value) ))
                if value > 0:
                    self.posTable.item(symIX, algoIX).setBackground(QColor(0,230,118))
                    self.posTable.item(symIX, algoIX).setForeground(QBrush(QColor(100, 100, 100)))


    def subscribe(self):
        self.downloadThread = QThread()
        self.downloader = Downloader()

        """
        self.worker.signalEmitted.connect(self.readWorkerSignal, Qt.DirectConnection)
        self.worker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.worker.emit_error.connect(self.error_received, Qt.DirectConnection)
        self.worker.symbolInfo.connect(self.symbolInfoReceived, Qt.DirectConnection)

        # Connection query
        self.chartWindow.amIConnected.connect(self.worker.connectionStatus, Qt.DirectConnection)
        self.worker.amIConnected.connect(self.chartWindow.updateConnectionStatus, Qt.DirectConnection)

        # Matching symbols (source=chart)
        self.chartWindow.lookupRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.symInfoToChart.connect(self.chartWindow.lookupResultsReceived, Qt.DirectConnection)
        self.chartWindow.requestHistData.connect(self.worker.getHistData, Qt.DirectConnection)
        self.worker.sendHistDataToChart.connect(self.chartWindow.newDataReceived, Qt.DirectConnection)

        self.worker.tick.connect(self.tick, Qt.DirectConnection)
        """

        self.downloader.moveToThread(self.downloadThread)

        # self.downloadThread.started.connect(self.downloader.main)
        self.downloader.finished.connect(self.downloadThread.quit)
        self.downloader.finished.connect(self.downloader.deleteLater)
        self.downloadThread.finished.connect(self.downloadThread.deleteLater)

        self.downloadThread.start()

        self.downloadThread.finished.connect(
            lambda: self.enable_connect_button()
        )
        self.downloadThread.finished.connect(
            lambda: self.connectionLabel.setText("Status: disconnected")
        )

        self.downloader.receive_watchlist(self.watchlist)
        self.downloader.receive_datapoint_requirement(self.MIN_DATAPOINTS_REQUIRED, int(self.settings['strategy']['hist_excess']))
        self.downloader.receive_settings(self.settings)
        # self.downloader.main()



    def startupRoutine(self):
        logFileDirectory = '{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'log' )
        if not os.path.exists(logFileDirectory): os.makedirs(logFileDirectory)
        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        t = t.strftime("%Y-%m-%d_%H-%M-%S.%f")
        self.logInfo  = '{}/{}_INFO.log'.format(logFileDirectory, t)
        self.logError = '{}/{}_ERROR.log'.format(logFileDirectory, t)
        self.log('info', 'Starting application')
        # Timezone
        api_endpoint = "http://worldtimeapi.org/api/timezone/America/New_York"
        response = None
        if self.useTimeAPI or not self.debug:
            nAttempts, success = 0, False
            while nAttempts < self.MAX_ATTEMPTS_TO_FETCH_TIMEZONE and not success:
                nAttempts += 1
                logmsg = 'Fetching timezone information. Local time {} Attempt {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nAttempts)
                statusmsg = 'Fetching timezone information. Attempt {}'.format(nAttempts)
                self.status_message.emit(statusmsg)
                self.log('info', logmsg)
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': 1,
                        "Content-Type": "json"
                        }
                    response = requests.get(api_endpoint, headers={})
                    success = True
                    self.log('info', 'Timezone data received. New York time {}'.format(datetime.utcfromtimestamp(int(response.json()['unixtime']))))
                except: pass
            if not success:
                self.status_message.emit('ERROR. Failed fetching timezone info')
                msgBox = InfoMessageBox('Error', '\nFailed fetching timezone info. \n\nPLEASE RESTART APPLICATION.\n')
                return

            unixtime = int(response.json()['unixtime'])
            nytime = response.json()['datetime']
        else:
            """DEBUG"""
            unixtime = 1685003072
            nytime = '2023-07-14 17:05:00'

        # edt = datetime.utcfromtimestamp(unixtime)
        edt = parser.parse(nytime)
        edt = datetime(edt.year, edt.month, edt.day, edt.hour, edt.minute, edt.second)
        local = datetime.now()
        if edt > local:
            self.currentTimeISAheadOfEDT = False
            self.timeDIfferenceWithEDT = int((edt-local).seconds/3600)
        else:
            self.currentTimeISAheadOfEDT = True
            self.timeDIfferenceWithEDT = int((local-edt).seconds/3600)
        self.timeMultiplier = -1 if self.currentTimeISAheadOfEDT else 1
        self.timeInfoReady = True
        self.status_message.emit('')



    def readHolidaysFile(self):
        path = '{}/{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'config', 'holidays.json' )
        if os.path.isfile(path):
            with open(path) as f:
                holidays = json.load(f)
                self.holidays = {}
                for name, details in holidays.items():
                    closedAllDay    = details['closedAllDay']
                    regularCloseDT  = details['date'] + ' ' + details['regularSessionClose'] if not closedAllDay else ''
                    extendedCloseDT = details['date'] + ' ' + details['extendedSessionClose'] if not closedAllDay else ''
                    d = {
                        'date' : datetime.strptime(details['date'], "%Y-%m-%d"),
                        'closedAllDay' : closedAllDay,
                        'regularSessionClose' : parser.parse(details['regularSessionClose']) if not closedAllDay else '',
                        'extendedSessionClose' : parser.parse(details['extendedSessionClose']) if not closedAllDay else ''
                    }
                    self.holidays[name] = d
        else: return {}

    def refreshWatchlistLayout(self):
        for i in reversed(range(self.watchlistLayout.count())):
            self.watchlistLayout.itemAt(i).widget().setParent(None)
        _w = QWidget()
        title = QHBoxLayout()
        title.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        title.setContentsMargins(0, 0, 0, 0)
        title.setSpacing(0)
        for column in ['Symbol', 'Exchange', 'Prev. Close', 'Change', 'Bid', 'Last', 'Ask', 'Position', 'Margin', 'Execution', 'Auction', 'Session', 'History', '']:
            w = QLabel(column)
            w.setFixedWidth(80)
            w.setStyleSheet("QLabel{color:#cccccc}")
            w.setAlignment(Qt.AlignCenter|Qt.AlignTop)
            title.addWidget(w)
        _w.setLayout(title)
        self.watchlistLayout.addWidget(_w)
        self.watchlistItems = {}
        line = QWidget()
        line.setFixedSize(1040, 1)
        line.setStyleSheet("QWidget{background-color:#aaaaaa; text-align: left}")
        self.watchlistLayout.addWidget(line)
        for reqId in self.watchlist:
            item = WatchlistItem(reqId, self.watchlist[reqId].contract, self.get_total_positions(reqId))
            self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
            self.watchlistItems[reqId] = item
        if len(self.watchlist) == 0:
            self.noItemsInWatchlist()
        return

    def export_trades(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,
            "Export Trades", "Trades {}.csv".format(datetime.now().strftime("%Y-%b-%d %H.%M.%S")), "CSV Files(*.csv)", options = options)
        if fileName:
            header = ['Time', 'Symbol', 'Algorithm', 'Action', 'Qty', 'VWAP']
            data = []
            for i in range(self.trades):
                d = []
                for j in range(len(self.trades[i])):
                    d.append(str(self.trades[i][j]))
                data.append(d)
            with open(fileName, 'w', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(data)

    def get_total_positions(self, reqId):
        symbol = self.watchlist[reqId].contract.symbol
        total_positions = 0
        for _, position in self.positions[symbol]['positions'].items():
            total_positions += int(position)

        return total_positions

    def watchlistEmptyWidget(self):
        noItemW = QWidget()
        noITemLayout = QHBoxLayout()
        noITemLayout.setAlignment(Qt.AlignCenter)
        noItemLabel = QLabel('Watchlist is empty')
        noItemLabel.setStyleSheet('QLabel{color: #cccccc; margin-right: 40px;}')
        noITemLayout.addWidget(noItemLabel)
        noItemW.setLayout(noITemLayout)
        self.noitem = [noItemW]

    def noItemsInWatchlist(self):
        self.watchlistEmptyWidget()
        self.watchlistLayout.addWidget(self.noitem[0])

    def getMktState(self):
        self.sendMktStateToWatchlist.emit(self.mktState)

    def watchlistToJSON(self, watchlist):
        d = {}
        for reqId, item in watchlist.items():
            c = item.contract
            d[c.symbol] = {
                'exchange' : c.exchange,
                'primaryExchange': c.primaryExchange,
                'currency' : c.currency,
                'secType' : c.secType,
                'conId' : c.conId
            }
        return json.dumps(d)

    def watchlistPath(self):
        return '{}/{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'config', 'watchlist.json' )

    def saveWatchlist(self):
        fileName = self.watchlistPath()
        with open(fileName, 'w') as f:
            f.write(self.watchlistToJSON(self.watchlist))


    def savePortfolio(self):
        fileName = self.config_path + '/portfolio.json'
        with open(fileName, 'w') as f:
            f.write( json.dumps(self.portfolio) )

    def savePositions(self):
        fileName = self.config_path + '/positions.json'
        with open(fileName, 'w') as f:
            f.write( json.dumps(self.positions) )


    def loadWatchlist(self):
        fileName = self.watchlistPath()
        if os.path.isfile(fileName):
            with open(fileName) as f:
                wl = json.load(f)

                for symbol, details in wl.items():
                    contract = Contract()
                    contract.symbol = symbol.upper()
                    contract.exchange = details['exchange']
                    contract.primaryExchange = details['primaryExchange']
                    contract.currency = details['currency']
                    contract.secType = details['secType']
                    contract.conId = details['conId']
                    contractDescription = SymbolDescripttion(contract)
                    self.addToWatchlist(contractDescription, startup=True)


    def loadPortfolio(self):
        filename = self.config_path + '/portfolio.json'
        if os.path.isfile(filename):
            with open(filename) as f:
                self.portfolio = json.load(f)

    def loadPositions(self):
        filename = self.config_path + '/positions.json'
        if os.path.isfile(filename):
            with open(filename) as f:
                self.positions = json.load(f)

    def update_portfolio(self, portfolio):
        self.portfolio = deepcopy(portfolio)
        self.savePortfolio()

    def update_portfolio_settings(self, symbol):
        exchange = ''
        for reqId, contractDescription in self.watchlist.items():
            if contractDescription.contract.symbol == symbol:
                exchange = contractDescription.contract.primaryExchange
                break
        self.portfolio_settings_window = PortfolioItemSettings(symbol, exchange, self.portfolio)
        self.portfolio_settings_window.save_settings.connect(self.update_portfolio, Qt.DirectConnection)

    def addToWatchlist(self, contractDescription, startup = False):
        if len(self.watchlist) == 0: self.noitem[0].deleteLater()
        self.streamingDataReqId += 1
        self.watchlist[self.streamingDataReqId] = contractDescription
        if self.isConnected and not startup:
            self.worker.subscribeToStreamingData(self.streamingDataReqId, contractDescription)
        if not startup and contractDescription.contract.symbol not in list(self.positions.keys()):
            entry = {}
            for presetName in list(self.preset_data.keys()):
                entry[presetName] = 0
            self.positions[contractDescription.contract.symbol] = {'positions': entry}
            self.savePositions()
        # self.refreshWatchlistLayout()
        item = WatchlistItem(self.streamingDataReqId, contractDescription.contract, self.get_total_positions(self.streamingDataReqId))
        item.remove.connect(self.removeFromWatchlist, Qt.DirectConnection)
        item.requestMarketState.connect(self.getMktState, Qt.DirectConnection)
        item.update_settings.connect(self.update_portfolio_settings, Qt.DirectConnection)
        self.sendMktStateToWatchlist.connect(item.mktStateUpdate, Qt.DirectConnection)
        self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
        self.watchlistItems[self.streamingDataReqId] = item

        if not startup:
            self.saveWatchlist()

            portfolio_item = {}
            for algo, _ in self.preset_data.items():
                portfolio_item[algo] = self.settings['strategy']['trade_all']
            self.portfolio[contractDescription.contract.symbol.upper()] = {}
            self.portfolio[contractDescription.contract.symbol.upper()]['permissions'] = portfolio_item
            self.portfolio[contractDescription.contract.symbol.upper()]['pos_size'] = int(self.settings['strategy']['pos_size'])
            self.savePortfolio()


    def removeFromWatchlist(self, reqId):

        if self.isConnected: self.close_all_positions(reqId)

        if reqId in self.watchlist:
            if self.isConnected: self.worker.cancelStreamingData(reqId)
            symbol = self.watchlist[reqId].contract.symbol
            self.portfolio.pop(self.watchlist[reqId].contract.symbol.upper(), None)
            self.watchlist.pop(reqId, None)
            self.positions.pop(symbol, None)
            self.saveWatchlist()
            self.savePortfolio()
            self.savePositions()

        if reqId in self.watchlistItems:
            self.watchlistItems[reqId].deleteLater()
            self.watchlistItems.pop(reqId, None)

        if len(self.watchlist) == 0:
            self.noItemsInWatchlist()


    def tick(self, reqId, tickType, price):
        if reqId in self.watchlistItems:
            self.watchlistItems[reqId]._update(tickType, price)

    def mapTimeToMktState(self, t):
        if t.weekday() in [5, 6]: return 0
        tint = t.hour * 10000 + t.minute * 100 + t.second
        if tint >= self.sessionToday['premarketOpen'] and tint < self.sessionToday['premarketClose']: return 1
        if tint >= self.sessionToday['marketOpen'] and tint < self.sessionToday['marketClose']: return 2
        if tint >= self.sessionToday['aftermarketOpen'] and tint < self.sessionToday['aftermarketClose']: return 3
        return 0


    def displayMktState(self, state:int):
        if state == 0:
            self.mktStatusLabel.setText('Market is closed')
            self.mktStatusLabel.setStyleSheet("QLabel { color: #aaaaaa; }")
        elif state == 1:
            self.mktStatusLabel.setText('Pre-market trading')
            self.mktStatusLabel.setStyleSheet("QLabel { color: #f39c12; }")
        elif state == 2:
            self.mktStatusLabel.setText('Market is open')
            self.mktStatusLabel.setStyleSheet("QLabel { color: #00E676;}")
        elif state == 3:
            self.mktStatusLabel.setText('After hours trading')
            self.mktStatusLabel.setStyleSheet("QLabel { color: #f39c12; }")

    def updateTodaysSessionTimes(self, details):
        regT = details['regularSessionClose']
        extT = details['extendedSessionClose']
        regCloseToday = regT.hour * 10000 + regT.minute * 100
        extCloseToday = extT.hour * 10000 + extT.minute * 100
        self.sessionToday['marketClose'] = regCloseToday
        self.sessionToday['aftermarketOpen'] = regCloseToday
        self.sessionToday['aftermarketClose'] = extCloseToday


    def getSessionTimesToday(self, t):
        dintToday = int(str(t.year) + str(t.month) + str(t.day))
        self.isHoliday, self.closedAllDay = False, False
        for name, details in self.holidays.items():
            hdt = details['date']
            dintHoliday = int(str(hdt.year) + str(hdt.month) + str(hdt.day))
            if dintHoliday == dintToday:
                self.isHoliday = True
                self.holidayName = name
                if not details['closedAllDay']:
                    self.updateTodaysSessionTimes(details)
                else: self.closedAllDay = True
                break

    def refreshHolidayLabel(self):
        if self.isHoliday:
            holiday = self.holidays[self.holidayName]
            if self.closedAllDay:
                label = 'Markets are closed in observation of {}'.format(self.holidayName)
            else:
                regClose = holiday['regularSessionClose'].strftime("%H:%M %p")
                regClose = regClose[1:] if regClose[0] == '0' else regClose
                extClose = holiday['extendedSessionClose'].strftime("%H:%M %p")
                extClose = extClose[1:] if extClose[0] == '0' else extClose
                label = 'Markets close early at {}, after market trading until {} ({})'.format(
                    regClose, extClose, self.holidayName
                )
            self.holidayLabel.setText(label)
            self.holidayLabel.setMaximumHeight(30)
        else:
            self.holidayLabel.setText('')
            self.holidayLabel.setMaximumHeight(0)

    def check_gpu_availability(self):
        if not cuda.is_available():
            self.closeApp.emit()
            msgBox = InfoMessageBox(
                'No GPU detected',
                'No GPU detected.\n\nApplication was terminated.',
                error=True
                )


    def showTime(self):
        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        if t.day != self.lastKnownDay:
            self.check_gpu_availability()
            self.getSessionTimesToday(t)
            self.lastKnownDay = t.day
            self.refreshHolidayLabel()
            self.get_timeframe_marks(default=False)
            if not self.isConnected: self.enable_connect_button()
            if self.settings['strategy']['flatten_eod']:
                minutes_to_close = self.settings['strategy']['flatten_eod_seconds'] // 60
                seconds_to_close = self.settings['strategy']['flatten_eod_seconds'] % 60
                if seconds_to_close != 0:
                    minutes_to_close += 1
                    seconds_to_close = 60 - seconds_to_close
                self.maxT = self.sessionToday['marketClose'] - minutes_to_close * 100 + seconds_to_close
            self.positionsCLosedToday = False
        if self.timeInfoReady: self.clockTime.setText(t.strftime("EDT %I:%M:%S %p"))
        self.mktState = self.mapTimeToMktState(t)
        if self.mktState != self.prevMktState:
            self.prevMktState = self.mktState
            self.displayMktState(self.mktState)
            self.sendMktStateToWatchlist.emit(self.mktState)
        if not self.historicalDataReady and self.isConnected and (datetime.now() - self.lastHistoricalDataRequest).seconds > self.MAX_HISTORICAL_DATA_TIMEOUT_SECONDS:
            self.historicalDataReady = True
            self.tell_downloader_to_stop.emit()
        tint = t.hour * 10000 + t.minute * 100
        if self.initialRun: self.last_tint = tint
        if self.timeframe_marks_ready and (tint in self.timeframe_marks_int or self.debug) and tint != self.last_tint and not self.initialRun:
            self.last_tint = tint
            self.sample_prices(t)
        if tint > self.maxT and t.weekday() not in [5, 6] and not self.positionsCLosedToday and self.settings['strategy']['flatten_eod']:
            for reqId in list(self.watchlistItems.keys()):
                if self.isConnected: self.close_all_positions(reqId, eod=True)
            self.positionsCLosedToday = True


    def sample_prices(self, t):
        self.dataUpdated = np.zeros(self.nStocks, dtype='bool')
        self.updatedPrices = np.zeros(self.nStocks, dtype='float64')
        n = 0
        for reqId, item in self.watchlistItems.items():
            if item.isTrading and item._last.text() != '-':
                try:
                    p = float(item._last.text())
                    self.dataUpdated[n] = True
                    self.updatedPrices[n] = p
                except: self.log('error', 'Parsing error occured')
            n += 1

        if sum(self.dataUpdated) > 0: self.realtime_calc(t)


    def stop_dash_thread(self):
        self.dashThread.quit()


    def open_presets_window(self):
        self.presets.show()


    def open_chart_window(self):


        # self.chartWindow.quitDash.connect(self.dashWorker.stop)
        # self.chartWindow.quitDash.connect(self.dashWorker.deleteLater)
        # self.chartWindow.quitDash.connect(self.dashThread.deleteLater)

        self.chartWindow.show_graph()

    def open_explorer_window(self):
        if self.explorerReady:
            if not self.explorerInitiated:
                self.explorer = Explorer(deepcopy(self.symbols), deepcopy(self.preset_data))
                self.explorer.requestData.connect(self.transmitDataToExplorer, Qt.DirectConnection)
                self.data_to_explorer.connect(self.explorer.data_received, Qt.DirectConnection)
                self.explorerInitiated = True
            self.explorer.show()
        else: msgBox = InfoMessageBox('Info', 'Data Explorer is not yet ready\n\nPlease try again later\n')


    def enable_connect_button(self):
        self.connectButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
        self.connectButton.setEnabled(True)

    def disable_connect_button(self):
        self.connectButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.connectButton.setEnabled(False)

    def enable_start_button(self):
        self.startButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
        self.startButton.setEnabled(True)

    def disable_start_button(self):
        self.startButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.startButton.setEnabled(False)

    def enable_stop_button(self):
        self.stopButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
        self.stopButton.setEnabled(True)

    def disable_stop_button(self):
        self.stopButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.stopButton.setEnabled(False)

    def enable_search_button(self):
        self.searchButton.setEnabled(True)
        self.searchButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.searchButton.setText('Search')

    def disable_search_button(self):
        self.searchButton.setEnabled(False)
        self.searchButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.searchButton.setText('Please wait...')

    def start(self):
        self.disable_start_button()
        self.executing = []
        for reqId, item in self.watchlistItems.items():
            if item._history.text().upper() == 'READY':
                item._execution.setText('On')
                item._execution.setStyleSheet("QLabel{color:#00E676;}")
                self.executing.append(True)
            else: self.executing.append(False)

        self.isExecuting = True
        self.enable_stop_button()


    def stop(self):
        self.disable_stop_button()
        self.executing = []
        for reqId, item in self.watchlistItems.items():
            item._execution.setText('Off')
            item._execution.setStyleSheet("QLabel{color:#ff5252;}")
            self.executing.append(False)
        self.isExecuting = False
        self.enable_start_button()


    def clientID(self):
        return random.randint(1, pow(2, 16) - 1)

    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.horizontalHeader().setVisible(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setHorizontalHeaderLabels( ['Symbol', 'Algorithm', 'Qty'] )

        self.tableWidget.move(0,0)

        # table selection change
        self.tableWidget.doubleClicked.connect(self.on_click)

    @pyqtSlot()
    def on_click(self):
        print("\n")
        for currentQTableWidgetItem in self.tableWidget.selectedItems():
            print(currentQTableWidgetItem.row(), currentQTableWidgetItem.column(), currentQTableWidgetItem.text())

    @pyqtSlot()
    def open_symbol_lookup_window(self):
        self.w = SymbolLookupWindow()
        self.w.show()

    @pyqtSlot()
    def search_button_clicked(self):
        text = self.symbolSerachText.text()
        if text == '':
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            # msg.setText("Error")
            msg.setInformativeText('Search field cannot be empty')
            msg.setWindowTitle("Search Hint")
            msg.exec_()

        elif not self.isConnected:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            # msg.setText("Error")
            msg.setInformativeText('Please establish connection')
            msg.setWindowTitle("Search Hint")
            msg.exec_()

        elif time.time() - self.searchLastRequested < 1.:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            # msg.setText("Error")
            msg.setInformativeText('Please wait at least 1 second before consecutive requests')
            msg.setWindowTitle("Search Hint")
            msg.exec_()

        else:
            self.disable_search_button()
            self.searchQuery = text.upper()
            self.searchLastRequested = time.time()
            self.symbolSerachText.setText('')
            self.status_message.emit('Searching for {}...'.format(self.searchQuery))
            self.symInfoRequested.emit(text, 0)

    def symbolInfoReceived(self, exitcode, contractDescriptions):
        if exitcode == 0:
            self.enable_search_button()
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setInformativeText('Search request was unsuccessful')
            msg.setWindowTitle("Search Hint")
            msg.exec_()
        elif exitcode == 1:
            self.searchWindow = SearchWindow(self.searchQuery, contractDescriptions, 'watchlist')
            self.searchWindow.sendContractToWatchlist.connect(self.addToWatchlist, Qt.DirectConnection)
            self.searchWindow.show()
            self.status_message.emit('')
            self.enable_search_button()






        """
        self.searchWindow.defailtMsg.deleteLater()

        for contractDescription in contractDescriptions:
            derivSecTypes = ""
            for derivSecType in contractDescription.derivativeSecTypes:
                derivSecTypes += " "
                derivSecTypes += derivSecType

            self.searchWindow.vlayout = QVBoxLayout()

            self.searchWindow.symInfo = QLabel("QuantTrader")
            self.searchWindow.symInfo.setAlignment(Qt.AlignCenter)
            # self.title.setStyleSheet("QLabel {font-weight: bold; color: black; font-size: 18px;}")
            self.searchWindow.vlayout.addWidget(self.searchWindow.symInfo)

            self.searchWindow.layout.addLayout(self.searchWindow.vlayout)
        """

        # print("Contract: conId:%s, symbol:%s, secType:%s primExchange:%s, currency:%s, derivativeSecTypes:%s, description:%s, issuerId:%s" % (
        #         contractDescription.contract.conId,
        #         contractDescription.contract.symbol,
        #         contractDescription.contract.secType,
        #         contractDescription.contract.primaryExchange,
        #         contractDescription.contract.currency, derivSecTypes,
        #         contractDescription.contract.description,
        #         contractDescription.contract.issuerId))



        # self.title = QLabel("QuantTrader")
        # self.title.setAlignment(Qt.AlignCenter)
        # self.title.setStyleSheet("QLabel {font-weight: bold; color: black; font-size: 18px;}")
        # layout.addWidget(self.title)



    def symbolSamples(self, reqId: int,
                           contractDescriptions):
            super().symbolSamples(reqId, contractDescriptions)
            print("Symbol Samples. Request Id: ", reqId)

            for contractDescription in contractDescriptions:
                 derivSecTypes = ""
                 for derivSecType in contractDescription.derivativeSecTypes:
                     derivSecTypes += " "
                     derivSecTypes += derivSecType
            print("Contract: conId:%s, symbol:%s, secType:%s primExchange:%s, currency:%s, derivativeSecTypes:%s, description:%s, issuerId:%s" % (
                    contractDescription.contract.conId,
                    contractDescription.contract.symbol,
                    contractDescription.contract.secType,
                    contractDescription.contract.primaryExchange,
                    contractDescription.contract.currency, derivSecTypes,
                    contractDescription.contract.description,
                    contractDescription.contract.issuerId))



    def readWorkerSignal(self):
        return


    def requestStreamingDataForAllItemsInWatchlist(self):
        for streamingDataReqId, contractDescription in self.watchlist.items():
            if self.isConnected: self.worker.subscribeToStreamingData(streamingDataReqId, contractDescription)
            self.status_message.emit('[{}] subscribing to streaming data...'.format(contractDescription.contract.symbol))
            time.sleep(1/25.)
        self.status_message.emit('')

    def downloader_requested_subscription(self, reqId, contractDescription):
        if self.isConnected: self.worker.subscribeToStreamingData(reqId, contractDescription)

    def downloader_requested_historical_data(self, contractDescription, endDateTime):
        return

    def worker_connected(self, code):
        if code == 1:
            self.disable_connect_button()
            self.status_message.emit('')
            self.connectionLabel.setText("Status:    connected")
            self.isConnected = True
            self.connectionEstablished.emit(1)
            self.downloader.initiate()
            self.lastHistoricalDataRequest = datetime.now()
            self.downloader.first_historical_data()
        elif code == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Failed to establish connection')
            msg.setWindowTitle("Error")
            msg.exec_()

    def error_received(self, code, message):
        additional_message = ''
        if code == 502:
            self.disable_connect_button()
            self.status_message.emit('Critical error. Restart the application.')
            additional_message = '\n\nTHIS ERROR IS CRITICAL. YOU MUST RESTART THE PROGRAM NOW!'
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setInformativeText(message+additional_message)
        msg.setWindowTitle("Error. Code "+str(code))
        msg.exec_()

    def worker_log_msg(self, msg):
        self.log('info', msg)


    def status_msg(self, msg):
        self.status_message.emit(msg)

    def watchlist_data_status(self, id, status):
        item = self.watchlistItems[id]
        if status == 'failed':
            item._history.setText('Failed')
            item._history.setStyleSheet("QLabel{color:#ff5252; font-weight: normal;}")
        elif status == 'loading':
            item._history.setText('Loading...')
            item._history.setStyleSheet("QLabel{color:#aaaaaa; font-weight: normal;}")
        elif status == 'ready':
            item._history.setText('Ready')
            item._history.setStyleSheet("QLabel{color:#00E676; font-weight: normal;}")

    def update_hist_request_time(self):
        self.lastHistoricalDataRequest = datetime.now()

    def get_timeframe_marks(self, default=False):
        self.timeframe_marks = []
        if default:
            self.sessionToday = {
                'premarketOpen' : 40000,
                'premarketClose' : 93000,
                'marketOpen' : 93000,
                'marketClose' : 160000,
                'aftermarketOpen' : 160000,
                'aftermarketClose' : 200000
            }
        premarket_open_hour  = int(self.sessionToday['premarketOpen']/10000)
        market_open_hour     = int(self.sessionToday['marketOpen']/10000)
        premarket_open_minute  = int( (self.sessionToday['premarketOpen'] - premarket_open_hour * 10000) / 100 )
        market_open_minute  = int( (self.sessionToday['marketOpen'] - market_open_hour * 10000) / 100 )
        virtual_session_start = {
            "hour": premarket_open_hour if not self.settings['strategy']['onlyRTH_history'] else market_open_hour,
            "minute": premarket_open_minute if not self.settings['strategy']['onlyRTH_history'] else market_open_minute
        }
        virtual_session_start["minute"] += self.settings['strategy']['timeframe']
        added_hours = 0
        while virtual_session_start["minute"] >= 60:
            virtual_session_start["minute"] -= 60
            added_hours += 1
        virtual_session_start["hour"] += added_hours

        current_mark = virtual_session_start["hour"] * 10000 + virtual_session_start["minute"] * 100
        rounds_remaining = 3 if not self.settings['strategy']['onlyRTH_history'] else 1
        session_round = 1 if self.settings['strategy']['onlyRTH_history'] else 0
        el = {"hour": virtual_session_start["hour"], "minute": virtual_session_start["minute"]}
        timeframe = self.settings['strategy']['timeframe']
        while rounds_remaining > 0:
            close_time_reference = "premarketClose"
            if session_round == 1:
                close_time_reference = "marketClose"
            if session_round == 2:
                close_time_reference = "aftermarketClose"

            this_session_end = self.sessionToday[close_time_reference]

            self.timeframe_marks.append(deepcopy(virtual_session_start))
            el["hour"] = virtual_session_start["hour"]
            el["minute"] = virtual_session_start["minute"]
            while current_mark < this_session_end:
                el["minute"] += timeframe
                while el["minute"] >= 60:
                    el["minute"] -= 60
                    el["hour"] += 1

                current_mark = el["hour"] * 10000 + el["minute"] * 100
                if current_mark >= this_session_end:
                    current_mark = this_session_end
                    el["hour"] = int(this_session_end / 10000)
                    el["minute"] = int( (this_session_end - el["hour"] * 10000) / 100 )
                    virtual_session_start["hour"] = el["hour"]
                    virtual_session_start["minute"] = el["minute"]
                    virtual_session_start["minute"] += timeframe
                    while virtual_session_start["minute"] >= 60:
                        virtual_session_start["minute"] -= 60
                        virtual_session_start["hour"] += 1

                self.timeframe_marks.append(deepcopy(el))

            rounds_remaining -= 1
            session_round += 1

        if default:
            t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
            self.getSessionTimesToday(t)


    def get_tf_marks_int(self):
        m = []
        for mark in self.timeframe_marks:
            m.append(mark["hour"]*10000 + mark["minute"]*100)
        return m

    def get_symbols(self):
        self.symbols = []
        for reqId, contractDescription in self.watchlist.items():
            self.symbols.append(self.watchlist[reqId].contract.symbol)

    def data_transform(self, success, timestamps, closes):
        self.get_timeframe_marks(default=True)
        self.timeframe_marks_int = self.get_tf_marks_int()

        self.dt, self.c, self.returns = [], [], []
        for n in range(len(timestamps)):
            t, c = timestamps[n], closes[n]
            _t, _c = [], []
            for i in range(len(t)):
                dt = parser.parse(t[i][:17])
                dtint = dt.hour * 10000 + dt.minute * 100
                if dtint in self.timeframe_marks_int:
                    _t.append(dt)
                    _c.append(c[i])

            _t.reverse()
            _c.reverse()

            _r = []
            for i in range(1, len(_c)):
                _r.append( (_c[i] - _c[i-1]) / _c[i-1] )

            if len(_t) > 0:
                del _t[0]
                del _c[0]

            self.dt.append(_t)
            self.c.append(_c)
            self.returns.append(_r)

        self.get_timeframe_marks(default=False)
        return

        self.symbols = []
        for reqId, contractDescription in self.watchlist.items():
            self.symbols.append(self.watchlist[reqId].contract.symbol)
        self.timestamps, self.closes = [], []
        for n in range(len(timestamps)):
            dt, c = timestamps[n], closes[n]
            ix, mix, tix = len(dt) - 1, 0, 0
            t = parser.parse(dt[ix][:17])
            tint = t.hour * 10000 + t.minute * 100
            m = self.timeframe_marks[mix]
            mint = m['hour'] * 10000 + m['minute'] * 100
            while mint < tint and mix < len(self.timeframe_marks):
                mix += 1
                m = self.timeframe_marks[mix]
                mint = m['hour'] * 10000 + m['minute'] * 100
            while tint < mint and ix > 0:
                ix -= 1
                t = parser.parse(dt[ix][:17])
                tint = t.hour * 10000 + t.minute * 100

            self.timestamps[n][tix].insert(0, t)
            self.closes[n][tix].insert(0, c[tix])
            dayPrev = t.day

        self.get_timeframe_marks(default=False)

    def is_regular_session(self):
        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        tint = t.hour * 10000 + t.minute * 100
        if tint > self.sessionToday['marketOpen'] and tint < self.sessionToday['marketClose'] and t.weekday() not in [5, 6]:
            return True
        else: return False


    def get_shortest_history(self):
        return min([len(r) for r in self.returns])

    def truncate_price_history(self, threshold, max_history = 10**10):
        _threshold = min(threshold, max_history)
        for i in range(len(self.returns)):
            if len(self.returns[i]) > _threshold:
                del self.returns[i][:(len(self.returns[i])-_threshold)]
                del self.dt[i][:(len(self.dt[i])-_threshold)]
                del self.c[i][:(len(self.c[i])-_threshold)]


    def get_algo_inputs(self):
        self.AlgoInputs = []
        n = 0
        for _, algo_settings in self.preset_data.items():
            settings = np.array([
                algo_settings['2min'],
                algo_settings['2max'],
                algo_settings['3min'],
                algo_settings['2max'],
                algo_settings['12min'],
                algo_settings['12max'],
                algo_settings['avgmin'],
                algo_settings['avgmax']
            ], dtype='float64')
            self.AlgoInputs.append(settings)
            n += 1
        self.AlgoInputs = np.array(self.AlgoInputs, dtype='float64')


    def initialize_data_structures(self):
        self.STDs = np.zeros(shape=(self.nStocks, len(cudafns.SD_Periods), self.nDatapoints), dtype='float64')
        self.STDs = self.STDs.tolist()
        self.Averages = np.zeros(shape=(self.nStocks, len(cudafns.AVG_Periods) + 1, self.nDatapoints), dtype='float64')
        self.Averages = self.Averages.tolist()
        self.Signals = np.zeros(shape=(self.nStocks, self.nAlgos, self.nDatapoints), dtype='int8')
        self.get_algo_inputs()

    def init_report(self):
        self.reportDT = []
        self.reportCloses = []
        self.reportSignals = []
        for i in range(self.nStocks):
            self.reportDT.append([])
            self.reportCloses.append([])
            self.reportSignals.append([])

        if self.nDatapoints > 0 and self.nAlgos > 0:

            for s in range(self.nStocks):
                for i in range(self.nDatapoints):
                    dt = self.dt[s][i].strftime("%Y-%b-%d %H:%M:%S")
                    self.reportDT[s].append(dt)
                    self.reportCloses[s].append(self.c[s][i])
                    signals = []
                    for a in range(self.nAlgos):
                        signal, value = '', self.Signals[s][a][i]
                        if value == 1: signal = 'buy'
                        if value == -1: signal = 'sell'
                        signals.append(signal)
                    self.reportSignals[s].append(signals)

    def commission_update(self, orderID, commission):
        if orderID in self.pending_orders and commission < 10**6:
            orderData = self.pending_orders[orderID]
            orderData['commissions'] = commission


    def order_status_update(self, orderID, remaining, VWAP):

        if remaining == 0 and orderID in list(self.pending_orders.keys()):
            orderData = self.pending_orders[orderID]
            self.watchlistItems[orderData['reqId']].positionChanged(orderData['pos_change'])
            i = 0
            for key in list(self.positions[orderData['symbol']]['positions'].keys()):
                self.positions[orderData['symbol']]['positions'][key] += orderData['adjustments'][i]
                i += 1
            self.savePositions()
            self.update_position_table()


            t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
            t = '{} EDT'.format(t.strftime("%Y-%b-%d %H:%M:%S.%f"))
            for algoIX in range(len(self.algoNames)):
                pos_change = orderData['adjustments'][algoIX]
                if pos_change != 0:
                    tradeInfo = []
                    tradeInfo.append(t)
                    tradeInfo.append(orderData['symbol'])
                    tradeInfo.append(self.algoNames[algoIX])
                    tradeInfo.append('BUY' if pos_change > 0 else 'SELL')
                    tradeInfo.append(abs( pos_change ))
                    tradeInfo.append(VWAP)
                    # tradeInfo.append( round(orderData['commissions'] * 1. * abs(pos_change) / abs(orderData['pos_change']) , 7) )
                    self.trades.append(tradeInfo)

                    rowPosition = self.tradesTable.rowCount()
                    self.tradesTable.insertRow(rowPosition)
                    pos = 0
                    for _item in tradeInfo:
                        self.tradesTable.setItem(rowPosition, pos, QTableWidgetItem( str(_item) ))
                        pos += 1

            self.pending_orders.pop(orderID, None)

        return

    def prepare_order(self, orderId, reqId, qty):
        order = Order()
        order.action = 'SELL' if qty < 0 else 'BUY'
        order.totalQuantity = abs(qty)
        order.orderType, order.transmit, order.eTradeOnly, order.firmQuoteOnly = 'MKT', True, False, False
        contract = self.watchlist[reqId].contract
        if self.debug:
            contract = Contract()
            contract.symbol, contract.secType, contract.exchange, contract.currency = 'AAPL', 'STK', 'SMART', 'USD'
        self.transmit_order.emit(orderId, contract, order)


    def close_all_positions(self, reqId, eod=False):
        item = self.watchlistItems[reqId]
        n = list(self.watchlistItems.keys()).index(reqId)

        self.get_symbols()

        totalPos = 0
        adjustments = []
        for key in self.positions[self.symbols[n]]['positions'].keys():
            totalPos += self.positions[self.symbols[n]]['positions'][key]
            adjustments.append(-1 * self.positions[self.symbols[n]]['positions'][key])

        if totalPos != 0:
            pendingOrderData = {}
            pendingOrderData['symbol'] = self.symbols[n]
            pendingOrderData['adjustments'] = deepcopy(adjustments)
            pendingOrderData['pos_change'] = -1 * totalPos
            pendingOrderData['reqId'] = reqId
            pendingOrderData['commissions'] = 0
            self.pending_orders[self.orderID] = pendingOrderData
            self.prepare_order(self.orderID, reqId, -1 * totalPos)
            self.orderID += 1
            time.sleep(1./self.REQUEST_LIMIT_PER_SECOND)

        if not eod:
            self.positions.pop(self.symbols[n], None)
            self.portfolio.pop(self.symbols[n], None)
            self.nStocks -= 1
            del self.symbols[n]
        else:
            for key in self.positions[self.symbols[n]]['positions'].keys():
                self.positions[self.symbols[n]]['positions'][key] = 0
        self.savePositions()


    def execute_pending_positions(self):
        reqIds = list(self.watchlistItems.keys())
        for n in range(len(self.dataUpdated)):
            isSymbolExecuting = str(self.watchlistItems[reqIds[n]]._execution.text()).upper() == 'ON'
            isSessionAcive = self.last_tint < self.maxT
            isAuctionOpen = str(self.watchlistItems[reqIds[n]]._auction.text()).upper() == 'OPEN'
            if self.dataUpdated[n] and isSymbolExecuting and self.mktState != 0 and isSessionAcive and isAuctionOpen:
                if self.pending_positions_total[n] == 0 and min(self.pending_positions_per_algo[n]) != max(self.pending_positions_per_algo[n]):
                    for key in self.positions[self.symbols[n]]['positions'].keys():
                        self.positions[self.symbols[n]]['positions'][key] = 0
                    self.savePositions()
                elif self.pending_positions_total[n] != 0:
                    pendingOrderData = {}
                    pendingOrderData['symbol'] = self.symbols[n]
                    pendingOrderData['adjustments'] = deepcopy(self.pending_positions_per_algo[n])
                    pendingOrderData['pos_change'] = self.pending_positions_total[n]
                    pendingOrderData['reqId'] = reqIds[n]
                    pendingOrderData['commissions'] = 0
                    self.pending_orders[self.orderID] = pendingOrderData
                    self.prepare_order(self.orderID, reqIds[n], self.pending_positions_total[n])
                    self.orderID += 1
            time.sleep(1./self.REQUEST_LIMIT_PER_SECOND)


    def get_pending_positions(self):
        self.pending_positions_per_algo = []
        self.pending_positions_total = []
        self.algoNames = list(self.preset_data.keys())
        for n in range(len(self.dataUpdated)):
            self.pending_positions_per_algo.append( [ 0 for _ in range(self.nAlgos) ] )
            if self.dataUpdated[n]:
                pos_size =  int(math.floor( 1. * int(self.portfolio[ self.symbols[n] ]['pos_size']) / self.updatedPrices[n] ))
                for algoIX in range(self.nAlgos):
                    algoSignal = self.Signals[n][algoIX][-1]
                    algoPosition = self.positions[self.symbols[n]]['positions'][self.algoNames[algoIX]]
                    self.pending_positions_per_algo[-1][algoIX] = pos_size if algoSignal > 0 else -1 * algoPosition
            self.pending_positions_total.append( sum(self.pending_positions_per_algo[-1]) )

        self.execute_pending_positions()


    def realtime_calc(self, t):

        dt = datetime(t.year, t.month, t.day, t.hour, t.minute, 0)
        for n in range(len(self.dataUpdated)):
            if self.dataUpdated[n]:
                self.dt[n].append(dt)
                del self.dt[n][0]

                self.c[n].append(self.updatedPrices[n])
                del self.c[n][0]

                r = .0
                if len(self.c[n]) > 2: r = (self.updatedPrices[n] - self.c[n][-2]) / self.c[n][-2]
                self.returns[n].append(r)
                del self.returns[n][0]

                for m in range(len(cudafns.SD_Periods)):
                    self.STDs[n][m].append(.0)
                    del self.STDs[n][m][0]

                for m in range(len(cudafns.AVG_Periods) + 1):
                    self.Averages[n][m].append(.0)
                    del self.Averages[n][m][0]

                for m in range(self.nAlgos):
                    self.Signals[n][m].append(0)
                    del self.Signals[n][m][0]



        self.STDs = np.array(self.STDs, dtype='float64')
        self.Averages = np.array(self.Averages, dtype='float64')
        self.Signals = np.array(self.Signals, dtype='int8')

        self.BLOCKS_PER_GRID = math.floor( (self.nStocks*len(cudafns.SD_Periods)) / self.THREADS_PER_BLOCK + 1)

        t_started = time.time()

        stream = cuda.stream()
        cuda_returns = cuda.to_device( np.array(self.returns, dtype='float64'), stream=stream)
        cuda_STDs = cuda.to_device(self.STDs, stream=stream)
        cuda_SD_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)

        cudafns.compute_standard_deviations_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
            cuda_returns, cuda_STDs, cuda_SD_Periods, (self.nStocks*len(cudafns.SD_Periods)), self.nStocks)

        cuda_STDs.copy_to_host(self.STDs, stream=stream)
        stream.synchronize()

        self.BLOCKS_PER_GRID = math.floor( (self.nStocks*len(cudafns.AVG_Periods)) / self.THREADS_PER_BLOCK + 1)

        stream = cuda.stream()
        cuda_STDs = cuda.to_device(self.STDs, stream=stream)
        cuda_Averages = cuda.to_device(self.Averages, stream=stream)
        cuda_SD_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)
        cuda_AVG_Periods = cuda.to_device(np.array(cudafns.AVG_Periods, dtype='int'), stream=stream)

        cudafns.compute_averages_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
            cuda_STDs, cuda_Averages, cuda_SD_Periods, cuda_AVG_Periods, (self.nStocks*len(cudafns.AVG_Periods)), self.nStocks)

        cuda_Averages.copy_to_host(self.Averages, stream=stream)
        stream.synchronize()

        n = self.Averages.shape[2] - 1
        for s in range(self.nStocks):
            if self.dataUpdated[s]:
                avg = .0
                for i in range(len(cudafns.AVG_Periods)):
                    avg += self.Averages[s][i][n]
                avg /= len(cudafns.AVG_Periods)
                self.Averages[s][i+1][n] = avg

        self.BLOCKS_PER_GRID = math.floor( (self.nStocks*self.nAlgos) / self.THREADS_PER_BLOCK + 1)

        stream = cuda.stream()
        cuda_Averages = cuda.to_device(self.Averages, stream=stream)
        cuda_Signals = cuda.to_device(self.Signals, stream=stream)
        cuda_InputMatrix = cuda.to_device(self.AlgoInputs, stream=stream)

        cudafns.compute_signals_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
            cuda_Averages, cuda_Signals, cuda_InputMatrix,
            self.FIRST_VALID_INDEX, (self.nStocks*self.nAlgos), self.nStocks)

        cuda_Signals.copy_to_host(self.Signals, stream=stream)
        stream.synchronize()

        t_finished = time.time()

        self.STDs = self.STDs.tolist()
        self.Averages = self.Averages.tolist()
        self.Signals = self.Signals.tolist()

        _dt = dt.strftime("%Y-%b-%d %H:%M:%S")
        for n in range(self.nStocks):
            if self.dataUpdated[n]:
                self.reportDT[n].append(_dt)
                self.reportCloses[n].append(self.c[n][-1])
                signals = []
                for a in range(self.nAlgos):
                    signal, value = '', self.Signals[n][a][-1]
                    if value == 1: signal = 'buy'
                    if value == -1: signal = 'sell'
                    signals.append(signal)
                self.reportSignals[n].append(signals)

        _t = t_finished - t_started
        self.update_compute_time.emit(dt.strftime("%b-%d %H:%M:%S"), int(round(_t*1000., 0)))

        self.get_pending_positions()

        return

    def transmitDataToExplorer(self):
        self.data_to_explorer.emit(self.reportDT, self.reportCloses, self.reportSignals)


    def initial_algo_run(self):
        self.truncate_price_history(self.get_shortest_history())

        self.nStocks = len(self.returns)
        self.nDatapoints = 0
        if self.nStocks > 0:
            self.nDatapoints = len(self.returns[0])
        self.nAlgos = 0
        if len(self.portfolio) > 0:
            self.nAlgos = len(self.preset_data)

        if self.nDatapoints > 0 and self.nAlgos > 0:
            self.update_kernel_status.emit('compiling')
            self.initialize_data_structures()
            STDs = np.array(self.STDs, dtype='float64')
            self.BLOCKS_PER_GRID = math.floor(self.nDatapoints / self.THREADS_PER_BLOCK + 1)
            cuda.select_device(self.CUDA_DEVICE_ID)
            context = cuda.current_context(0)

            stream = cuda.stream()
            cuda_returns = cuda.to_device( np.array(self.returns, dtype='float64'), stream=stream)
            cuda_STDs = cuda.to_device(STDs, stream=stream)
            cuda_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)

            cudafns.compute_standard_deviations_init[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](cuda_returns, cuda_STDs, cuda_Periods)

            cuda_STDs.copy_to_host(STDs, stream=stream)
            stream.synchronize()

            Averages = np.array(self.Averages, dtype='float64')
            stream = cuda.stream()
            cuda_STDs = cuda.to_device(STDs, stream=stream)
            cuda_Averages = cuda.to_device(Averages, stream=stream)
            cuda_SD_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)
            cuda_AVG_Periods = cuda.to_device(np.array(cudafns.AVG_Periods, dtype='int'), stream=stream)

            cudafns.compute_averages_init[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](cuda_STDs, cuda_Averages, cuda_SD_Periods, cuda_AVG_Periods)

            cuda_Averages.copy_to_host(Averages, stream=stream)
            stream.synchronize()

            MIN_DATAPOINTS = cudafns.SD_Periods[-1] + cudafns.AVG_Periods[-1] - 1
            self.FIRST_VALID_INDEX = MIN_DATAPOINTS - 1
            for n in range(self.nDatapoints):
                if n < self.FIRST_VALID_INDEX: continue
                for k in range(self.nStocks):
                    avg = .0
                    for i in range(len(cudafns.AVG_Periods)): avg += Averages[k][i][n]
                    avg /= len(cudafns.AVG_Periods)
                    Averages[k][len(cudafns.AVG_Periods)][n] = avg

            self.BLOCKS_PER_GRID = math.floor( (self.nStocks*self.nAlgos) / self.THREADS_PER_BLOCK + 1)

            stream = cuda.stream()
            cuda_Averages = cuda.to_device(Averages, stream=stream)
            cuda_Signals = cuda.to_device(self.Signals, stream=stream)
            cuda_InputMatrix = cuda.to_device(self.AlgoInputs, stream=stream)

            cudafns.compute_signals_init[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
                cuda_Averages, cuda_Signals, cuda_InputMatrix,
                self.FIRST_VALID_INDEX, (self.nStocks*self.nAlgos), self.nStocks)

            cuda_Signals.copy_to_host(self.Signals, stream=stream)
            stream.synchronize()

            self.BLOCKS_PER_GRID = math.floor( (self.nStocks*len(cudafns.SD_Periods)) / self.THREADS_PER_BLOCK + 1)

            stream = cuda.stream()
            cuda_returns = cuda.to_device( np.array(self.returns, dtype='float64'), stream=stream)
            cuda_STDs = cuda.to_device(STDs, stream=stream)
            cuda_SD_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)

            cudafns.compute_standard_deviations_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
                cuda_returns, cuda_STDs, cuda_SD_Periods, (self.nStocks*len(cudafns.SD_Periods)), self.nStocks)

            stream.synchronize()

            self.BLOCKS_PER_GRID = math.floor( (self.nStocks*len(cudafns.AVG_Periods)) / self.THREADS_PER_BLOCK + 1)

            stream = cuda.stream()
            cuda_STDs = cuda.to_device(STDs, stream=stream)
            cuda_Averages = cuda.to_device(Averages, stream=stream)
            cuda_SD_Periods = cuda.to_device(np.array(cudafns.SD_Periods, dtype='int'), stream=stream)
            cuda_AVG_Periods = cuda.to_device(np.array(cudafns.AVG_Periods, dtype='int'), stream=stream)

            cudafns.compute_averages_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
                cuda_STDs, cuda_Averages, cuda_SD_Periods, cuda_AVG_Periods, (self.nStocks*len(cudafns.AVG_Periods)), self.nStocks)

            stream.synchronize()

            self.BLOCKS_PER_GRID = math.floor( (self.nStocks*self.nAlgos) / self.THREADS_PER_BLOCK + 1)

            stream = cuda.stream()
            cuda_Averages = cuda.to_device(Averages, stream=stream)
            cuda_Signals = cuda.to_device(self.Signals, stream=stream)
            cuda_InputMatrix = cuda.to_device(self.AlgoInputs, stream=stream)

            cudafns.compute_signals_realtime[self.BLOCKS_PER_GRID, self.THREADS_PER_BLOCK, stream](
                cuda_Averages, cuda_Signals, cuda_InputMatrix,
                self.FIRST_VALID_INDEX, (self.nStocks*self.nAlgos), self.nStocks)

            stream.synchronize()

            self.STDs = STDs.tolist()
            self.Averages = Averages.tolist()
            self.Signals = self.Signals.tolist()

            self.init_report()
            self.update_kernel_status.emit('ready')
            self.timeframe_marks_ready = True
            self.initialRun = False
            self.explorerReady = True



    def downloader_finished(self, success, timestamps, closes):
        self.historicalDataReady = True
        # print("First: {}, Last: {}".format(timestamps[0][-1], timestamps[0][0]))
        if len(self.watchlist) > 0:
            self.data_transform(success, timestamps, closes)
            self.initial_algo_run()
            self.enable_start_button()
        else:
            msgBox = InfoMessageBox('Error', 'CUDA kernels can not be compiled without data. \n\nPlease add at least one instrument to portfolio and restart application\n')

    def receive_valid_id(self, id):
        self.orderID = id

    @pyqtSlot()
    def establish_connection(self):
        self.subscribe()
        self.disable_connect_button()
        self.status_message.emit('Establishing connection...')
        self.thread = QThread()
        self.worker = Worker()
        # self.worker.clientID = self.clientID()
        self.symInfoRequested.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.signalEmitted.connect(self.readWorkerSignal, Qt.DirectConnection)
        self.worker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.worker.emit_error.connect(self.error_received, Qt.DirectConnection)
        self.worker.log.connect(self.worker_log_msg, Qt.DirectConnection)
        self.worker.symbolInfo.connect(self.symbolInfoReceived, Qt.DirectConnection)

        # Downloader
        self.downloader.statusMag.connect(self.status_msg, Qt.DirectConnection)
        self.downloader.subscribe.connect(self.downloader_requested_subscription, Qt.DirectConnection)
        self.downloader.data_status_update.connect(self.data_status_update, Qt.DirectConnection)
        self.downloader.cancel_request.connect(self.worker.cancel_historical_data, Qt.DirectConnection)
        self.downloader.status_change.connect(self.watchlist_data_status, Qt.DirectConnection)
        self.downloader.api_data_request.connect(self.worker.downloader_requested_data, Qt.DirectConnection)
        self.worker.transmit_data_to_downloader.connect(self.downloader.data_received, Qt.DirectConnection)
        self.downloader.log.connect(self.log, Qt.DirectConnection)
        self.tell_downloader_to_stop.connect(self.downloader.stop_forcefully, Qt.DirectConnection)
        self.downloader.download_sequence_finished.connect(self.downloader_finished, Qt.DirectConnection)
        self.downloader.update_hist_request_time.connect(self.update_hist_request_time, Qt.DirectConnection)
        self.worker.tell_downloader_data_is_success.connect(self.downloader.data_end, Qt.DirectConnection)
        self.transmit_order.connect(self.worker.placeOrder, Qt.DirectConnection)
        self.worker.transmit_order_status.connect(self.order_status_update, Qt.DirectConnection)
        self.worker.transmit_commission.connect(self.commission_update, Qt.DirectConnection)
        self.worker.transmit_valid_id.connect(self.receive_valid_id, Qt.DirectConnection)

        # Autocomplete
        # self.w._model.dataRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        # self.worker.toAutocompleter.connect(self.w._model.dataReceived, Qt.DirectConnection)

        # Connection query
        self.chartWindow.amIConnected.connect(self.worker.connectionStatus, Qt.DirectConnection)
        self.worker.amIConnected.connect(self.chartWindow.updateConnectionStatus, Qt.DirectConnection)

        # Matching symbols (source=chart)
        self.chartWindow.lookupRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.symInfoToChart.connect(self.chartWindow.lookupResultsReceived, Qt.DirectConnection)
        self.chartWindow.requestHistData.connect(self.worker.getHistData, Qt.DirectConnection)
        self.worker.sendHistDataToChart.connect(self.chartWindow.newDataReceived, Qt.DirectConnection)

        self.worker.tick.connect(self.tick, Qt.DirectConnection)

        self.worker.moveToThread(self.thread)



        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)

        self.thread.start()
        # self.worker.initiate()

        self.thread.finished.connect(
            lambda: self.enable_connect_button()
        )
        self.thread.finished.connect(
            lambda: self.connectionLabel.setText("Status: disconnected")
        )



if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    app = QApplication(sys.argv)
    with open('{}/{}'.format(path, 'style.qss'), 'r') as f:
        style = f.read()
    app.setStyleSheet(style)
    ex = App()
    sys.exit(app.exec_())
