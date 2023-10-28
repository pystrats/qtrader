from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
from threading import Thread

from ibapi.contract import Contract
from ibapi.order import Order

from yahoo_fin import stock_info as si

from search import SearchWindow
from msgboxes import InfoMessageBox


class SubmitOrder(QWidget):

    submit_order = pyqtSignal(object, object)
    amIConnected = pyqtSignal()
    lookupRequest = pyqtSignal(str, str)

    isConnected = False
    lookupQuery = ''

    symbol = ''
    exchange = ''
    quote = ''

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.shortcut_enter = QShortcut(QKeySequence('Return'), self)
        self.shortcut_enter.activated.connect(self.return_hit)

        self.width = 445
        self.height = 390
        self.colWidth = 120

        w = QWidget()
        l = QVBoxLayout()
        self.setLayout(l)

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

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/2. - self.height/2.)

        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)
        
        self.title = QLabel('Submit Order')
        self.title.setStyleSheet('QLabel{color:#aaaaaa; font-size: 14px; margin-bottom: 20px;}')

        self.setWindowTitle("Submit Order")

        self.symbolSerachText = QLineEdit()
        self.symbolSerachText.setMaxLength(30)
        self.symbolSerachText.setAlignment(Qt.AlignLeft)
        self.symbolSerachText.setFixedSize(250,25)
        self.symbolSerachText.setTextMargins(10, 1, 10, 1)

        self.leftControlPanelSpacer = QLabel('')
        self.leftControlPanelSpacer.setFixedWidth(20)

        self.lookupButton = QPushButton('Search', self)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff; margin-right: 0px;}")
        self.lookupButton.setFixedSize(100, 25)
        self.lookupButton.clicked.connect(self.openSearchWindow)

        self.topPanel = QHBoxLayout()
        self.topPanel.addWidget(self.symbolSerachText)
        self.topPanel.addWidget(self.leftControlPanelSpacer)
        self.topPanel.addWidget(self.lookupButton)

        self.symbolPanel = QHBoxLayout()
        self.symbolName = QLabel(self.symbol)
        self.symbolName.setStyleSheet("QLabel {color: #f39c12; margin-right: 0px; font-size: 21px; font-weight: bold;}")
        self.exchangeName = QLabel(self.exchange)
        self.exchangeName.setStyleSheet("QLabel {color: #aaaaaa; margin-left: 15px; font-size: 14px;}")
        self.exchangeName.setAlignment(Qt.AlignVCenter)
        self.quoteField = QLabel(self.quote)
        self.quoteField.setStyleSheet("QLabel {color: #eeeeee; margin-left: 15px; font-size: 14px;}")
        # self.quoteField.setAlignment(Qt.AlignVCenter)

        self.symbolPanel.addWidget(self.symbolName)
        self.symbolPanel.addWidget(self.exchangeName)
        self.symbolPanel.addWidget(self.quoteField)

        self.params = QGridLayout()
        self.params.setHorizontalSpacing(15)
        self.params.setVerticalSpacing(10)

        self.actionLabel = QLabel('Action')
        self.action = QComboBox()
        self.action.setFixedWidth(self.colWidth)
        self.action.addItem('BUY')
        self.action.addItem('SELL')

        self.priceLabel = QLabel('Price')
        self.price = QDoubleSpinBox()
        self.price.setRange(0., 999999.)
        # self.price.setPrefix("$ ")
        self.price.setFixedWidth(self.colWidth)

        self.qtyLabel = QLabel('Qty')
        self.qty = QSpinBox()
        self.qty.setRange(0, 1000000)
        self.qty.setMaximum(1000000)
        self.qty.setValue(100)
        self.qty.setFixedWidth(self.colWidth)

        self.tifLabel = QLabel('TIF')
        self.tif = QComboBox()
        self.tif.setFixedWidth(self.colWidth)
        self.tif.addItem('GTC')
        self.tif.addItem('DAY')

        self.typeLabel = QLabel('Type')
        self.type = QComboBox()
        self.type.currentIndexChanged.connect(self.onCurrentIndexChanged)
        self.type.setFixedWidth(self.colWidth)
        self.type.addItem('MKT')
        self.type.addItem('STP')
        self.type.addItem('LMT')

        self.buttonPanel = QHBoxLayout()
        self.buttonPanel.setContentsMargins(0, 50, 0, 0)

        self.abortBtn = QPushButton('Abort')
        self.abortBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.abortBtn.setEnabled(True)
        self.abortBtn.setFixedSize(100,30)
        self.abortBtn.clicked.connect(self.abort, Qt.DirectConnection)

        self.btnPadding = QLabel('')

        self.tramsmitBtn = QPushButton('Transmit')
        self.tramsmitBtn.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.tramsmitBtn.setEnabled(True)
        self.tramsmitBtn.setFixedSize(100,30)
        self.tramsmitBtn.clicked.connect(self.transmit, Qt.DirectConnection)

        self.buttonPanel.addWidget(self.abortBtn)
        self.buttonPanel.addWidget(self.btnPadding)
        self.buttonPanel.addWidget(self.tramsmitBtn)

        self.params.addWidget(self.actionLabel, 0, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        self.params.addWidget(self.action, 0, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        self.params.addWidget(self.typeLabel, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        self.params.addWidget(self.type, 1, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        self.params.addWidget(self.priceLabel, 2, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        self.params.addWidget(self.price, 2, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        self.params.addWidget(self.qtyLabel, 3, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        self.params.addWidget(self.qty, 3, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        self.params.addWidget(self.tifLabel, 4, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        self.params.addWidget(self.tif, 4, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)

        _l.addLayout(self.topPanel, 0, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addLayout(self.symbolPanel, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addLayout(self.params, 2, 0, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addLayout(self.buttonPanel, 3, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)


        # _l.addWidget(self.title, 0, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        # _l.addWidget(self.cancelBtn, 0, 2, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        # _l.addWidget(self.separator, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignCenter)
        # _l.addWidget(self.abortBtn, 2, 2, alignment=Qt.AlignVCenter|Qt.AlignCenter)

    def enable_lookup_button(self):
        self.lookupButton.setEnabled(True)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.lookupButton.setText('Search')

    def disable_lookup_button(self):
        self.lookupButton.setEnabled(False)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.lookupButton.setText('Please wait')

    def return_hit(self):
        self.openSearchWindow()

    def openSearchWindow(self):
        self.amIConnected.emit()
        if not self.isConnected:
            msgBox = InfoMessageBox('Error', 'Please establish connection')
            self.enable_lookup_button()
        elif self.symbolSerachText.text() == '':
            msgBox = InfoMessageBox('Error', 'Request cannot be empty')
            self.enable_lookup_button()
        else:
            self.disable_lookup_button()
            self.lookupQuery = self.symbolSerachText.text()
            self.lookupRequest.emit(self.lookupQuery, 'order')
            self.symbolSerachText.setText('')

    def lookupResultsReceived(self, code, contractDescriptions):
        if code == 1:
            self.lookupWindow = SearchWindow(self.lookupQuery, contractDescriptions, 'order')
            self.lookupWindow.sendContractToOrder.connect(self.getContractInfo, Qt.DirectConnection)
            self.lookupWindow.show()
        else: msgBox = InfoMessageBox('Error', 'Lookup request failed')
        self.enable_lookup_button()

    def refresh_quote_field(self):
        self.quoteField.setText(self.quote)
        self.quoteField.adjustSize()
        # self.quoteField.repaint()
        # self.quoteField.update()
        

    def get_quote(self, arg):
        try:
            self.quote = str(round(float(si.get_live_price(self.symbol)), 2))
        except Exception as e: 
            self.quote = 'request failed'
        self.refresh_quote_field()

    def getContractInfo(self, contractDescription):
        self.symbol = contractDescription.contract.symbol.upper()
        self.exchange = contractDescription.contract.primaryExchange.upper()
        self.symbolName.setText(self.symbol)
        self.symbolName.adjustSize()
        self.exchangeName.setText(self.exchange)
        self.exchangeName.adjustSize()
        self.quoteField.setText('requesting quote...')
        # self.quoteField.setStyleSheet("QLabel {color: #eeeeee; margin-left: 25px; font-size: 12px;}")
        self.quoteField.adjustSize()
        thread = Thread(target = self.get_quote, args = ('', ))
        thread.start()


    def onCurrentIndexChanged(self, index):
        if index == 0: 
            self.disable_price_field()
            self.disable_tif_field()
        else: 
            self.enable_price_field()
            self.enable_tif_field()

    def disable_price_field(self):
        self.price.setDisabled(True)
        self.price.setStyleSheet("color: #666666;")

    def enable_price_field(self):
        self.price.setDisabled(False)
        self.price.setStyleSheet("color: #eeeeee;")

    def enable_tif_field(self):
        self.tif.setEnabled(True)
        self.tif.setStyleSheet("color: #eeeeee;")

    def disable_tif_field(self):
        self.tif.setEnabled(False)
        self.tif.setStyleSheet("color: #666666;")

    def abort(self):
        self.close()

    def transmit(self):
        price = self.price.value()
        qty = self.qty.value()
        orderType = self.type.currentText()
        action = self.action.currentText()
        tif = self.tif.currentText()
        if self.symbol == '': msgBox = InfoMessageBox('Error', 'Select a contract to trade \n Search using the field at the top')
        elif qty == 0 and price != .0: msgBox = InfoMessageBox('Error', 'Qty is set to zero. Please adjust.')
        elif qty != 0 and (price == .0 and orderType != 'MKT'): msgBox = InfoMessageBox('Error', 'Price is set to zero. Please adjust.')
        elif qty == 0 and price == .0: msgBox = InfoMessageBox('Error', 'Neither Qty nor Price can be zero')
        else:
            order = Order()
            order.action = action
            order.totalQuantity = qty
            if orderType != 'MKT': order.tif = tif
            order.orderType, order.transmit, order.eTradeOnly, order.firmQuoteOnly = orderType, True, False, False
            if orderType == 'LMT': order.lmtPrice = price
            if orderType == 'STP': order.auxPrice = price
            contract = Contract()
            contract.symbol, contract.secType, contract.exchange, contract.currency = self.symbol, 'STK', 'SMART', 'USD'
            contract.primaryExchange = self.exchange
            self.submit_order.emit(order, contract)
            msgBox = InfoMessageBox('Success', 'Order submitted')
            self.close()


    def updateConnectionStatus(self, status):
        self.isConnected = status

        order = Order()
        order.action = 'BUY'
        order.totalQuantity = 100
        order.orderType, order.transmit, order.eTradeOnly, order.firmQuoteOnly = 'LMT', True, False, False
        order.lmtPrice = 172.5
        contract = Contract()
        contract.symbol, contract.secType, contract.exchange, contract.currency = self.symbol, 'STK', 'SMART', 'USD'

