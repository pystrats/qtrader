import sys, time, threading, os, random
import threading
from datetime import datetime, timedelta
import dateutil.parser as parser
import json

import requests

from PyQt5.QtWidgets import (QMainWindow, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QHBoxLayout,
            QLineEdit, QInputDialog, QLabel, QTableWidget, QTableWidgetItem, QGridLayout, QMessageBox, QStatusBar, QDesktopWidget,
            QScrollArea, QShortcut, QAbstractButton, QDialogButtonBox, QFrame, QFileDialog)
from PyQt5.QtGui import QIcon, QIntValidator, QFont, QPalette, QColor, QKeySequence, QCloseEvent, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSlot, QObject, QThread, pyqtSignal, QTimer, QTime

import dash
from dash import dcc, html

from connection import Trader, Connection
from chart import Chart
from dashworker import DashWorker
from completer import LineCompleterWidget
from search import SearchWindow
from msgboxes import InfoMessageBox, InfoWidget
from watchlistitem import WatchlistItem

from ibapi.contract import Contract


class App(QMainWindow):

    closeSignal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.title = 'QuantTrader'
        self.left = 10
        self.top = 10
        self.width = 1280
        self.height = 720
        self.showExitDialogue = True
        self.exitDialogueShown = False
        self.maximizeOnStartup = False
        self.setWindowTitle(self.title)

        self.setGeometry(self.left, self.top, self.width, self.height)

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')
        watchlistMenu = mainMenu.addMenu('Watchlist')
        viewMenu = mainMenu.addMenu('View')
        searchMenu = mainMenu.addMenu('Search')
        toolsMenu = mainMenu.addMenu('Tools')
        helpMenu = mainMenu.addMenu('Help')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)


        settingsButton = QAction(QIcon('exit24.png'), 'Settings', self)
        settingsButton.setShortcut('Ctrl+S')
        settingsButton.setStatusTip('Settings')
        settingsButton.triggered.connect(self.show_new_window)
        fileMenu.addAction(settingsButton)

        exportWatchlistButton = QAction(QIcon(), 'Export Watchlist', self)
        exportWatchlistButton.setShortcut('Ctrl+E')
        exportWatchlistButton.setStatusTip('Export Watchlist')
        exportWatchlistButton.triggered.connect(self.export_watchlist)
        watchlistMenu.addAction(exportWatchlistButton)


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

        self.statusMsgHolder.addWidget(self.statusBarConnectionMsg, alignment=Qt.AlignVCenter)
        self.statusMsgHolder.addWidget(self.connectionCircle, alignment=Qt.AlignVCenter)
        self.statusMsgHolderWidget.setLayout(self.statusMsgHolder)

        self.status = QLabel('', self)
        self.status.setAlignment(Qt.AlignRight)

        self.statusBar.addWidget(self.statusMsgHolderWidget)
        self.statusBar.addPermanentWidget(self.status)

        self.table_widget = TableWidget(self)
        self.table_widget.connectionEstablished.connect(self.on_connection_changed, Qt.DirectConnection)
        self.table_widget.status_message.connect(self.status_message, Qt.DirectConnection)
        self.setCentralWidget(self.table_widget)

        self.closeSignal.connect(self.close)

        if self.maximizeOnStartup: self.showMaximized()

        # View
        chartButton = QAction(QIcon(), 'Chart Window', self)
        chartButton.setShortcut('Ctrl+Shift+C')
        chartButton.setStatusTip('Open chart window')
        chartButton.triggered.connect(self.table_widget.open_chart_window)
        viewMenu.addAction(chartButton)

        self.show()

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
            "Save File", "watchlist.json", "All Files(*);;JSON Files(*.json)", options = options)
        if fileName:
            with open(fileName, 'w') as f:
                f.write(self.watchlistToJSON(self.table_widget.watchlist))
            self.fileName = fileName
            # self.setWindowTitle(str(os.path.basename(fileName)) + " - Notepad Alpha[*]")

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

    def show_new_window(self):
        print("Showing new window")
        self.w = AnotherWindow()
        self.w.show()

    def show_about_window(self):
        self.about = AboutWindow()
        self.about.show()

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
        self.title.setStyleSheet("QLabel {font-weight: bold; color: black; font-size: 18px;}")
        layout.addWidget(self.title)

        self.version = QLabel("Version: 1.00.000")
        self.version.setAlignment(Qt.AlignCenter)
        self.version.setStyleSheet("QLabel {color: black; font-size: 15px;}")
        layout.addWidget(self.version)

        self.releaseDate = QLabel("Release date: May 6, 2023")
        self.releaseDate.setAlignment(Qt.AlignCenter)
        self.releaseDate.setStyleSheet("QLabel {color: black; font-size: 15px;}")
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


