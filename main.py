import sys, time, threading, os, random, math
import threading
from datetime import datetime, timedelta
from copy import deepcopy
from time import sleep
import dateutil.parser as parser
import sqlite3
import json
import psutil
import signal
import numpy as np

import requests

from PyQt5.QtWidgets import (QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QHBoxLayout,
            QLineEdit, QInputDialog, QLabel, QTableWidget, QTableWidgetItem, QGridLayout, QMessageBox, QStatusBar, QDesktopWidget,
            QScrollArea, QShortcut, QAbstractButton, QDialogButtonBox, QFrame, QFileDialog, QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QIcon, QIntValidator, QFont, QPalette, QColor, QKeySequence, QCloseEvent, QFontDatabase, QBrush
from PyQt5.QtCore import Qt, pyqtSlot, QObject, QThread, pyqtSignal, QTimer, QTime
from PyQt5.QtWebEngineWidgets import QWebEngineView

import dash
from dash import dcc, html

from connection import QTraderConnection
from chart import Chart
# from dashworker import DashWorker
from completer import LineCompleterWidget
from search import SearchWindow
from msgboxes import InfoMessageBox, InfoWidget
from watchlistitem import WatchlistItem
from settings import Settings
# from presets import Presets
from cancelOrder import CancelOrder
from submitOrder import SubmitOrder
from downloader import Downloader
from pisettings import PortfolioItemSettings
from explorer import Explorer
from equity import EquityPlot
from table import CustomTable
from reconnector import Reconnector
from customClient import CustomEClient
from quickChart import QuickChart
from templates import *
from globals import *

from ibapi.contract import Contract
from ibapi.order import Order

import warnings
warnings.filterwarnings("ignore")


class App(QMainWindow):

    closeSignal = pyqtSignal()

    # exportTrades = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.title = 'QTrader'
        self.left = 10
        self.top = 10
        self.showExitDialogue = True
        self.exitDialogueShown = False
        self.maximizeOnStartup = True
        self.setWindowTitle(self.title)
        self.disableAutoRestart = False

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
        actionMenu = mainMenu.addMenu('Action')
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

        # tradesExportButton = QAction(QIcon(), 'Export Trades', self)
        # tradesExportButton.setShortcut('Ctrl+Shift+T')
        # tradesExportButton.setStatusTip('Export Trades')
        # tradesExportButton.triggered.connect(self.export_trades)
        # fileMenu.addAction(tradesExportButton)

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

        self.statusBarComputeTimeMsg = QLabel('', self)

        self.statusMsgHolder.addWidget(self.statusBarConnectionMsg, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.connectionCircle, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarDataStatus, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.statusBarDataStatusBox, alignment=Qt.AlignVCenter)
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
        self.table_widget.update_compute_time.connect(self.compute_time_update, Qt.DirectConnection)
        self.table_widget.closeApp.connect(self.close_without_dialogue, Qt.DirectConnection)
        self.table_widget.restartApp.connect(self.restartWithDialogue, Qt.DirectConnection)
        # self.exportTrades.connect(self.table_widget.export_trades, Qt.DirectConnection)
        self.setCentralWidget(self.table_widget)

        self.closeSignal.connect(self.close)

        if self.maximizeOnStartup: self.showMaximized()

        # View
        chartButton = QAction(QIcon(), 'Chart Window (deactivated)', self)
        chartButton.setShortcut('Ctrl+Shift+C')
        chartButton.setStatusTip('Open chart window')
        chartButton.triggered.connect(self.table_widget.open_chart_window)
        viewMenu.addAction(chartButton)

        # presetsButton = QAction(QIcon(), 'Strategy Presets', self)
        # presetsButton.setShortcut('Ctrl+Shift+P')
        # presetsButton.setStatusTip('Open strategy presets')
        # presetsButton.triggered.connect(self.table_widget.open_presets_window)
        # viewMenu.addAction(presetsButton)

        # explorerButton = QAction(QIcon(), 'Data Explorer', self)
        # explorerButton.setShortcut('Ctrl+Shift+D')
        # explorerButton.setStatusTip('Open Data Explorer')
        # explorerButton.triggered.connect(self.table_widget.open_explorer_window)
        # viewMenu.addAction(explorerButton)

        equityButton = QAction(QIcon(), 'Account Equity', self)
        equityButton.setShortcut('Ctrl+Shift+R')
        equityButton.setStatusTip('Open Equity Plot')
        equityButton.triggered.connect(self.table_widget.show_equity_window)
        viewMenu.addAction(equityButton)

        """
        qChartButton = QAction(QIcon(), 'Quick Chart', self)
        # qChartButton.setShortcut('')
        qChartButton.setStatusTip('Open Quick Chart')
        qChartButton.triggered.connect(self.table_widget.show_quick_chart)
        viewMenu.addAction(qChartButton)
        """

        # Action
        submitOrderBtn = QAction(QIcon(), 'Submit Order', self)
        submitOrderBtn.setShortcut('Ctrl+N')
        submitOrderBtn.setStatusTip('Submit New Order')
        submitOrderBtn.triggered.connect(self.table_widget.submit_order_window)
        actionMenu.addAction(submitOrderBtn)

        cancelOrderBtn = QAction(QIcon(), 'Cancel Order', self)
        cancelOrderBtn.setShortcut('Ctrl+C')
        cancelOrderBtn.setStatusTip('Cancel previously submitted order')
        cancelOrderBtn.triggered.connect(self.table_widget.show_cancel_order_window)
        actionMenu.addAction(cancelOrderBtn)

        icon_path = '{}/{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'resources', 'qtrader_icon128x128.png' )
        self.setWindowIcon(QIcon(icon_path))

        self.show()

    # def export_trades(self):
    #     self.exportTrades.emit()

    def data_status_update(self, status):
        if status == 'loading':
            self.statusBarDataStatus.setText('Data: Loading')
            self.statusBarDataStatusBox.setStyleSheet("background-color: #f39c12; min-width: 17px; height: 17px;")
        elif status == 'ready':
            self.statusBarDataStatus.setText('Data: Ready')
            self.statusBarDataStatusBox.setStyleSheet("background-color: green; min-width: 17px; height: 17px;")

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
        return json.dumps(d, indent=4)



    def export_watchlist(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,
            "Export Portfolio", "portfolio.json", "All Files(*);;JSON Files(*.json)", options = options)
        if fileName:
            with open(fileName, 'w') as f:
                f.write(self.watchlistToJSON(self.table_widget.watchlist))
            self.fileName = fileName
            # self.setWindowTitle(str(os.path.basename(fileName)) + " - Notepad Alpha[*]")

    def import_watchlist(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Import Portfolio", "","JSON Files (*.json)", options=options)
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

    def shutdown_routine(self):
        if self.table_widget.worker.isConnected():
            try:
                self.table_widget.worker.reqAccountUpdates(False, self.table_widget.worker.accountId)
            except:
                self.table_widget.log('error', 'Cancelling account updates subscription failed')
            time.sleep(1/25.)
        self.table_widget.log('info', 'Shutting down')

    def restartWithDialogue(self):
        if not self.disableAutoRestart:
            self.warning = ExitMessageBox(width= 350, height=135)
            self.time_to_wait = 10

            timer = QTimer(self)
            timer.setInterval(1000)
            timer.timeout.connect(self.changeContent)
            timer.start()

            yesButton = QPushButton('Settings')
            yesButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
            yesButton.setFixedSize(100,30)
            noButton  = QPushButton('Shutdown')
            noButton.setFixedSize(100,30)

            self.warning.addButton(yesButton, QMessageBox.YesRole)
            self.warning.addButton(noButton, QMessageBox.NoRole)
            self.warning.setWindowTitle('Restart')
            self.warning.setText("No connection with IB TWS or IB Gateway\n\nRestarting in {0} seconds".format(self.time_to_wait))
            g = self.frameGeometry()
            self.warning.reinit(g)
            ret = self.warning.exec_()
            if ret == 0:
                self.disableAutoRestart = True
                self.show_settings()
                return
            else:
                self.showExitDialogue = False
                self.close()

    def changeContent(self):
        if not self.disableAutoRestart:
            self.time_to_wait -= 1
            self.warning.setText("No connection with IB TWS or IB Gateway\n\nRestarting in {0} seconds".format(self.time_to_wait))
            if self.time_to_wait <= 0:
                os.execv(sys.executable, ['python'] + sys.argv)


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
                self.shutdown_routine()
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
        # if okPressed and text != '':
            # print(text)

    def show_about_window(self):
        self.about = AboutWindow()
        self.about.show()


class SymbolDescripttion:
    def __init__(self, contract):
        self.contract = contract

class ExitMessageBox(QMessageBox):
    def __init__(self, width=300, height=125):
        QMessageBox.__init__(self)
        self.width = width
        self.height = height

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

        self.setMinimumWidth(self.width)
        self.setMinimumHeight(self.height)

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

        self.title = QLabel("QTrader")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font-weight: bold; color: #f39c12; font-size: 21px;}")
        layout.addWidget(self.title)

        self.version = QLabel("Version: pre-release 0.0.1")
        self.version.setAlignment(Qt.AlignCenter)
        self.version.setStyleSheet("QLabel {color: #eeeeee; font-size: 15px;}")
        layout.addWidget(self.version)

        self.releaseDate = QLabel("Release date: Oct 29, 2023")
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



class API(QObject, QTraderConnection):

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
    amIConnectedOrder = pyqtSignal(bool)
    symInfoToChart = pyqtSignal(int, object)
    symInfoToOrder = pyqtSignal(int, object)
    sendHistDataToChart = pyqtSignal(object)
    tick = pyqtSignal(int, int, float)
    log = pyqtSignal(str)
    transmit_data_to_downloader = pyqtSignal(int, object)
    tell_downloader_data_is_success = pyqtSignal(int, str, str)
    transmit_valid_id = pyqtSignal(int)
    # transmit_order_status = pyqtSignal(int, int, float)
    transmit_commission = pyqtSignal(int, float)
    transmit_account_info = pyqtSignal(str, str, str, str)
    transmit_position = pyqtSignal(str, str, float, float, float, float, float, float, str)
    transmit_open_order = pyqtSignal(int, object, object, object)
    transmit_order_status = pyqtSignal(int, str, float, float, float, int)
    reconnected = pyqtSignal()
    tramsmitDataToMain = pyqtSignal(str, object)
    tellMainDataEnded = pyqtSignal(str)

    contractRequestOrigin  = 'unknown'
    sourcesByReqId = {}
    histData = {}

    nonDownloaderReqIds = []
    nonDownloaderSymbols = []

    period = 'daily'
    connection_attempts = 0

    block502error = False

    # host = '127.0.0.1'
    # port = 4002
    # clientId = 0

    validOrderId = 0

    def timeout(self):
        time.sleep(0)

    # def initiate(self):
        # Connection.__init__(self, '127.0.0.1', 7497, 0)
        # super().connect(self.host, self.port, self.clientID)
        # time.sleep(1.5)
        # super().run()

    def adjust_connection_settings(self, port, clientId, accountId, host = '127.0.0.1'):
        self.host = host
        self.port = int(port)
        self.clientID = int(clientId)
        self.accountId = accountId

    def submitSampleOrder(self):
        self.validOrderId = 8
        order = Order()
        order.action = 'BUY'
        order.totalQuantity = 100
        order.orderType, order.transmit, order.eTradeOnly, order.firmQuoteOnly = 'LMT', True, False, False
        order.lmtPrice = 172.5
        contract = Contract()
        contract.symbol, contract.secType, contract.exchange, contract.currency = 'AAPL', 'STK', 'SMART', 'USD'
        self.placeOrder(self.validOrderId, contract, order)
        
    def reconnect(self):
        self.block502error = True
        if not self.isConnected():
            try:
                self.connect()
                self.block502error = False
                self.reconnected.emit()
            except Exception as e: print(e) 

    def __run(self):
        
        if self.isConnected():
            try:
                self.reqAccountUpdates(True, self.accountId)
                self.reqAllOpenOrders()
                super().run()
            except:
                self.log.emit('Failed launching the message loop. Disconnecting')
                self._disconnect()

    def connect(self):
        if not self.isConnected():
            try:
                super().connect(self.host, self.port, self.clientID)
            except:
                print('Connection attempt failed')
            else:
                if not self.isConnected(): print('Bad connection')
                else:
                    self.connected.emit(1)
                    self.reqAccountUpdates(True, self.accountId)
                    self.reqAllOpenOrders()
                    super().run()


    def submit_order(self, order, contract):
        self.validOrderId += 1
        self.placeOrder(self.validOrderId, contract, order)


    def cancel_order(self, orderId):
        self.cancelOrder(orderId, "")

    def connectionStatus(self):
        # self.timeout()
        self.amIConnected.emit(self.isConnected())

    def connectionStatusOrder(self):
        # self.timeout()
        self.amIConnectedOrder.emit(self.isConnected())


    # @pyqtSlot()
    def sym_search(self, arg, source):
        # self.timeout()
        if source == 'chart': 
            self.contractRequestOrigin = 'chart'
        elif source == 'order':
            self.contractRequestOrigin = 'order'
        try:
            self.reqMatchingSymbols(218, arg)
        except:
            if source == 'chart' : 
                self.symInfoToChart.emit(0, 0)
            elif source == 'order':
                self.symInfoToOrder.emit(0, 0)
            else: self.symbolInfo.emit(0, 0)
        # signalEmitted.emit()

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        # self.timeout()
        self.transmit_valid_id.emit(orderId)
        self.validOrderId = orderId - 1


    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=None):
        # self.timeout()
        if False and errorCode == 502 and not self.block502error:
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

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        # print('Transmitting {} {} {} {}'.format(key, val, currency, accountName))
        super().updateAccountValue(key, val, currency, accountName)
        # self.timeout()
        self.transmit_account_info.emit(key, val, currency, accountName)
        # print("UpdateAccountValue. Key:", key, "Value:", val, "Currency:", currency, "AccountName:", accountName)

    def updatePortfolio(self, contract, position, marketPrice: float, marketValue: float, averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        # print("UpdatePortfolio.", "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:",
        #       contract.exchange, "Position:", position, "MarketPrice:", marketPrice,
        #       "MarketValue:", marketValue, "AverageCost:", averageCost,
        #       "UnrealizedPNL:", unrealizedPNL, "RealizedPNL:", realizedPNL,
        #       "AccountName:", accountName)
        # self.timeout()
        exchange = contract.primaryExchange if contract.exchange == '' else contract.exchange
        self.transmit_position.emit(str(contract.symbol), str(exchange), float(position), float(marketPrice), float(averageCost), float(marketValue), float(unrealizedPNL), float(realizedPNL), str(accountName))

    '''
    def openOrder(self, orderId, contract, order, orderState):
        print('Receiving order info')
        super().openOrder(orderId, contract, order, orderState)
        print("OpenOrder. PermId:", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, 
              "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
              "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status,
              "MinTradeQty:", order.minTradeQty, "MinCompeteSize:", order.minCompeteSize,
              "MidOffsetAtWhole:", order.midOffsetAtWhole,"MidOffsetAtHalf:" ,order.midOffsetAtHalf,
              "FAGroup:", order.faGroup, "FAMethod:", order.faMethod)
    '''

    '''
    def orderStatus(self, orderId, status: str, filled, 
                    remaining, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
                            avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,
              "Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
              "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",
              lastFillPrice, "ClientId:", clientId, "WhyHeld:",
              whyHeld, "MktCapPrice:", mktCapPrice)
    '''


    def openOrderEnd(self):
        super().openOrderEnd()


    def symbolSamples(self, reqId, contractDescriptions):
        # super().symbolSamples(reqId, contractDescriptions)
        # self.timeout()
        if self.contractRequestOrigin == 'chart':
            self.symInfoToChart.emit(1, contractDescriptions)
        elif self.contractRequestOrigin == 'order':
            self.symInfoToOrder.emit(1, contractDescriptions)
        else: self.symbolInfo.emit(1, contractDescriptions)
        self.contractRequestOrigin = 'unknown'

    def openOrder(self, orderId, contract, order, orderState):
        # self.timeout()
        super().openOrder(orderId, contract, order, orderState)
        msg = '[openOrder] ID {} Symbol {} {} {} Commissions {}'.format(orderId, contract.symbol, order.action, order.totalQuantity, round(orderState.commission, 6))
        self.log.emit(msg)
        commission = round(orderState.commission, 6)
        if commission > 0: self.transmit_commission.emit(orderId, commission)
        # print("OpenOrder. PermId:", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, 
        #       "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
        #       "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
        #       "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
        #       "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status,
        #       "MinTradeQty:", order.minTradeQty, "MinCompeteSize:", order.minCompeteSize,
        #       "MidOffsetAtWhole:", order.midOffsetAtWhole,"MidOffsetAtHalf:" ,order.midOffsetAtHalf,
        #       "FAGroup:", order.faGroup, "FAMethod:", order.faMethod)
        self.transmit_open_order.emit(orderId, contract, order, orderState)
        

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        # self.timeout()
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        msg = '[orderStatus] ID {} Status {} Filled {} Remaining {} VWAP {}'.format(orderId, status, str(filled), str(remaining), str(avgFillPrice))
        self.log.emit(msg)
        # print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,
        #       "Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
        #       "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",
        #       lastFillPrice, "ClientId:", clientId, "WhyHeld:",
        #       whyHeld, "MktCapPrice:", mktCapPrice)
        
        self.transmit_order_status.emit(int(orderId), str(status), float(filled), float(remaining), float(avgFillPrice), int(permId))

    def cancel_historical_data(self, reqId):
        self.cancelHistoricalData(reqId)

    def prepareContract(self, contract):
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
        return dataType

    def downloader_requested_data(self, reqId, endDateTime, RTH_only, contract):
        dataType = self.prepareContract(contract)
        useRTH = 1 if RTH_only else 0
        self.reqHistoricalData(reqId, contract, endDateTime, "1 M", "30 mins", dataType, useRTH, 1, False, [])

    def reqHistDataOneSymbol(self, reqId, contract, RTHonly=True):
        self.nonDownloaderReqIds.append(reqId)
        self.nonDownloaderSymbols.append(contract.symbol)
        dataType = self.prepareContract(contract)
        useRTH = 1 if RTHonly else 0
        self.reqHistoricalData(reqId, contract, "", "1 M", "30 mins", dataType, useRTH, 1, False, [])


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
        except: 
            msg = 'Error Historical data request failed'
            self.log.emit(msg)

    def historicalData(self, reqId:int, bar):
        # print("HistoricalData. ReqId:", reqId, "BarData.",
        # type(bar.date),
        # type(bar.open),
        # type(bar.high),
        # type(bar.close),
        # type(bar.volume)
        # )
        # self.timeout()
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
        elif reqId in self.nonDownloaderReqIds:
            n = self.nonDownloaderReqIds.index(reqId)
            symbol = self.nonDownloaderSymbols[n]
            self.tramsmitDataToMain.emit(symbol, bar)
        else:
            self.transmit_data_to_downloader.emit(reqId, bar)


    def historicalDataEnd(self, reqId: int, start: str, end: str):
        # self.timeout()
        super().historicalDataEnd(reqId, start, end)
        if reqId in self.sourcesByReqId.keys():
            self.sendHistDataToChart.emit(self.histData[reqId])
        elif reqId in self.nonDownloaderReqIds:
            n = self.nonDownloaderReqIds.index(reqId)
            symbol = self.nonDownloaderSymbols[n]
            self.tellMainDataEnded.emit(symbol)
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
    update_compute_time = pyqtSignal(str, int)
    tell_downloader_to_stop = pyqtSignal()
    data_to_explorer = pyqtSignal(object, object, object)
    transmit_order = pyqtSignal(int, object, object)
    closeApp = pyqtSignal()
    restartApp = pyqtSignal()
    tell_worker_to_cancel_order = pyqtSignal(int)
    symbols_to_qchart = pyqtSignal(object)
    sendDataToQChart = pyqtSignal(object)
    subscribe_to_all_streaming = pyqtSignal()

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.debug = False
        self.useTimeAPI = False
        self.show_gauge_panel = False
        self.debugMode = 0  # 0 - Off        
                            # 1 - Changes in tables

        self.REQUEST_LIMIT_PER_SECOND = 25
        self.MIN_DATAPOINTS_REQUIRED = 11  # 2680
        self.HISTORY_EXCESS_TO_LOAD_PERCENT = 30
        self.MAX_HISTORY_DEPTH_REALTIME = self.MIN_DATAPOINTS_REQUIRED * 1.5
        self.MAX_ATTEMPTS_TO_FETCH_TIMEZONE = 20
        self.histReqId = 1000000
        self.symbols = []
        self.explorerReady = False
        self.explorerInitiated = False
        self.histDataRequestsActive = []
        self.logActive = True
        self.data = {}

        self.CUDA_DEVICE_ID = 0
        self.THREADS_PER_BLOCK = 128


        self.isConnected = False
        self.isExecuting = False
        self.worker = None
        self.searchLastRequested = time.time()
        self.searchQuery = ''
        self.streamingDataReqId = 2000000
        self.config_path = '{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'config' )
        self.settings = {}
        self.read_settings()

        self.historicalDataReady = False
        self.lastHistoricalDataRequest = None
        self.MAX_HISTORICAL_DATA_TIMEOUT_SECONDS = 240

        self.CONNECTION_STATUS_CHECK_FREQUENCY_SECONDS = 1
        self.connection_seconds_elapsed_since_last_check = 0
        self.MAX_RECONNECTION_ATTEMPTS = 18
        self.SECONDS_BETWEEN_CONNECTION_ATTEMPTS = 10
        self.initialConnectionEstablished = False
        self.reconnectionInProgress = False
        self.RESTART_TIMEOUT_SEC = 1
        self.secSinceLastConnCheck = 0

        self.timeframe_marks_ready = False
        self.last_tint = -1
        self.initialRun = True

        self.maxT = 10*10
        self.positionsCLosedToday = False
        self.orderID = 3000000
        self.activeOrders = []
        self.pending_orders = {}

        self.connTimeout = 3.
        self.maxConnTimeout = 600.

        self.last_known_30min_timestamp = -1
        self.last_known_1h_timestamp = -1
        self.last_known_day = -1
        self.last_known_minute = -1
        self.last_known_trading_day = -1

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
        # self.load_presets()
        self.portfolio = {}
        self.loadPortfolio()
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.layout = QGridLayout()
        self.loadPositions()

        self.TFMARKS30MIN = []
        for hour in range(4, 20):
            for half_hour in range(2): self.TFMARKS30MIN.append(hour*100 + half_hour*30)

        self.TFMARKS1H    = [400, 500, 600, 700, 800, 900, 930, 1030, 1130, 1230, 1330, 1430, 1530, 1600, 1700, 1800, 1900]

        self.accountInfo = {
            'NetLiquidation' : {'name':'Net Liquidation Value', 'value':'N/A'},
            'BuyingPower' : {'name':'Buying Power', 'value':'N/A'},
            'DayTradesRemaining' : {'name':'Day Trades Remaining', 'value':'N/A'},
            'InitMarginReq' : {'name':'Initial Margin Requirements', 'value':'N/A'},
            'MaintMarginReq' : {'name':'Maintenance Margin Requirements', 'value':'N/A'},
            'RegTEquity' : {'name':'Reg T Equity', 'value':'N/A'},
            'RegTMargin' : {'name':'Reg T Margin', 'value':'N/A'},
            'AvailableFunds' : {'name':'Available Funds', 'value':'N/A'},
            'CashBalance' : {'name':'Cash Balance', 'value':'N/A'},
            'EquityWithLoanValue' : {'name':'Equity With Loan', 'value':'N/A'},
            'ExcessLiquidity' : {'name':'Excess Liquidity', 'value':'N/A'},
            'FullAvailableFunds' : {'name':'Full Available Funds', 'value':'N/A'},
            'AccruedCash' : {'name':'Accrued Cash', 'value':'N/A'},
            'StockMarketValue' : {'name':'Stock Market Value', 'value':'N/A'},
            'TotalCashBalance' : {'name':'Total Cash Balance', 'value':'N/A'},
            'UnrealizedPnL' : {'name':'Unrealized PnL', 'value':'N/A'},
            'Cushion' : {'name':'Cusion', 'value':'N/A'},
            'AccountCode' : {'name':'Account Code', 'value':'N/A'}
        }

        self.accountInfoList = list(self.accountInfo.keys())

        self.accPositions = {}
        self.POS_TEMPLATE = {'exchange' : '', 'position' : .0, 'mktPrice' : .0, 'VWAP' : .0, 'mktValue' : .0, 'unrealizedPnL' : .0, 'realizedPnL' : .0, 'account' : ''}

        self.orders = {}
        self.ORDER_PRESET = {'symbol': '', 'exchange':'', 'action':'', 'type':'', 'qty':'', 'limit':'', 
                             'stop':'', 'status':'', 'filled':'', 'remaining':'', 'avgfillprice':'',
                             'orderId':'', 'permId':'', 'TIF':'', 'secType':'', 'tradeReported':False}

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
        self.accountTab = QWidget()
        self.positionsTab = QWidget()
        self.ordersTab = QWidget()
        self.equityTab = QWidget()
        self.algoTab = QWidget()
        # self.posTab = QWidget()
        self.tradesTab = QWidget()
        self.trades_old = []
        self.tabs.resize(300,200)



        # Add tabs
        self.tabs.addTab(self.tab1,"Dashboard")
        self.tabs.addTab(self.positionsTab, "Positions")
        self.tabs.addTab(self.ordersTab, "Orders")
        self.tabs.addTab(self.accountTab,"Account")
        self.tabs.addTab(self.algoTab,"Algorithms")
        # self.tabs.addTab(self.posTab, "PositionsOld")
        self.tabs.addTab(self.tradesTab, "Trades")
        self.tabs.addTab(self.equityTab, "Equity")
        # self.tabs.addTab(self.tab2,"Pending Liquidations")
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
        self.clockLayout.setContentsMargins(0, 0, 0, 0)
        self.clockTxt = QLabel('')
        self.clockTime = QLabel('')
        self.clockLayout.addWidget(self.clockTxt)
        self.clockLayout.addWidget(self.clockTime)
        self.clock.setLayout(self.clockLayout)

        self.mktStatusWidget = QWidget()
        self.mktStatusTable = QGridLayout()
        self.mktStatusTable.setContentsMargins(0, 0, 0, 0)
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



        # self.tab1.layout.addLayout(self.buttonPanel, 0, 3, alignment=Qt.AlignRight)
        self.tab1.layout.addWidget(self.symbolSerachText, 0, 0)
        self.tab1.layout.addWidget(self.searchButton, 0, 1)
        self.tab1.layout.addWidget(self.clock, 0, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignVCenter)
        self.tab1.layout.addWidget(self.mktStatusWidget, 1, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignVCenter)
        if self.show_gauge_panel:
            self.tab1.layout.addWidget(self.gaugePanel, 3, 0, 1, 4, alignment=Qt.AlignCenter|Qt.AlignTop)
        self.tab1.layout.addWidget(self.watchlistWidget, 4, 0, 20, 4, alignment=Qt.AlignTop|Qt.AlignCenter)
        # self.tab1.layout.addWidget(self.connectButton, 0, 8, 1, 3)
        # self.tab1.layout.addWidget(self.startButton, 0, 11, 1, 3)
        # self.tab1.layout.addWidget(self.stopButton, 0, 14, 1, 3, alignment=Qt.AlignRight)
        # self.tab1.layout.setHorizontalSpacing(20)
        # self.tab1.layout.addWidget(self.connectionLabel, 2, 5)



        # self.tab1.layout.addLayout(self.stock, 1, 0, alignment=Qt.AlignLeft)


        # self.tab1.setLayout(self.tab1.layout)
        

        # Second tab ###########################################################
        self.createTable()
        self.tab2.layout = QVBoxLayout()
        self.tab2.layout.addWidget(self.tableWidget)
        self.tab2.setLayout(self.tab2.layout)

        # Account ##############################################################
        self.accountTab.wrapper = QVBoxLayout()
        self.accountTab.setLayout(self.accountTab.wrapper)
        self.accountTable = QTableWidget()
        self.accountTable.cellChanged.connect(self.accountCellChanged, Qt.DirectConnection)
        self.accountTable.setColumnCount(2)
        self.accountTable.setRowCount(len(self.accountInfoList))
        self.accountTab.wrapper.addWidget(self.accountTable)

        self.accountTable.horizontalHeader().setVisible(False)
        self.accountTable.verticalHeader().setVisible(False)
        self.accountTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.accountTable.setShowGrid(False)

        header = self.accountTable.horizontalHeader()       
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        row = 0
        for key in self.accountInfoList:
            w_item = QTableWidgetItem( str(self.accountInfo[key]['name']) )
            w_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.accountTable.setItem(row, 0, w_item)
            if row%2 == 1: w_item.setBackground(QColor(74, 105, 135))
            w_item = QTableWidgetItem( str(self.accountInfo[key]['value']) )
            w_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if row%2 == 1: w_item.setBackground(QColor(74, 105, 135))
            self.accountTable.setItem(row, 1, w_item)
            row += 1

        self.accountData = {
            'Reg T Margin': -1,
            'NLV': -1
        }

        # Positions ###########################################################
        self.positionsTab.wrapper = QVBoxLayout()
        self.positionsTab.setLayout(self.positionsTab.wrapper)
        self.positionsTable = QTableWidget()
        self.positionsTable.cellChanged.connect(self.positionsCellChanged, Qt.DirectConnection)
        self.positionsTable.setColumnCount(9)
        self.positionsTable.setRowCount(0)
        self.positionsTab.wrapper.addWidget(self.positionsTable)

        self.positionsTable.verticalHeader().setVisible(False)
        self.positionsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.positionsTable.setHorizontalHeaderLabels(['Instrument', 'Exchange', 'Position', 'Mkt Price', 'VWAP', 'Mkt Value', 'Unrealized PnL', 'Realized PnL', 'Account ID'])
        header = self.positionsTable.horizontalHeader()
        self.symbolFont = QFont()
        self.symbolFont.setBold(True)

        for col in range(9): header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        
        # Orders ###############################################################
        self.ordersTab.wrapper = QVBoxLayout()
        self.ordersTab.setLayout(self.ordersTab.wrapper)
        self.ordersTable = QTableWidget()
        self.ordersTable.cellChanged.connect(self.ordersCellChanged, Qt.DirectConnection)
        self.ordersTable.setColumnCount(14)
        self.ordersTable.setRowCount(0)
        self.ordersTab.wrapper.addWidget(self.ordersTable)

        self.ordersTable.verticalHeader().setVisible(False)
        self.ordersTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ordersTable.setHorizontalHeaderLabels(['Symbol', 'Exchange', 'Action', 'Order Type', 'Qty', 'Limit Price', 'Stop Price', 'Status', 'Filled', 'Remaining', 'Avg Fill Price', 'TIF', 'Order ID', 'Perm ID'])
        header = self.ordersTable.horizontalHeader()
        for col in range(14): header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # Algorithms #############################################################
        self.algoTab.wrapper = QVBoxLayout()
        self.algoTab.setLayout(self.algoTab.wrapper)
        self.algoTable = QTableWidget()
        self.algoTable.cellChanged.connect(self.ordersCellChanged, Qt.DirectConnection)
        self.algoTable.setColumnCount(11)
        self.algoTable.setRowCount(0)
        self.algoTab.wrapper.addWidget(self.algoTable)

        self.algoTable.verticalHeader().setVisible(False)
        self.algoTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.algoTable.setHorizontalHeaderLabels(['Symbol', 'Algorithm', 'Position', 'VWAP', 'TP Active', 'TP Price', 'TP Qty', 'SL Active', 'SL Price', 'SL Qty', 'State'])
        header = self.algoTable.horizontalHeader()
        for col in range(11): header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.updateAlgoTable()
       

        # Positions (old) ######################################################
        """
        self.posTab.wrapper = QVBoxLayout()
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
        """

        # Trades ###############################################################
        self.tradesTab.wrapper = QVBoxLayout()
        self.tradesTab.setLayout(self.tradesTab.wrapper)
        self.tradesTable_old = QTableWidget()
        self.tradesTable_old.setColumnCount(6)
        self.tradesTable_old.setRowCount(0)
        self.tradesTable_old.setColumnWidth(0, 320)
        self.tradesTable_old.verticalHeader().setVisible(False)
        self.tradesTable_old.setHorizontalHeaderLabels( ['Date', 'Time', 'Symbol', 'Action', 'Qty', 'Fill'] )

        self.tradesTable = QTableWidget()
        self.tradesTable.setColumnCount(6)
        self.tradesTable.setRowCount(0)
        self.tradesTab.wrapper.addWidget(self.tradesTable)

        self.tradesTable.verticalHeader().setVisible(False)
        self.tradesTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tradesTable.setHorizontalHeaderLabels(['Symbol', 'Date', 'Time', 'Action', 'Qty', 'Fill'])
        header = self.tradesTable.horizontalHeader()
        for col in range(6): header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.trades = []

        # Equity ###############################################################
        self.equityTab.wrapper = QVBoxLayout()
        self.equityTab.setLayout(self.equityTab.wrapper)
        self.equityTable = QTableWidget()
        self.equityTable.setColumnCount(6)
        self.equityTable.setRowCount(0)
        self.equityTab.wrapper.addWidget(self.equityTable)

        self.equityTable.verticalHeader().setVisible(False)
        self.equityTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.equityTable.setHorizontalHeaderLabels(['Symbol', 'Date', 'Time', 'Mkt Price', 'Qty', 'Realized PnL'])
        header = self.equityTable.horizontalHeader()
        for col in range(6): header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.equity = []
        self.cumEquity = [.0]

        self.initiate_db_connection()

        self.equityPlot = EquityPlot()

        """
        self.qChart = QuickChart()
        self.qChart.requestSymbols.connect(self.transmitSymbolsToQChart, Qt.DirectConnection)
        self.symbols_to_qchart.connect(self.qChart.getSymbols, Qt.DirectConnection)
        self.qChart.requestData.connect(self.qChartRequestedData, Qt.DirectConnection)
        self.sendDataToQChart.connect(self.qChart.dataReceived, Qt.DirectConnection)
        """

        # Log tab ##############################################################
        self.tab3.wrapper = QVBoxLayout()
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


        # self.presets = Presets()
        # self.presets.send_presets_to_app.connect(self.new_presets_received, Qt.DirectConnection)

        self.orderCancelWindow = CancelOrder()
        self.orderCancelWindow.cancel_order.connect(self.cancel_order, Qt.DirectConnection)

        self.submitOrderWindow = SubmitOrder()

        # API Main Thread #################################################
        """
        self.apiThread = QThread()
        self.worker = API()

        self.worker.signalEmitted.connect(self.readWorkerSignal, Qt.DirectConnection)
        self.worker.connected.connect(self.worker_reconnected, Qt.DirectConnection)
        # self.worker.reconnected.connect(self.worker_reconnected, Qt.DirectConnection)
        self.worker.emit_error.connect(self.error_received, Qt.DirectConnection)
        self.worker.log.connect(self.worker_log_msg, Qt.DirectConnection)
        self.worker.symbolInfo.connect(self.symbolInfoReceived, Qt.DirectConnection)
        self.worker.transmit_order_status.connect(self.order_status_update, Qt.DirectConnection)
        self.worker.transmit_commission.connect(self.commission_update, Qt.DirectConnection)
        self.worker.transmit_valid_id.connect(self.receive_valid_id, Qt.DirectConnection)
        self.worker.transmit_account_info.connect(self.account_info_update, Qt.DirectConnection)
        self.worker.transmit_position.connect(self.position_update, Qt.DirectConnection)
        self.worker.transmit_open_order.connect(self.open_order_received, Qt.DirectConnection)
        self.worker.tick.connect(self.tick, Qt.DirectConnection)
        
        self.transmit_order.connect(self.worker.placeOrder, Qt.DirectConnection)
        self.symInfoRequested.connect(self.worker.sym_search, Qt.DirectConnection)
        self.tell_worker_to_cancel_order.connect(self.worker.cancel_order, Qt.DirectConnection)

        self.submitOrderWindow.amIConnected.connect(self.worker.connectionStatusOrder, Qt.DirectConnection)
        self.worker.amIConnectedOrder.connect(self.submitOrderWindow.updateConnectionStatus, Qt.DirectConnection)
        self.submitOrderWindow.lookupRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.symInfoToOrder.connect(self.submitOrderWindow.lookupResultsReceived, Qt.DirectConnection)
        self.submitOrderWindow.submit_order.connect(self.worker.submit_order, Qt.DirectConnection)        

        self.worker.moveToThread(self.apiThread)

        self.worker.finished.connect(self.apiThread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.apiThread.finished.connect(self.apiThread.deleteLater)

        self.worker.adjust_connection_settings(self.settings['connection']['port'], self.settings['connection']['clientId'], self.settings['account']['accountId'])
        self.apiThread.start()
        """
        ###################################################################


        # Run Dash
        """
        self.dashThread = QThread()
        self.dashWorker = DashWorker()
        self.dashWorker.moveToThread(self.dashThread)
        self.dashThread.started.connect(self.dashWorker.run)
        # self.dashWorker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.dashWorker.finished.connect(self.dashThread.quit)
        self.dashWorker.finished.connect(self.dashWorker.deleteLater)
        self.dashThread.finished.connect(self.dashThread.deleteLater)
        self.dashThread.start()
        """

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

        # self.chartWindow = Chart()
        # Essential chart funactionality commented with single line comments,
        # additional functionality (dash) with multi-line comments
        """
        self.dashWorker.requestWindowSize.connect(self.chartWindow.get_browser_size, Qt.DirectConnection)
        self.chartWindow.transmitWindowSize.connect(self.dashWorker.update_window_size, Qt.DirectConnection)

        self.chartWindow.resized.connect(self.dashWorker.resized, Qt.DirectConnection)
        # self.chartWindow.button.clicked.connect(self.dashWorker.update_figure, Qt.DirectConnection)

        self.chartWindow.tellDashToChangeState.connect(self.dashWorker.stateChange, Qt.DirectConnection)
        self.chartWindow.sendDataToDash.connect(self.dashWorker.newDataReceived, Qt.DirectConnection)
        self.dashWorker.ready.connect(self.startupRoutine, Qt.DirectConnection)
        """

        self.currentTimeISAheadOfEDT = False
        self.timeDIfferenceWithEDT = 0
        self.timeMultiplier = 1
        self.timeInfoReady = False

        self.startupRoutine()
        self.establish_connection()

    def updateAlgoTable(self):
        self.algoTable.setRowCount(0)
        row = 0
        for symbol in self.positions.keys():
            for strategy in self.positions[symbol].keys():
                s = self.positions[symbol][strategy]
                self.algoTable.insertRow(row)
                self.algoTable.setItem(row, 0, QTableWidgetItem( symbol ))
                self.algoTable.setItem(row, 1, QTableWidgetItem( strategy ))
                self.algoTable.setItem(row, 2, QTableWidgetItem( str( s['position'] ) ))
                self.algoTable.setItem(row, 3, QTableWidgetItem( str( s['vwap'] ) ))
                self.algoTable.setItem(row, 4, QTableWidgetItem( 'No' if not s['tpActive'] else 'Active' ))
                self.algoTable.setItem(row, 5, QTableWidgetItem( str( s['tpPrice'] ) ))
                self.algoTable.setItem(row, 6, QTableWidgetItem( str( s['tpQty'] ) ))
                self.algoTable.setItem(row, 7, QTableWidgetItem( 'No' if not s['slActive'] else 'Active' ))
                self.algoTable.setItem(row, 8, QTableWidgetItem( str( s['slPrice'] ) ))
                self.algoTable.setItem(row, 9, QTableWidgetItem( str( s['slQty'] ) ))
                self.algoTable.setItem(row, 10, QTableWidgetItem( s['state'] ))


    def ordersCellChanged(self, row, column):
        if self.debugMode == 1: print('Orders. Changed row {} column {}'.format(row, column))

    def positionsCellChanged(self, row, column):
        if self.debugMode == 1: print('Positions. Changed row {} column {}'.format(row, column))

    def accountCellChanged(self, row, column):
        if self.debugMode == 1: print('Account. Changed row {} column {}'.format(row, column))

    def transmitSymbolsToQChart(self, code):
        symbols = []
        for key in list(self.watchlist.keys()):
            symbols.append(self.watchlist[key].contract.symbol)
        self.symbols_to_qchart.emit(symbols)

    def preprocessDataForQChart(self, data):
        d = []
        for n in range(len(data['close'])):
            d.append(
                (n,
                 data['open'][n],
                 data['high'][n],
                 data['low'][n],
                 data['close'][n])
            )
        return d

    def qChartRequestedData(self, symbol, timeframe):
        if symbol in self.downloader.data.keys():
            data = self.preprocessDataForQChart(self.downloader.data[symbol])
            self.sendDataToQChart.emit(data)


    def initiate_db_connection(self):
        DB_DIR = '{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'db' )
        if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)
        self.DB_PATH = ''.join([DB_DIR, '/', 'history.db'])

        con = sqlite3.connect(self.DB_PATH)
        cur = con.cursor()

        query            = """ CREATE TABLE IF NOT EXISTS trades (
                                        id integer PRIMARY KEY,
                                        ticker text NOT NULL,
                                        sectype text NOT NULL,
                                        datetime text NOT NULL,
                                        action text NOT NULL,
                                        qty real,
                                        fill real,
                                        pnl text
                                    ); """

        cur.execute(query)

        query            = """ CREATE TABLE IF NOT EXISTS equity (
                                        id integer PRIMARY KEY,
                                        ticker text NOT NULL,
                                        datetime text NOT NULL,
                                        mktprice real,
                                        qty real,
                                        pnl real
                                    ); """
        
        cur.execute(query)

        cur.execute("SELECT * FROM trades")
        rows = cur.fetchall()
        for row in rows: self.trades.append(deepcopy(row))

        row = 0  # self.tradesTable.rowCount()
        for trade in self.trades:
            self.tradesTable.insertRow(row)
            self.tradesTable.setItem(row, 0, QTableWidgetItem(trade[1]))
            self.tradesTable.item(row, 0).setForeground(QColor(243, 156, 18))
            self.tradesTable.item(row, 0).setFont(self.symbolFont)
            self.tradesTable.setItem(row, 1, QTableWidgetItem(trade[3][:10]))
            self.tradesTable.setItem(row, 2, QTableWidgetItem(trade[3][11:]))
            self.tradesTable.setItem(row, 3, QTableWidgetItem(trade[4]))
            if trade[4] == 'BUY':
                self.tradesTable.item(row, 3).setForeground(QColor(0, 230, 118))
            else: self.tradesTable.item(row, 3).setForeground(QColor(255, 82, 82))
            # self.tradesTable.item(row, 3).setFont(self.symbolFont)
            self.tradesTable.setItem(row, 4, QTableWidgetItem(str(trade[5])))
            self.tradesTable.setItem(row, 5, QTableWidgetItem(str(trade[6])))

        cur.execute("SELECT * FROM equity")
        rows = cur.fetchall()
        equityItems = []
        for row in rows: equityItems.append(deepcopy(row))
        cur.close()

        row = 0
        for item in equityItems:
            self.equityTable.insertRow(row)
            self.equityTable.setItem(row, 0, QTableWidgetItem(item[1]))
            self.equityTable.item(row, 0).setForeground(QColor(243, 156, 18))
            self.equityTable.item(row, 0).setFont(self.symbolFont)
            self.equityTable.setItem(row, 1, QTableWidgetItem(item[2][:10]))
            self.equityTable.setItem(row, 2, QTableWidgetItem(item[2][11:]))
            self.equityTable.setItem(row, 3, QTableWidgetItem(str(item[3])))
            self.equityTable.setItem(row, 4, QTableWidgetItem(str(item[4])))
            self.equityTable.setItem(row, 5, QTableWidgetItem( ''.join(['$', str(round(item[5], 2))]) ))
            c = QColor(0, 230, 118) if float(item[5]) >= .0 else QColor(255, 82, 82)
            self.equityTable.item(row, 5).setForeground(c)
            # self.equityTable.item(row, 5).setFont(self.symbolFont)
            self.equity.append(float(item[5]))
            self.cumEquity.append(self.cumEquity[-1]+float(item[5]))


    def submit_market_order(self, symbol, qty, direction='BUY'):
        _contract = None
        for reqId in self.watchlist.keys():
            if self.watchlist[reqId].contract.symbol.upper() == symbol.upper():
                _contract = self.watchlist[reqId].contract
                break
        if _contract == None:
            self.log('error', 'Could not place order {} {} {} @MKT. Contract is not in the watchlist.'.format(
                direction, qty, symbol
            ))
            return
        if direction not in ['BUY', 'SELL']:
            self.log('error', 'Could not place order {} {} {} @MKT. Unknown action {}.'.format(
                direction, qty, symbol, direction
            ))
            return
        if qty <= 0:
            self.log('error', 'Could not place order {} {} {} @MKT. Invalid Qty.'.format(
                direction, qty, symbol
            ))
            return

        order = Order()
        order.action = direction
        order.totalQuantity = qty
        order.orderType, order.transmit, order.eTradeOnly, order.firmQuoteOnly = 'MKT', True, False, False
        contract = Contract()
        contract.symbol, contract.secType, contract.exchange, contract.currency = symbol, 'STK', 'SMART', 'USD'
        contract.primaryExchange = _contract.primaryExchange

        self.worker.submit_order(order, contract)


    def cancel_order(self, orderId):
        self.tell_worker_to_cancel_order.emit(orderId)

    def data_status_update(self, msg):
        self.update_data_status.emit(msg)

    def read_settings(self):
        filename = self.config_path + '/settings.json'
        if os.path.isfile(filename):
            with open(filename) as f:
                self.settings = json.load(f)
        else:
            self.settings = {"strategy": {"onlyRTH_history": True, "onlyRTH_trading": True, "pos_size": 100, "flatten_eod": False, "flatten_eod_seconds": 300}, "connection": {"port": 4002, "clientId": 0}, "server": {"address": "000.000.000.000", "key": "", "role": "Client"}, "common": {"checkUpdates": True, "risk": 300, "animation": True}, "margin": {"intraday": 19, "overnight": 29}, "account": {"accountId": "DU1869966", "delayed_quotes": True}}

    """
    def load_presets(self):
        self.preset_data = {}
        filename = '{}{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/', 'presets.json' )
        if os.path.isfile(filename):
            with open(filename) as f:
                self.preset_data = json.load(f)
    """


    """
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
    """


    def log(self, level, msg):
        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        t = t.strftime("%Y-%m-%d %I:%M:%S.%f %p")
        fullMsg = '{} [{}] {}\n'.format(t, level.upper(), msg)
        rowPosition = self.logTable.rowCount()
        self.logTable.insertRow(rowPosition)
        self.logTable.setItem(rowPosition, 0, QTableWidgetItem(fullMsg))
        fileName = self.logInfo if level == 'info' else self.logError
        if self.logActive:
            with open(fileName, 'a+') as f: f.write(fullMsg)

    """
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
    """


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

        self.downloader.receive_watchlist(self.watchlist)
        self.downloader.receive_datapoint_requirement(self.MIN_DATAPOINTS_REQUIRED, 0)
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

        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        self.tint = t.hour*100 + t.minute
        self.mint = t.minute
        self.time = t



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
        for column in ['Symbol', 'Exchange', 'Prev. Close', 'Change', 'Bid', 'Last', 'Ask', 'Position', 'Value', 'Execution', 'Auction', 'Session', 'History', '']:
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
            item = WatchlistItem(reqId, self.watchlist[reqId].contract, 0, animated=self.settings['common']['animation'])
            self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
            self.watchlistItems[reqId] = item
        if len(self.watchlist) == 0:
            self.noItemsInWatchlist()
        return

    """
    def export_trades(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,
            "Export Trades", "Trades {}.csv".format(datetime.now().strftime("%Y-%b-%d %H.%M.%S")), "CSV Files(*.csv)", options = options)
        if fileName:
            header = ['Time', 'Symbol', 'Algorithm', 'Action', 'Qty', 'VWAP']
            data = []
            for i in range(self.trades_old):
                d = []
                for j in range(len(self.trades_old[i])):
                    d.append(str(self.trades_old[i][j]))
                data.append(d)
            with open(fileName, 'w', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(data)
    """

    """
    def get_total_positions(self, reqId):
        symbol = self.watchlist[reqId].contract.symbol
        total_positions = 0
        for _, position in self.positions[symbol]['positions'].items():
            total_positions += int(position)

        return total_positions
    """

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
        return json.dumps(d, indent=4)

    def watchlistPath(self):
        return '{}/{}/{}'.format( os.path.dirname(os.path.abspath(__file__)), 'config', 'watchlist.json' )

    def saveWatchlist(self):
        fileName = self.watchlistPath()
        with open(fileName, 'w') as f:
            f.write(self.watchlistToJSON(self.watchlist))


    def savePortfolio(self):
        fileName = self.config_path + '/portfolio.json'
        with open(fileName, 'w') as f:
            f.write( json.dumps(self.portfolio, indent=4) )

    def savePositions(self):
        fileName = self.config_path + '/positions.json'
        with open(fileName, 'w') as f:
            f.write( json.dumps(self.positions, indent=4) )
        self.updateAlgoTable()


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

    def update_portfolio(self, portfolio, symbol):
        self.portfolio = deepcopy(portfolio)
        permissions_changed = False
        for symbol, settings in self.portfolio.items():
            for setting, value in settings['permissions'].items():
                if type(value) == bool and value == True and self.positions[symbol][setting]['state'] == 'deactivated':
                    self.positions[symbol][setting] = deepcopy(STRATEGY_INFO)
                    permissions_changed = True
        self.savePortfolio()
        if permissions_changed: self.savePositions()
        self.adjust_execution_label(symbol)


    def update_portfolio_settings(self, symbol):
        exchange = ''
        for reqId, contractDescription in self.watchlist.items():
            if contractDescription.contract.symbol == symbol:
                exchange = contractDescription.contract.primaryExchange
                break
        self.portfolio_settings_window = PortfolioItemSettings(symbol, exchange, self.portfolio)
        self.portfolio_settings_window.save_settings.connect(self.update_portfolio, Qt.DirectConnection)

    def requestDataAndSubscribe(self, contract):
        self.histReqId += 1
        if contract.symbol in self.data.keys(): del self.data[contract.symbol]
        self.worker.reqHistDataOneSymbol(self.histReqId, contract, self.settings['strategy']['onlyRTH_history'])

    def new_portfolio_item(self):
        return deepcopy(DEFAULT_PORTFOLIO_ENTRY)

    def addToWatchlistFromSearch(self, contractDescription):
        self.addToWatchlist(contractDescription, manual=True)

    def addToWatchlist(self, contractDescription, startup = False, manual=False):
        if len(self.watchlist) == 0: self.noitem[0].deleteLater()
        self.streamingDataReqId += 1
        self.watchlist[self.streamingDataReqId] = contractDescription
        if self.isConnected and not startup and not manual:
            self.worker.subscribeToStreamingData(self.streamingDataReqId, contractDescription)
        if not startup and contractDescription.contract.symbol not in list(self.positions.keys()):
            self.positions[contractDescription.contract.symbol] = deepcopy(STRATEGY_TEMPLATE)
            self.savePositions()
        # self.refreshWatchlistLayout()
        item = WatchlistItem(self.streamingDataReqId, contractDescription.contract, 0, animated=self.settings['common']['animation'])
        item.remove.connect(self.removeFromWatchlist, Qt.DirectConnection)
        item.requestMarketState.connect(self.getMktState, Qt.DirectConnection)
        item.update_settings.connect(self.update_portfolio_settings, Qt.DirectConnection)
        self.sendMktStateToWatchlist.connect(item.mktStateUpdate, Qt.DirectConnection)
        self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
        self.watchlistItems[self.streamingDataReqId] = item

        if not startup:
            self.saveWatchlist()

            portfolio_item = self.new_portfolio_item()
            
            self.portfolio[contractDescription.contract.symbol.upper()] = {}
            self.portfolio[contractDescription.contract.symbol.upper()]['permissions'] = deepcopy(portfolio_item)
            self.portfolio[contractDescription.contract.symbol.upper()]['pos_size'] = int(self.settings['strategy']['pos_size'])
            self.savePortfolio()

            item._history.setText('Loading...')
            item._history.setStyleSheet("QLabel{color:#aaaaaa; font-weight: normal;}")
            self.requestDataAndSubscribe(contractDescription.contract)


    def removeFromWatchlist(self, reqId):

        # if self.isConnected: self.close_all_positions(reqId)

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

    def update_data(self, symbol, price, timeframe):
        if symbol not in self.data.keys(): return
        s = self.data[symbol][timeframe]
        s['high'][-1] = max(s['high'][-1], price)
        s['low'][-1]  = min(s['low'][-1], price)
        s['close'][-1] = price

    def flush_data(self, symbol, price, timeframe):
        if symbol not in self.data.keys(): return
        s = self.data[symbol][timeframe]
        s['datetime'].append(self.time)
        s['open'].append(price)
        s['high'].append(price)
        s['low'].append(price)
        s['close'].append(price)
        s['volume'].append(0)


    def tick(self, reqId, tickType, price):
        if reqId in self.watchlistItems:
            self.watchlistItems[reqId]._update(tickType, price)

        if tickType != 4 or reqId not in self.watchlistItems.keys(): return

        symbol = self.watchlistItems[reqId].symbol

        # s = self.data[symbol]['30min']
        # print('{} Date {} Open {} High {} Low {} Close {}'.format(
        #     symbol,
        #     s['datetime'][-1],
        #     s['open'][-1],
        #     s['high'][-1],
        #     s['low'][-1],
        #     s['close'][-1]
        # ))

        if self.mint == self.last_known_minute:
            for timeframe in ['30min', '1h', 'daily']: self.update_data(symbol, price, timeframe)
        else:
            self.last_known_minute = self.mint
            if self.tint in self.TFMARKS30MIN:
                self.flush_data(symbol, price, '30min')
                if self.tint in self.TFMARKS1H:
                    self.flush_data(symbol, price, '1h')
                else: self.update_data(symbol, price, '1h')
            else:
                for timeframe in ['30min', '1h']: self.update_data(symbol, price, timeframe)

            if self.data[symbol]['daily']['datetime'][-1].day != self.time.day:
                self.flush_data(symbol, price, 'daily')
                self.data[symbol]['meta']['openingTick'] = True
            else: 
                self.update_data(symbol, price, 'daily')
                self.data[symbol]['meta']['openingTick'] = False

        for strategy in self.positions[symbol].keys():
            if self.portfolio[symbol]['permissions'][strategy]:
                stratdata = self.positions[symbol][strategy]
                if strategy == 'Long Breakout':
                    # Long Breakout - Initial Entry
                    activeOrder = stratdata['activeOrderId'] == -1
                    if stratdata['state'] == 'activated' and not activeOrder:
                        # Deactivate strategy if day opened with a gap
                        # or if launched when instrument is already trading above the 
                        # entry level
                        if (self.data[symbol]['meta']['openingTick'] or self.data[symbol]['meta']['firstEverTick'] or self.positions[symbol][strategy]['lastPrice'] == -1 ) \
                            and price > self.portfolio[symbol]['permissions'][strategy + ' Price']:
                            self.deactivateStrategy(symbol, strategy)
                            self.log('info', 'Instrument is trading above breakout level. Deactivating strategy {}. Symbol {}'.format(strategy, symbol))
                        elif price > self.portfolio[symbol]['permissions'][strategy + ' Price']:
                            risk = price - self.data[symbol]['daily']['low'][-1] + 2 * self.tickSize(price) * SLIPPAGE_IN_TICKS
                            if risk <= 0:
                                self.deactivateStrategy(symbol, strategy)
                                self.log('error', 'Can not buy below day low. Price {} Day Low {} Symbol {}'.format(
                                    price, self.data[symbol]['daily']['low'][-1], symbol
                                ))
                            else:
                                posSize = self.positionSize(symbol, price, risk, 'BUY')
                                if posSize <= 0: self.deactivateStrategy(symbol, strategy)
                                else:
                                    self.positions[symbol][strategy]['activeOrderId'] = self.worker.validOrderId + 1
                                    self.positions[symbol][strategy]['slPrice'] = self.data[symbol]['daily']['low'][-1] - self.tickSize(price) * SLIPPAGE_IN_TICKS
                                    self.submit_market_order(symbol, posSize, direction='BUY')
                                    self.log('info', 'Submitting MKT order to BUY {} {}'.format(posSize, symbol))
                                    self.savePositions()

                    if stratdata['state'] == 'initiated' and not activeOrder:
                        if price < stratdata['slPrice']:
                            stratdata['activeOrderId'] = self.worker.validOrderId + 1
                            stratdata['orderInfo'] = 'stoppedOut'
                            self.submit_market_order(symbol, stratdata['slQty'], direction='SELL')
                            self.log('info', 'Stopped out. {} {}@{}'.format(stratdata['slQty'], symbol, price))
                        elif stratdata['tpActive'] and price > stratdata['tpPrice']:
                            stratdata['activeOrderId'] = self.worker.validOrderId + 1
                            stratdata['orderInfo'] = 'tpHit'
                            self.submit_market_order(symbol, stratdata['tpQty'], direction='SELL')
                            self.log('info', 'Reached target. Selling {} {}@{}'.format(stratdata['tpQty'], symbol, price))

                    if not stratdata['slTrailing'] and price > stratdata['slPrice'] + 2 * (stratdata['vwap'] - stratdata['slPrice']):
                        stratdata['slTrailing'] = True
                        stratdata['slPrice'] = self.roundToNearestTick(stratdata['vwap'] + self.tickSize(price), price)

                    if stratdata['slTrailing'] and stratdata['slPrice'] != self.data[symbol]['1h']['low'][-1]:
                        stratdata['slPrice'] = max(stratdata['slPrice'], self.data[symbol]['1h']['low'][-1])


                    if self.positions[symbol][strategy]['lastPrice'] == -1: self.positions[symbol][strategy]['lastPrice'] = price

                elif strategy == 'Short Breakout':
                    # Short Breakout - Initial Entry
                    activeOrder = stratdata['activeOrderId'] == -1
                    if stratdata['state'] == 'activated' and not activeOrder:
                        # Deactivate strategy if day opened with a gap
                        # or if launched when instrument is already trading above the 
                        # entry level
                        if (self.data[symbol]['meta']['openingTick'] or self.data[symbol]['meta']['firstEverTick'] or self.positions[symbol][strategy]['lastPrice'] == -1 ) \
                            and price < self.portfolio[symbol]['permissions'][strategy + ' Price']:
                            self.deactivateStrategy(symbol, strategy)
                            self.log('info', 'Instrument is trading below breakout level. Deactivating strategy {}. Symbol {}'.format(strategy, symbol))
                        elif price < self.portfolio[symbol]['permissions'][strategy + ' Price']:
                            risk = self.data[symbol]['daily']['high'][-1] - price + 2 * self.tickSize(price) * SLIPPAGE_IN_TICKS
                            if risk <= 0:
                                self.deactivateStrategy(symbol, strategy)
                                self.log('error', 'Can not sell above day high. Price {} Day high {} Symbol {}'.format(
                                    price, self.data[symbol]['daily']['high'][-1], symbol
                                ))
                            else:
                                posSize = self.positionSize(symbol, price, risk, 'SHORT')
                                if posSize <= 0: self.deactivateStrategy(symbol, strategy)
                                else:
                                    self.positions[symbol][strategy]['activeOrderId'] = self.worker.validOrderId + 1
                                    self.positions[symbol][strategy]['slPrice'] = self.data[symbol]['daily']['high'][-1] + self.tickSize(price) * SLIPPAGE_IN_TICKS
                                    self.submit_market_order(symbol, posSize, direction='SELL')
                                    self.log('info', 'Submitting MKT order to SHORT {} {}'.format(posSize, symbol))
                                    self.savePositions()

                    if stratdata['state'] == 'initiated' and not activeOrder:
                        if price > stratdata['slPrice']:
                            stratdata['activeOrderId'] = self.worker.validOrderId + 1
                            stratdata['orderInfo'] = 'stoppedOut'
                            self.submit_market_order(symbol, stratdata['slQty'], direction='BUY')
                            self.log('info', 'Stopped out. {} {}@{}'.format(stratdata['slQty'], symbol, price))
                        elif stratdata['tpActive'] and price < stratdata['tpPrice']:
                            stratdata['activeOrderId'] = self.worker.validOrderId + 1
                            stratdata['orderInfo'] = 'tpHit'
                            self.submit_market_order(symbol, stratdata['tpQty'], direction='BUY')
                            self.log('info', 'Reached target. Buying back {} {}@{}'.format(stratdata['tpQty'], symbol, price))

                    if not stratdata['slTrailing'] and price < stratdata['slPrice'] - 2 * (stratdata['slPrice'] - stratdata['vwap']):
                        stratdata['slTrailing'] = True
                        stratdata['slPrice'] = self.roundToNearestTick(stratdata['vwap'] - self.tickSize(price), price)

                    if stratdata['slTrailing'] and stratdata['slPrice'] != self.data[symbol]['1h']['high'][-1]:
                        stratdata['slPrice'] = min(stratdata['slPrice'], self.data[symbol]['1h']['high'][-1])


                    if self.positions[symbol][strategy]['lastPrice'] == -1: self.positions[symbol][strategy]['lastPrice'] = price


        if self.data[symbol]['meta']['firstEverTick']: self.data[symbol]['meta']['firstEverTick'] = False




        """
        s = self.data[symbol]['30min']
        print('Date: {} Open: {} High: {} Low: {} Close: {}'.format(
            s['datetime'][-1],
            s['open'][-1],
            s['high'][-1],
            s['low'][-1],
            s['close'][-1]
        ))
        """

    def tickSize(self, price):
        return .01 if price > 1. else .0001
    
    def roundToNearestTick(self, value, price):
        return round(value, int(math.log10(self.tickSize(price)**-1)))

    def positionSize(self, symbol, price, risk, action):
        if self.accountInfo['AvailableFunds']['value'] == 'N/A':
            self.log('error', 'Missing account information')
            return -1
        availableFunds = float(self.accountInfo['AvailableFunds']['value'])

        posSizeRiskBased = math.floor(self.portfolio[symbol]['pos_size'] / risk)

        maxPosSize = self.maxStockPosition(availableFunds, action, price)
        posSize = min(posSizeRiskBased, maxPosSize)
        if posSizeRiskBased > maxPosSize and posSize != 0: self.log('info', 'Position size reduced to comply with regulatory margin requirements')
        if posSize == 0: self.log('info', 'Insufficient funds. {} {} {}@{}'.format(
            action, posSizeRiskBased, symbol, price
        ))
        if posSize < 0:
            posSize = 0
            self.log('error', 'Negative pos size. {} {}@{} {}@risk'.format(
                action, symbol, price, risk
            ))
        return posSize

    def maxStockPosition(self, funds, action, price):
        maxPos = 0
        if action == 'BUY':
            coeff = 1 if funds <= 2000 else 2
            maxPos = coeff * funds / price
        elif action == 'SHORT':
            if price > 16.67:
                maxPos = (funds/price)/.3
            elif price > 5. and price <= 16.67:
                maxPos = funds/5.
            elif price > 2.5 and price <= 5.:
                maxPos = funds/price
            else:
                maxPos = funds/2.5
        maxPos = math.floor(maxPos)
        return maxPos

    def resetStratInfo(self, symbol, strategy):
        self.positions[symbol][strategy] = deepcopy(STRATEGY_INFO)

    def deactivateStrategy(self, symbol, strategy, savePositions = True):
        if symbol not in self.positions.keys() or symbol not in self.portfolio.keys():
            self.log('error', 'Symbol {} is not being tracked'.format(symbol))
            return
        if strategy not in self.positions[symbol].keys():
            self.log('error', 'Unknown strategy {} for symbol {}'.format(strategy, symbol))
            return
        self.positions[symbol][strategy]['state'] = 'deactivated'
        self.positions[symbol][strategy]['lastPrice'] = -1
        self.portfolio[symbol]['permissions'][strategy] = False
        self.savePortfolio()
        if savePositions: self.savePositions()


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

    def terminateReconnector(self):
        self.reconnectionInProgress = False
        self.reconnectThread.quit()
        self.reconnector.deleteLater()
        self.reconnectThread.deleteLater()


    def reconnect(self):
        self.reconnectionInProgress = True
        # self.connectionEstablished.emit(0)
        self.isConnected = False
        self.log('info', 'Connection lost. Trying to reconnect')

        self.reconnectThread = QThread()
        self.reconnector = Reconnector()
        # self.reconnector.log.connect(self.log, Qt.DirectConnection)
        self.reconnector.reconnectSignal.connect(self.worker.reconnect, Qt.DirectConnection)
        self.reconnector.terminateSelf.connect(self.terminateReconnector, Qt.DirectConnection)
        self.reconnector.moveToThread(self.reconnectThread)
        self.reconnectThread.start()

        self.reconnector.reconnect()

    def isTWSRunning(self):
        return 'java' in [i.name() for i in psutil.process_iter()]


    def showTime(self):
        # Restart if need be
        self.secSinceLastConnCheck += 1
        if self.secSinceLastConnCheck >= self.RESTART_TIMEOUT_SEC:
            self.secSinceLastConnCheck = 0
            if not self.worker.isConnected(): 
                self.connectionEstablished.emit(0)
                self.restartApp.emit()

        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        if t.day != self.lastKnownDay:
            self.getSessionTimesToday(t)
            self.lastKnownDay = t.day
            self.refreshHolidayLabel()
            # self.get_timeframe_marks(default=False)
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

        """
        if self.settings['strategy']['flatten_eod'] and tint > self.maxT and t.weekday() not in [5, 6] and not self.positionsCLosedToday:
            for reqId in list(self.watchlistItems.keys()):
                if self.isConnected: self.close_all_positions(reqId, eod=True)
            self.positionsCLosedToday = True
        """

        self.tint = int(tint/100)
        self.mint = t.minute
        self.time = t

        


    def stop_dash_thread(self):
        return
        # self.dashThread.quit()


    # def open_presets_window(self):
    #     self.presets.show()

    def show_cancel_order_window(self):
        self.orderCancelWindow.orders = deepcopy(self.orders)
        self.orderCancelWindow.repopulate_selector()
        self.orderCancelWindow.show()

    def submit_order_window(self):
        self.submitOrderWindow.show()


    def open_chart_window(self):
        return

        """
        self.chartWindow.quitDash.connect(self.dashWorker.stop)
        self.chartWindow.quitDash.connect(self.dashWorker.deleteLater)
        self.chartWindow.quitDash.connect(self.dashThread.deleteLater)
        """

        self.chartWindow.show_graph()

    """
    def open_explorer_window(self):
        if self.explorerReady:
            if not self.explorerInitiated:
                self.explorer = Explorer(deepcopy(self.symbols), deepcopy(self.preset_data))
                self.explorer.requestData.connect(self.transmitDataToExplorer, Qt.DirectConnection)
                self.data_to_explorer.connect(self.explorer.data_received, Qt.DirectConnection)
                self.explorerInitiated = True
            self.explorer.show()
        else: msgBox = InfoMessageBox('Info', 'Data Explorer is not yet ready\n\nPlease try again later\n')
    """

    def show_equity_window(self):
        self.equityPlot._plot(deepcopy(self.cumEquity))
        self.equityPlot.show()

    def show_quick_chart(self):
        self.qChart.show()
        

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
        return
        # print("\n")
        # for currentQTableWidgetItem in self.tableWidget.selectedItems():
        #     print(currentQTableWidgetItem.row(), currentQTableWidgetItem.column(), currentQTableWidgetItem.text())

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
            self.searchWindow.sendContractToWatchlist.connect(self.addToWatchlistFromSearch, Qt.DirectConnection)
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

            self.searchWindow.symInfo = QLabel("QTrader")
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



        # self.title = QLabel("QTrader")
        # self.title.setAlignment(Qt.AlignCenter)
        # self.title.setStyleSheet("QLabel {font-weight: bold; color: black; font-size: 18px;}")
        # layout.addWidget(self.title)


    """
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
    """



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

    def worker_reconnected(self):
        print('Worker connection established')
        if self.worker.isConnected():
            self.isConnected = True
            # self.connectionEstablished.emit(1)

    def worker_connected(self, code):
        if code == 1:
            self.disable_connect_button()
            self.status_message.emit('')
            self.connectionLabel.setText("Status:    connected")
            self.isConnected = True
            self.initialConnectionEstablished = True
            self.connectionEstablished.emit(1)
            self.connTimeout = 1.
            self.downloader.initiate()
            self.lastHistoricalDataRequest = datetime.now()
            if self.settings['account']['delayed_quotes']: self.worker.reqMarketDataType(3)
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
            # self.status_message.emit('Critical error. Restart the application.')
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


    def commission_update(self, orderID, commission):
        if orderID in self.pending_orders and commission < 10**6:
            orderData = self.pending_orders[orderID]
            orderData['commissions'] = commission

    def account_info_update(self, key, value, currency, account):
        if key in self.accountInfoList:
            row = self.accountInfoList.index(key)
            self.accountInfo[key]['value'] = value
            w_item = QTableWidgetItem( str(value) )
            w_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if row%2 == 1: w_item.setBackground(QColor(74, 105, 135))
            self.accountTable.setItem(row, 1, w_item)


    def position_update(self, symbol, exchange, position, marketPrice, averageCost, marketValue, unrealizedPNL, realizedPNL, accountName):
        sym = symbol.upper()
        marketPrice = round(marketPrice, 3)
        averageCost = round(averageCost, 4)
        if sym in list(self.accPositions.keys()):
            if realizedPNL != self.accPositions[sym]['realizedPnL']:
                pnl = realizedPNL - self.accPositions[sym]['realizedPnL']
                
                t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
                qty = float(abs(position-self.accPositions[sym]['position']))
                if (position > 0 and self.accPositions[sym]['position'] < 0) or (position < 0 and self.accPositions[sym]['position'] > 0):
                    qty = self.accPositions[sym]['position']
                item = (sym, t.strftime('%Y-%m-%d %H:%M:%S'),
                        float(marketPrice), qty, float(round(pnl, 2)))

                with sqlite3.connect(self.DB_PATH) as con:
                    cur = con.cursor()
                    cur.execute("BEGIN TRANSACTION;")
                    sql = ''' INSERT INTO equity(ticker,datetime,mktprice,qty,pnl)
                                      VALUES(?,?,?,?,?) '''
                    cur.execute(sql, item)
                    cur.execute("COMMIT;")
                    cur.close()

                row = 0
                self.equityTable.insertRow(row)
                self.equityTable.setItem(row, 0, QTableWidgetItem(item[0]))
                self.equityTable.item(row, 0).setForeground(QColor(243, 156, 18))
                self.equityTable.item(row, 0).setFont(self.symbolFont)
                self.equityTable.setItem(row, 1, QTableWidgetItem(item[1][:10]))
                self.equityTable.setItem(row, 2, QTableWidgetItem(item[1][11:]))
                self.equityTable.setItem(row, 3, QTableWidgetItem(str(item[2])))
                self.equityTable.setItem(row, 4, QTableWidgetItem(str(item[3])))
                self.equityTable.setItem(row, 5, QTableWidgetItem( ''.join(['$', str(round(item[4], 2))]) ))
                c = QColor(0, 230, 118) if float(item[4]) >= .0 else QColor(255, 82, 82)
                self.equityTable.item(row, 5).setForeground(c)
                # self.equityTable.item(row, 5).setFont(self.symbolFont)
                self.equity.append(item[4])
                self.cumEquity.append(self.cumEquity[-1]+item[4])


            row = list(self.accPositions.keys()).index(sym)
            self.accPositions[sym]['position'] = position
            self.positionsTable.item(row, 2).setText(str(position))
            self.accPositions[sym]['mktPrice'] = marketPrice
            self.positionsTable.item(row, 3).setText(str(marketPrice))
            self.accPositions[sym]['VWAP'] = averageCost
            self.positionsTable.item(row, 4).setText(str(averageCost))
            self.accPositions[sym]['mktValue'] = marketValue
            self.positionsTable.item(row, 5).setText(str(marketValue))
            self.accPositions[sym]['unrealizedPnL'] = unrealizedPNL
            self.positionsTable.item(row, 6).setText(str(unrealizedPNL))
            self.accPositions[sym]['realizedPnL'] = realizedPNL
            self.positionsTable.item(row, 7).setText(str(realizedPNL))
            if unrealizedPNL != .0:
                c = QColor(1, 99, 52) if unrealizedPNL >= .0 else QColor(133, 41, 41)
                for j in range(self.positionsTable.columnCount()):
                    self.positionsTable.item(row, j).setBackground(c)
            elif position == 0:
                for j in range(self.positionsTable.columnCount()):
                    self.positionsTable.item(row, j).setBackground(QColor(44, 62, 80))

            

        else:
            self.accPositions[sym] = deepcopy(self.POS_TEMPLATE)
            self.accPositions[sym]['exchange'] = exchange
            self.accPositions[sym]['position'] = position
            self.accPositions[sym]['mktPrice'] = marketPrice
            self.accPositions[sym]['VWAP'] = averageCost
            self.accPositions[sym]['mktValue'] = marketValue
            self.accPositions[sym]['unrealizedPnL'] = unrealizedPNL
            self.accPositions[sym]['realizedPnL'] = realizedPNL
            self.accPositions[sym]['account'] = accountName

            row = self.positionsTable.rowCount()
            self.positionsTable.insertRow(row)
            self.positionsTable.setItem(row, 0, QTableWidgetItem(str(sym)))
            self.positionsTable.item(row, 0).setFont(self.symbolFont)
            self.positionsTable.item(row, 0).setForeground(QBrush(QColor(243, 156, 18)))
            self.positionsTable.setItem(row, 1, QTableWidgetItem(str(exchange)))
            self.positionsTable.setItem(row, 2, QTableWidgetItem(str(position)))
            self.positionsTable.setItem(row, 3, QTableWidgetItem(str(marketPrice)))
            self.positionsTable.setItem(row, 4, QTableWidgetItem(str(averageCost)))
            self.positionsTable.setItem(row, 5, QTableWidgetItem(str(marketValue)))
            self.positionsTable.setItem(row, 6, QTableWidgetItem(str(unrealizedPNL)))
            self.positionsTable.setItem(row, 7, QTableWidgetItem(str(realizedPNL)))
            self.positionsTable.setItem(row, 8, QTableWidgetItem(str(accountName)))

            if unrealizedPNL != .0:
                c = QColor(1, 99, 52) if unrealizedPNL > .0 else QColor(133, 41, 41)
                for j in range(self.positionsTable.columnCount()):
                    self.positionsTable.item(row, j).setBackground(c)
        
        symbol_in_portfolio = False
        for reqId in self.watchlist.keys():
            if self.watchlist[reqId].contract.symbol == symbol:
                symbol_in_portfolio = True
                break
        if symbol_in_portfolio:
            self.watchlistItems[reqId]._position.setText(str( int(position) ))
            self.watchlistItems[reqId]._margin.setText(str( round(marketValue, 2) if position != .0 else 0 ))
            stylesheet = "QLabel{color:#00E676;}" if position > 0 else 'QLabel{color: #ff5252;}'
            if position == 0: stylesheet = "QLabel{color:#777777;}"
            self.watchlistItems[reqId]._position.setStyleSheet(stylesheet)
            self.watchlistItems[reqId]._margin.setStyleSheet(stylesheet)


    """
    def order_status_update_old(self, orderID, remaining, VWAP):

        if remaining == 0 and orderID in list(self.pending_orders.keys()):
            orderData = self.pending_orders[orderID]
            self.watchlistItems[orderData['reqId']].positionChanged(orderData['pos_change'])
            i = 0
            for key in list(self.positions[orderData['symbol']]['positions'].keys()):
                self.positions[orderData['symbol']]['positions'][key] += orderData['adjustments'][i]
                i += 1
            self.savePositions()


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
                    self.trades_old.append(tradeInfo)

                    rowPosition = self.tradesTable_old.rowCount()
                    self.tradesTable_old.insertRow(rowPosition)
                    pos = 0
                    for _item in tradeInfo:
                        self.tradesTable_old.setItem(rowPosition, pos, QTableWidgetItem( str(_item) ))
                        pos += 1

            self.pending_orders.pop(orderID, None)

        return
    """

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

    """
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
            # self.nStocks -= 1
            del self.symbols[n]
        else:
            for key in self.positions[self.symbols[n]]['positions'].keys():
                self.positions[self.symbols[n]]['positions'][key] = 0
        self.savePositions()
    """


    """
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
    """

    def transmitDataToExplorer(self):
        self.data_to_explorer.emit(self.reportDT, self.reportCloses, self.reportSignals)


    def downloader_finished(self, success, timestamps, closes):
        self.historicalDataReady = True
        # print("First: {}, Last: {}".format(timestamps[0][-1], timestamps[0][0]))
        if len(self.watchlist) > 0:
            # self.data_transform(success, timestamps, closes)
            self.enable_start_button()
        # else:
        #     msgBox = InfoMessageBox('Error', 'Data transform error')

    def receive_valid_id(self, id):
        self.orderID = id

    def databarReceived(self, symbol, bar):
        if symbol not in self.data:
            self.data[symbol] = {}
            template = {'datetime': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
            self.data[symbol]['30min'] = deepcopy(template)
            self.data[symbol]['1h'] = deepcopy(template)
            self.data[symbol]['daily'] = deepcopy(template)

        dt = bar.date[:17]
        s = self.data[symbol]['30min']
        s['datetime'].append(parser.parse(dt))
        s['open'].append(bar.open)
        s['high'].append(bar.high)
        s['low'].append(bar.low)
        s['close'].append(bar.close)
        s['volume'].append(int(bar.volume))

    
    def databarsEnded(self, symbol):
        if symbol not in self.data: return
        item = None
        for key in self.watchlistItems.keys():
            if self.watchlistItems[key].symbol.upper() == symbol.upper():
                item = self.watchlistItems[key]
                break
        if item == None: return
        item._history.setText('Ready')
        item._history.setStyleSheet("QLabel{color:#00E676; font-weight: normal;}")
        self.create_secondary_dataseries(symbol)
        self.adjust_execution_label(symbol)
        self.worker.subscribeToStreamingData(key, self.watchlist[key])


    def dttointmark(self, dt):
        return(dt.hour*100 + dt.minute)
    
    def create_secondary_dataseries(self, symbol):
        if self.data[symbol]['30min']['datetime'] == []: return
        self.data[symbol]['1h'] = {'datetime': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        [cd, co, ch, cl, cc, cv] =    [ self.data[symbol]['30min']['datetime'][0],
                                        self.data[symbol]['30min']['open'][0],
                                        self.data[symbol]['30min']['high'][0],
                                        self.data[symbol]['30min']['low'][0],
                                        self.data[symbol]['30min']['close'][0],
                                        self.data[symbol]['30min']['volume'][0]]

        for n in range(1, len(self.data[symbol]['30min']['datetime'])):
            if self.dttointmark(self.data[symbol]['30min']['datetime'][n]) in self.TFMARKS1H:
                self.data[symbol]['1h']['datetime'].append(cd)
                self.data[symbol]['1h']['open'].append(co)
                self.data[symbol]['1h']['high'].append(ch)
                self.data[symbol]['1h']['low'].append(cl)
                self.data[symbol]['1h']['close'].append(cc)
                self.data[symbol]['1h']['volume'].append(cv)
                [cd, co, ch, cl, cc, cv] =    [ self.data[symbol]['30min']['datetime'][n],
                                                self.data[symbol]['30min']['open'][n],
                                                self.data[symbol]['30min']['high'][n],
                                                self.data[symbol]['30min']['low'][n],
                                                self.data[symbol]['30min']['close'][n],
                                                self.data[symbol]['30min']['volume'][n]]        
            else:
                ch = max(ch, self.data[symbol]['30min']['high'][n])
                cl = min(cl, self.data[symbol]['30min']['low'][n])
                cc = self.data[symbol]['30min']['close'][n]
                cv += self.data[symbol]['30min']['volume'][n]
            
        self.data[symbol]['1h']['datetime'].append(cd)
        self.data[symbol]['1h']['open'].append(co)
        self.data[symbol]['1h']['high'].append(ch)
        self.data[symbol]['1h']['low'].append(cl)
        self.data[symbol]['1h']['close'].append(cc)
        self.data[symbol]['1h']['volume'].append(cv)

        self.data[symbol]['daily'] = {'datetime': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        [cd, co, ch, cl, cc, cv] =    [ self.data[symbol]['30min']['datetime'][0],
                                        self.data[symbol]['30min']['open'][0],
                                        self.data[symbol]['30min']['high'][0],
                                        self.data[symbol]['30min']['low'][0],
                                        self.data[symbol]['30min']['close'][0],
                                        self.data[symbol]['30min']['volume'][0]]
        
        for n in range(1, len(self.data[symbol]['30min']['datetime'])):
            if self.data[symbol]['30min']['datetime'][n].day != self.data[symbol]['30min']['datetime'][n-1].day:
                self.data[symbol]['daily']['datetime'].append(cd)
                self.data[symbol]['daily']['open'].append(co)
                self.data[symbol]['daily']['high'].append(ch)
                self.data[symbol]['daily']['low'].append(cl)
                self.data[symbol]['daily']['close'].append(cc)
                self.data[symbol]['daily']['volume'].append(cv)
                [cd, co, ch, cl, cc, cv] =    [ self.data[symbol]['30min']['datetime'][n],
                                                self.data[symbol]['30min']['open'][n],
                                                self.data[symbol]['30min']['high'][n],
                                                self.data[symbol]['30min']['low'][n],
                                                self.data[symbol]['30min']['close'][n],
                                                self.data[symbol]['30min']['volume'][n]]
            else:
                ch = max(ch, self.data[symbol]['30min']['high'][n])
                cl = min(cl, self.data[symbol]['30min']['low'][n])
                cc = self.data[symbol]['30min']['close'][n]
                cv += self.data[symbol]['30min']['volume'][n]

        self.data[symbol]['daily']['datetime'].append(cd)
        self.data[symbol]['daily']['open'].append(co)
        self.data[symbol]['daily']['high'].append(ch)
        self.data[symbol]['daily']['low'].append(cl)
        self.data[symbol]['daily']['close'].append(cc)
        self.data[symbol]['daily']['volume'].append(cv)

        self.data[symbol]['meta'] = {
            'openingTick': False,
            'firstEverTick': True
        }


    def adjust_execution_label(self, symbol):
        if symbol in self.portfolio.keys():
                executing = False
                for _, val in self.portfolio[symbol]['permissions'].items():
                    if type(val) == bool and val: executing = True
                for reqId in self.watchlistItems.keys():
                    if symbol.upper() == self.watchlistItems[reqId].symbol.upper():
                        if executing:
                            self.watchlistItems[reqId]._execution.setText("On")
                            self.watchlistItems[reqId]._execution.setStyleSheet("QLabel{color:#00E676;}")
                        else:
                            self.watchlistItems[reqId]._execution.setText("Off")
                            self.watchlistItems[reqId]._execution.setStyleSheet("QLabel{color:#ff5252;}")
                        break

    def receive_all_data_from_downloader(self, data):
        for symbol in data.keys():
            self.data[symbol] = {}
            self.data[symbol]['30min'] = deepcopy(data[symbol])
            for key in self.data[symbol]['30min'].keys(): self.data[symbol]['30min'][key].reverse()
        
        for symbol in self.data.keys():
            self.create_secondary_dataseries(symbol)
            self.adjust_execution_label(symbol)
        
        self.subscribe_to_all_streaming.emit()

    



    def open_order_received(self, orderId, contract, order, orderState):
        permId = int(order.permId)
        if permId not in list(self.orders.keys()):
            self.orders[permId] = deepcopy(self.ORDER_PRESET)

            self.orders[permId]['symbol'] = contract.symbol.upper()
            self.orders[permId]['exchange'] = contract.exchange
            self.orders[permId]['action'] = order.action
            self.orders[permId]['type'] = order.orderType
            self.orders[permId]['qty'] = order.totalQuantity
            self.orders[permId]['limit'] = order.lmtPrice
            self.orders[permId]['stop'] = order.auxPrice
            self.orders[permId]['status'] = orderState.status
            self.orders[permId]['filled'] = 0
            self.orders[permId]['remaining'] = order.totalQuantity
            self.orders[permId]['avgfillprice'] = 'N/A'
            self.orders[permId]['orderId'] = orderId
            self.orders[permId]['permId'] = order.permId
            self.orders[permId]['TIF'] = order.tif
            self.orders[permId]['secType'] = contract.secType
            self.orders[permId]['tradeReported'] = False

            row = self.ordersTable.rowCount()
            self.ordersTable.insertRow(row)
            self.ordersTable.setItem(row, 0, QTableWidgetItem(str(self.orders[permId]['symbol'])))
            self.ordersTable.item(row, 0).setForeground(QColor(243, 156, 18))
            self.ordersTable.item(row, 0).setFont(self.symbolFont)
            self.ordersTable.setItem(row, 1, QTableWidgetItem(str(self.orders[permId]['exchange'])))
            self.ordersTable.setItem(row, 2, QTableWidgetItem(str(self.orders[permId]['action'])))
            self.ordersTable.setItem(row, 3, QTableWidgetItem(str(self.orders[permId]['type'])))
            if str(self.orders[permId]['action']) == 'SELL':
                self.ordersTable.item(row, 2).setBackground(QColor(133, 41, 41))
            else:
                self.ordersTable.item(row, 2).setBackground(QColor(1, 99, 52))
            self.ordersTable.setItem(row, 4, QTableWidgetItem(str(self.orders[permId]['qty'])))
            self.ordersTable.setItem(row, 5, QTableWidgetItem(str(self.orders[permId]['limit'])))
            self.ordersTable.setItem(row, 6, QTableWidgetItem(str(self.orders[permId]['stop'])))
            self.ordersTable.setItem(row, 7, QTableWidgetItem(str(self.orders[permId]['status'])))
            self.ordersTable.setItem(row, 8, QTableWidgetItem(str(self.orders[permId]['filled'])))
            self.ordersTable.setItem(row, 9, QTableWidgetItem(str(self.orders[permId]['remaining'])))
            self.ordersTable.setItem(row, 10, QTableWidgetItem(str(self.orders[permId]['avgfillprice'])))
            self.ordersTable.setItem(row, 11, QTableWidgetItem(str(self.orders[permId]['TIF'])))
            self.ordersTable.setItem(row, 12, QTableWidgetItem(str(self.orders[permId]['orderId'])))
            self.ordersTable.setItem(row, 13, QTableWidgetItem(str(self.orders[permId]['permId'])))

            # self.orderCancelWindow.orders = self.orders
            # self.orderCancelWindow.repopulate_selector()


    def order_status_update(self, orderId:int, status:str, filled:float, remaining:float, 
                            avgFillPrice:float, permId:int):
        if permId in list(self.orders.keys()):
            self.orders[permId]['status'] = status
            self.orders[permId]['filled'] = filled
            self.orders[permId]['remaining'] = remaining
            self.orders[permId]['avgfillprice'] = avgFillPrice

            row = list(self.orders.keys()).index(permId)
            self.ordersTable.item(row, 7).setText(status)
            self.ordersTable.item(row, 8).setText(str(filled))
            self.ordersTable.item(row, 9).setText(str(remaining))
            self.ordersTable.item(row, 10).setText(str(avgFillPrice))

            bg_c, fg_c = QColor(44, 62, 80), QColor(238, 238, 238)
            if status == 'PreSubmitted':
                bg_c, fg_c = QColor(181, 116, 13), QColor(15, 15, 15)
            elif status == 'Submitted':
                bg_c = QColor(1, 99, 52)
            elif status == 'Filled':
                bg_c, fg_c = QColor(190, 190, 190), QColor(15, 15, 15)
            elif status == 'Cancelled':
                bg_c = QColor(60, 60, 60)
            self.ordersTable.item(row, 7).setBackground(QColor(bg_c))
            self.ordersTable.item(row, 7).setForeground(QColor(fg_c))

            if remaining == .0 or status == 'Cancelled': 
                self.ordersTable.item(row, 2).setBackground(QColor(44, 62, 80))
                self.orderCancelWindow.repopulate_selector()

            if status == 'Filled' and remaining == .0 and not self.orders[permId]['tradeReported']:
                    o = self.orders[permId]
                    t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
                    trade = (o['symbol'], o['secType'], t.strftime('%Y-%m-%d %H:%M:%S'),
                             o['action'], float(o['qty']), float(o['avgfillprice']),'')
                    con = sqlite3.connect(self.DB_PATH)
                    cur = con.cursor()
                    cur.execute("BEGIN TRANSACTION;")
                    sql = ''' INSERT INTO trades(ticker,sectype,datetime,action,qty,fill,pnl)
                                      VALUES(?,?,?,?,?,?,?) '''
                    cur.execute(sql, trade)
                    cur.execute("COMMIT;")
                    cur.close()

                    row = 0
                    self.tradesTable.insertRow(row)
                    self.tradesTable.setItem(row, 0, QTableWidgetItem(trade[0]))
                    self.tradesTable.item(row, 0).setForeground(QColor(243, 156, 18))
                    self.tradesTable.item(row, 0).setFont(self.symbolFont)
                    self.tradesTable.setItem(row, 1, QTableWidgetItem(trade[2][:10]))
                    self.tradesTable.setItem(row, 2, QTableWidgetItem(trade[2][11:]))
                    self.tradesTable.setItem(row, 3, QTableWidgetItem(trade[3]))
                    if trade[3] == 'BUY':
                        self.tradesTable.item(row, 3).setForeground(QColor(0, 230, 118))
                    else: self.tradesTable.item(row, 3).setForeground(QColor(255, 82, 82))
                    # self.tradesTable.item(row, 3).setFont(self.symbolFont)
                    self.tradesTable.setItem(row, 4, QTableWidgetItem(str(trade[4])))
                    self.tradesTable.setItem(row, 5, QTableWidgetItem(str(trade[5])))

                    found = False
                    for symbol, strats in self.positions.items():
                        if found: break
                        for name, strat in strats.items():
                            if strat['activeOrderId'] == orderId:
                                if strat['state'] == 'activated':
                                    strat['slActive'] = True
                                    strat['slQty'] = int(filled)
                                    strat['state'] = 'initiated'
                                    strat['vwap'] = avgFillPrice
                                    strat['tpActive'] = True
                                    strat['position'] = int(filled)
                                    strat['activeOrderId'] = -1
                                    strat['tpQty'] = math.ceil(filled/2)
                                    strat['tpPrice'] = self.roundToNearestTick(strat['slPrice'] + 3 * (avgFillPrice - strat['slPrice']), avgFillPrice)
                                elif strat['state'] == 'initiated':
                                    if strat['orderInfo'] == 'stoppedOut':
                                        self.resetStratInfo(symbol, name)
                                        self.deactivateStrategy(symbol, name, savePositions=False)
                                    elif strat['orderInfo'] == 'tpHit':
                                        strat['tpActive'] = False
                                        strat['tpQty'] = 0
                                        strat['tpPrice'] = .0
                                        strat['position'] -= int(filled)
                                        strat['slQty'] -= int(filled)
                                        strat['activeOrderId'] = -1 
                                self.savePositions()
                                found = True
                                break

                    self.orders[permId]['tradeReported'] = True
        


    @pyqtSlot()
    def establish_connection(self):
        self.subscribe()
        self.disable_connect_button()
        self.log('info', 'Establishing API connection')
        self.status_message.emit('Establishing connection')
        self.idleThread = QThread()
        self.thread = QThread()
        self.worker = API()
        # self.worker.clientID = self.clientID()
        self.symInfoRequested.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.signalEmitted.connect(self.readWorkerSignal, Qt.DirectConnection)
        self.worker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.worker.reconnected.connect(self.worker_reconnected, Qt.DirectConnection)
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
        self.downloader.transmitDataToMain.connect(self.receive_all_data_from_downloader, Qt.DirectConnection)
        self.subscribe_to_all_streaming.connect(self.downloader.subscribe_to_all_streaming, Qt.DirectConnection)

        self.transmit_order.connect(self.worker.placeOrder, Qt.DirectConnection)
        self.worker.transmit_order_status.connect(self.order_status_update, Qt.DirectConnection)
        self.worker.transmit_commission.connect(self.commission_update, Qt.DirectConnection)
        self.worker.transmit_valid_id.connect(self.receive_valid_id, Qt.DirectConnection)
        self.worker.transmit_account_info.connect(self.account_info_update, Qt.DirectConnection)
        self.worker.transmit_position.connect(self.position_update, Qt.DirectConnection)
        self.worker.transmit_open_order.connect(self.open_order_received, Qt.DirectConnection)
        self.worker.tramsmitDataToMain.connect(self.databarReceived, Qt.DirectConnection)
        self.worker.tellMainDataEnded.connect(self.databarsEnded, Qt.DirectConnection)
        self.tell_worker_to_cancel_order.connect(self.worker.cancel_order, Qt.DirectConnection)
        

        # Autocomplete
        # self.w._model.dataRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        # self.worker.toAutocompleter.connect(self.w._model.dataReceived, Qt.DirectConnection)

        # Connection query
        # self.chartWindow.amIConnected.connect(self.worker.connectionStatus, Qt.DirectConnection)
        # self.worker.amIConnected.connect(self.chartWindow.updateConnectionStatus, Qt.DirectConnection)

        self.submitOrderWindow.amIConnected.connect(self.worker.connectionStatusOrder, Qt.DirectConnection)
        self.worker.amIConnectedOrder.connect(self.submitOrderWindow.updateConnectionStatus, Qt.DirectConnection)

        # Matching symbols (source=chart)
        # self.chartWindow.lookupRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        # self.worker.symInfoToChart.connect(self.chartWindow.lookupResultsReceived, Qt.DirectConnection)
        # self.chartWindow.requestHistData.connect(self.worker.getHistData, Qt.DirectConnection)
        # self.worker.sendHistDataToChart.connect(self.chartWindow.newDataReceived, Qt.DirectConnection)

        # Matching symbols (source=order)
        self.submitOrderWindow.lookupRequest.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.symInfoToOrder.connect(self.submitOrderWindow.lookupResultsReceived, Qt.DirectConnection)

        self.submitOrderWindow.submit_order.connect(self.worker.submit_order, Qt.DirectConnection)

        self.worker.tick.connect(self.tick, Qt.DirectConnection)

        self.worker.moveToThread(self.thread)


        self.thread.started.connect(self.worker.connect)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)

        self.worker.adjust_connection_settings(self.settings['connection']['port'], self.settings['connection']['clientId'], self.settings['account']['accountId'])
        self.thread.start()
        # self.worker.initiate()

        self.thread.finished.connect(
            lambda: self.enable_connect_button()
        )
        self.thread.finished.connect(
            lambda: self.connectionLabel.setText("Status: disconnected")
        )
        self.thread.finished.connect(
            lambda: print('THREAD FINISHED')
        )
        

def tracer(frame, event, arg = None):
    code = frame.f_code
    func_name = code.co_name
    line_no = frame.f_lineno
    # print(f"A {event} encountered in {func_name}() at line number {line_no} ") 
    
    return tracer 

def restart(): 
    os.execv(sys.executable, ['python'] + sys.argv)

def printsignal(_signal): 
    print(f"Received signal: {_signal}")

def sigint_handler(_signal, frame):
    printsignal(_signal)
    restart()

def sigabrt_handler(_signal, frame):
    printsignal(_signal)
    restart()
    
def sigsegv_handler(_signal, frame):
    printsignal(_signal)
    restart()

def sigpipe_handler(_signal, frame):
    printsignal(_signal)
    restart()


if __name__ == '__main__':
    threading.settrace(tracer)
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGABRT, sigabrt_handler)
    signal.signal(signal.SIGSEGV, sigsegv_handler)
    signal.signal(signal.SIGPIPE, sigpipe_handler)
    
    path = os.path.dirname(os.path.abspath(__file__))
    app = QApplication(sys.argv)
    with open('{}/{}'.format(path, 'style.qss'), 'r') as f:
        style = f.read()
    app.setStyleSheet(style)
    ex = App()
    sys.exit(app.exec_())