class Empty(QWidget):

    def __init__(self, color):
        super(Empty, self).__init__()
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)


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

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        if errorCode == 502:
            self.emit_error.emit(errorCode, errorString)
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
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
        dtFormat = '%Y%m%d' if self.period in ['daily', 'weekly'] else '%Y%m%d %H:%M:%S'
        if self.period in ['30min', '5min']: dtFormat = '%Y%m%d %H:%M:%S.%f'
        dt = bar.date if self.period in ['daily', 'weekly'] else bar.date[:17]
        self.histData[reqId]['Date'].append( parser.parse(dt) )
        self.histData[reqId]['Open'].append(bar.open)
        self.histData[reqId]['High'].append(bar.high)
        self.histData[reqId]['Low'].append(bar.low)
        self.histData[reqId]['Close'].append(bar.close)
        self.histData[reqId]['Volume'].append(bar.volume)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        self.sendHistDataToChart.emit(self.histData[reqId])
        print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)

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

    def cancelStreamingData(self, reqId):
        self.cancelMktData(reqId)

    def tickPrice(self, reqId, tickType, price: float, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        print("TickPrice. TickerId:", reqId, "tickType:", tickType,
                    "Price:", price, "CanAutoExecute:", attrib.canAutoExecute,
                    "PastLimit:", attrib.pastLimit)
        self.tick.emit(reqId, tickType, price)
        # if tickType == TickTypeEnum.BID or tickType == TickTypeEnum.ASK:
        #     print("PreOpen:", attrib.preOpen)
        # else:
        #     print()



class PortfolioMember(QHBoxLayout):
    def __init__(self):
        super().__init__()

        self.label = QLabel("AAPL")
        self.addWidget(self.label)


class CustomQLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)




class TableWidget(QWidget):

    symInfoRequested = pyqtSignal(str, int)
    connectionEstablished = pyqtSignal(int)
    status_message = pyqtSignal(str)

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.isConnected = False
        self.worker = None
        self.searchLastRequested = time.time()
        self.searchQuery = ''
        self.streamingDataReqId = 100000
        # c1 = {}
        # c1.contract = Contract()
        # cc1.contract.symbol = 'AAPL'
        # c1.contract.primaryExchange = 'NYSE'
        # c2 = {}
        # c2 = Contract()
        # c2.symbol = 'MSFT'
        # c2.primaryExchange = 'NASDAQ'
        self.watchlist = {}
        self.watchlistItems = {}
        self.layout = QGridLayout(self)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.resize(300,200)



        # Add tabs
        self.tabs.addTab(self.tab1,"Dashboard")
        self.tabs.addTab(self.tab2,"Pending Liquidations")

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
        self.enable_connect_button()

        self.startButton = QPushButton("Start")
        self.startButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.startButton.setEnabled(False)
        self.startButton.clicked.connect(self.start)

        self.stopButton = QPushButton("Stop")
        self.stopButton.setFixedSize(self.defaultButtonWidth,self.defaultButtonHeight)
        self.stopButton.setEnabled(False)

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

        self.connectionLabel = QLabel("Status: disconnected")
        self.connectionLabel.setAlignment(Qt.AlignRight)

        timer = QTimer(self)
        timer.timeout.connect(self.showTime)
        timer.start(1000)

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
        # self.mktStatusWidget.setFixedHeight(28)
        self.mktStatusLayout = QHBoxLayout()
        self.mktStatusLayout.setAlignment(Qt.AlignTop|Qt.AlignRight)
        self.mktStatusLayout.setContentsMargins(0, 5, 0, 0)
        self.mktStatusLabel = QLabel('')
        self.mktStatus = QLabel('')
        self.mktStatusLayout.addWidget(self.mktStatusLabel, alignment=Qt.AlignTop|Qt.AlignRight)
        # self.mktStatusLayout.addWidget(self.mktStatus, alignment=Qt.AlignTop|Qt.AlignRight)
        self.mktStatusWidget.setLayout(self.mktStatusLayout)
        self.mktState = 0
        self.prevMktState = -1


        self.tab1.layout.addLayout(self.buttonPanel, 0, 3, alignment=Qt.AlignRight)
        self.tab1.layout.addWidget(self.symbolSerachText, 0, 0)
        self.tab1.layout.addWidget(self.searchButton, 0, 1)
        self.tab1.layout.addWidget(self.clock, 1, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        self.tab1.layout.addWidget(self.mktStatusWidget, 2, 3, 1, 1, alignment=Qt.AlignRight|Qt.AlignTop)
        self.tab1.layout.addWidget(self.watchlistWidget, 3, 0, 20, 4, alignment=Qt.AlignTop|Qt.AlignCenter)
        self.tab1.layout.addWidget(Empty('white'), 4, 0, 1, 4)
        # self.tab1.layout.addWidget(self.connectButton, 0, 8, 1, 3)
        # self.tab1.layout.addWidget(self.startButton, 0, 11, 1, 3)
        # self.tab1.layout.addWidget(self.stopButton, 0, 14, 1, 3, alignment=Qt.AlignRight)
        # self.tab1.layout.setHorizontalSpacing(20)
        # self.tab1.layout.addWidget(self.connectionLabel, 2, 5)




        # self.stock = PortfolioMember()
        # self.tab1.layout.addLayout(self.stock, 1, 0, alignment=Qt.AlignLeft)


        self.tab1.setLayout(self.tab1.layout)

        # Second tab ###########################################################
        self.createTable()
        self.tab2.layout = QVBoxLayout()
        self.tab2.layout.addWidget(self.tableWidget)
        self.tab2.setLayout(self.tab2.layout)


        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


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


    def startupRoutine(self):
        # print('Initiating startup routine')
        # self.statusWindow = InfoWidget()
        # # self.statusWindow.show()
        # status.appendMsg('Testing')
        # Timezone
        self.status_message.emit('Fetching timezone information...')
        api_endpoint = "http://worldtimeapi.org/api/timezone/America/New_York"
        response = None
        # try:
        #     response = requests.get(api_endpoint)
        # except:
        #     self.status_message.emit('ERROR. Failed to fetch timezone info')
        #     msgBox = InfoMessageBox('Error', '\nFailed to fetch timezone info. \n\nPLEASE RESTART APPLICATION.\n')
        #     return

        # unixtime = int(response.json()['unixtime'])
        """DEBUG"""
        unixtime = 1685003072

        edt = datetime.utcfromtimestamp(unixtime)
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


    def refreshWatchlistLayout(self):
        for i in reversed(range(self.watchlistLayout.count())):
            self.watchlistLayout.itemAt(i).widget().setParent(None)
        _w = QWidget()
        title = QHBoxLayout()
        title.setAlignment(Qt.AlignTop|Qt.AlignCenter)
        title.setContentsMargins(0, 0, 0, 0)
        title.setSpacing(0)
        for column in ['Symbol', 'Exchange', 'Bid', 'Last', 'Ask', 'Auction', 'Session', '']:
            w = QLabel(column)
            w.setFixedWidth(80)
            w.setStyleSheet("QLabel{color:#cccccc}")
            w.setAlignment(Qt.AlignCenter|Qt.AlignTop)
            title.addWidget(w)
        _w.setLayout(title)
        self.watchlistLayout.addWidget(_w)
        self.watchlistItems = {}
        line = QWidget()
        line.setFixedSize(560, 1)
        line.setStyleSheet("QWidget{background-color:#cccccc; text-align: left}")
        self.watchlistLayout.addWidget(line)
        for reqId in self.watchlist:
            item = WatchlistItem(reqId, self.watchlist[reqId].contract)
            self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
            self.watchlistItems[reqId] = item
        if len(self.watchlist) == 0:
            self.noItemsInWatchlist()
        return

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

    def addToWatchlist(self, contractDescription):
        if len(self.watchlist) == 0: self.noitem[0].deleteLater()
        self.streamingDataReqId += 1
        self.watchlist[self.streamingDataReqId] = contractDescription
        self.worker.subscribeToStreamingData(self.streamingDataReqId, contractDescription)
        # self.refreshWatchlistLayout()
        item = WatchlistItem(self.streamingDataReqId, contractDescription.contract)
        item.remove.connect(self.removeFromWatchlist, Qt.DirectConnection)
        self.watchlistLayout.addWidget(item, alignment=Qt.AlignTop)
        self.watchlistItems[self.streamingDataReqId] = item

    def removeFromWatchlist(self, reqId):
        if reqId in self.watchlist:
            self.worker.cancelStreamingData(reqId)
            self.watchlist.pop(reqId, None)

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
        if tint >= 40000 and tint < 93000: return 1
        if tint >= 93000 and tint < 160000: return 2
        if tint >= 160000 and tint < 200000: return 3
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
            self.mktStatusLabel.setStyleSheet("QLabel { color: #00E676; }")
        elif state == 3:
            self.mktStatusLabel.setText('After hours trading')
            self.mktStatusLabel.setStyleSheet("QLabel { color: #f39c12; }")


    def showTime(self):

        t = datetime.now() + self.timeMultiplier * timedelta(hours=self.timeDIfferenceWithEDT)
        if self.timeInfoReady: self.clockTime.setText(t.strftime("%I:%M:%S %p") + ' (EDT)')
        self.mktState = self.mapTimeToMktState(t)
        if self.mktState != self.prevMktState:
            self.prevMktState = self.mktState
            self.displayMktState(self.mktState)


    def stop_dash_thread(self):
        self.dashThread.quit()

    def open_chart_window(self):


        # self.chartWindow.quitDash.connect(self.dashWorker.stop)
        # self.chartWindow.quitDash.connect(self.dashWorker.deleteLater)
        # self.chartWindow.quitDash.connect(self.dashThread.deleteLater)

        self.chartWindow.show_graph()


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

    def enable_search_button(self):
        self.searchButton.setEnabled(True)
        self.searchButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.searchButton.setText('Search')

    def disable_search_button(self):
        self.searchButton.setEnabled(False)
        self.searchButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.searchButton.setText('Please wait...')

    @pyqtSlot()
    def start(self):
        self.watchlistItems[100001].animate()
        # self.chart = Chart()
        # self.chart.show()


    def clientID(self):
        return random.randint(1, pow(2, 16) - 1)

    def createTable(self):
       # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(4)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setItem(0,0, QTableWidgetItem("Cell (1,1)"))
        self.tableWidget.setItem(0,1, QTableWidgetItem("Cell (1,2)"))
        self.tableWidget.setItem(1,0, QTableWidgetItem("Cell (2,1)"))
        self.tableWidget.setItem(1,1, QTableWidgetItem("Cell (2,2)"))
        self.tableWidget.setItem(2,0, QTableWidgetItem("Cell (3,1)"))
        self.tableWidget.setItem(2,1, QTableWidgetItem("Cell (3,2)"))
        self.tableWidget.setItem(3,0, QTableWidgetItem("Cell (4,1)"))
        self.tableWidget.setItem(3,1, QTableWidgetItem("Cell (4,2)"))
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
        print("Received signal from the worker")

    def worker_connected(self, code):
        if code == 1:
            self.disable_connect_button()
            self.status_message.emit('')
            self.startButton.setEnabled(True)
            self.connectionLabel.setText("Status:    connected")
            self.isConnected = True
            self.connectionEstablished.emit(1)
            self.enable_start_button()
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


    @pyqtSlot()
    def establish_connection(self):
        self.disable_connect_button()
        self.status_message.emit('Establishing connection...')
        self.thread = QThread()
        self.worker = Worker()
        # self.worker.clientID = self.clientID()
        self.symInfoRequested.connect(self.worker.sym_search, Qt.DirectConnection)
        self.worker.signalEmitted.connect(self.readWorkerSignal, Qt.DirectConnection)
        self.worker.connected.connect(self.worker_connected, Qt.DirectConnection)
        self.worker.emit_error.connect(self.error_received, Qt.DirectConnection)
        self.worker.symbolInfo.connect(self.symbolInfoReceived, Qt.DirectConnection)

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
    dir = os.path.dirname(os.path.abspath(__file__))
    app = QApplication(sys.argv)
    # QFontDatabase.addApplicationFont(dir+"/resources/Neoteric-32A8.ttf")
    with open(dir+'/style.qss', 'r') as f:
        style = f.read()
    app.setStyleSheet(style)
    ex = App()
    sys.exit(app.exec_())
