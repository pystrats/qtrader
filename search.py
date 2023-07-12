from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QDesktopWidget, QWidget, QGridLayout, QShortcut, QLabel, QPushButton
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal


class SearchWindow(QWidget):

    sendContractToChart = pyqtSignal(object, str)
    sendContractToWatchlist = pyqtSignal(object)

    def __init__(self, query, contractDescriptions, source):
        """
        source          watchlist or chart
        """
        super().__init__()

        if contractDescriptions == None: return

        self.source = source

        self.layout = QVBoxLayout()

        # self.scroll.setWidget(self)
        # self.scroll.setWidgetResizable(True)
        # self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #

        self.setGeometry(250,250,650,700)

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        self.infoBox = QWidget()
        self.layout.addWidget(self.infoBox)
        self.setLayout(self.layout)
        self.infoBox.layout = QVBoxLayout()
        self.infoBox.setLayout(self.infoBox.layout)
        self.setWindowTitle("Matching symbols: "+str(query))
        self.infoBoxContainer = QGridLayout()
        self.vboxSpacing = 10
        self.activeContract = 1
        self.nContracts = 0
        self.nothingFound = False

        self.contractDescriptions = contractDescriptions

        self.shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.shortcut.activated.connect(self.close_window, Qt.DirectConnection)
        self.shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut.activated.connect(self.next, Qt.DirectConnection)
        self.shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        self.shortcut.activated.connect(self.previous, Qt.DirectConnection)
        self.shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut.activated.connect(self.ok, Qt.DirectConnection)

        if (len(contractDescriptions)==0):
            layout = QVBoxLayout()
            label = QLabel('Sorry, nothing found')
            label.setStyleSheet("QLabel {color: #ecf0f1; margin-bottom: 75px;}")
            self.infoBox.layout.addWidget(label, alignment=Qt.AlignCenter|Qt.AlignBottom)

            self.closeButton = QPushButton("Close")
            self.closeButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
            self.closeButton.setFixedSize(100,25)
            self.closeButton.setEnabled(True)
            self.closeButton.clicked.connect(self.close_window, Qt.DirectConnection)
            self.infoBox.layout.addWidget(self.closeButton, alignment=Qt.AlignCenter|Qt.AlignVCenter)
            self.nothingFound = True

        else:
            n = 0
            for contractDescription in contractDescriptions:
                derivSecTypes = ""
                for derivSecType in contractDescription.derivativeSecTypes:
                    derivSecTypes += " "
                    derivSecTypes += derivSecType

                # if n == 0: print(contractDescription.contract, contractDescription.contract.__dict__)
                n += 1

            self.nContracts = len(contractDescriptions)

            contractDescription = contractDescriptions[0]
            self.symbolHBox = QHBoxLayout()
            self.tickerLayout = QHBoxLayout()
            self.ticker = QLabel(self.no_symbol(contractDescription.contract.symbol.upper()))
            self.ticker.setStyleSheet("QLabel {font-size: 39px; color: #f39c12; font-weight: bold; margin-right: 1px;}")
            self.ticker.setMinimumWidth(250)
            self.ticker.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            self.exchangeLayout = QHBoxLayout()
            self.exchange = QLabel(self.no_symbol(contractDescription.contract.primaryExchange.upper()))
            self.exchange.setStyleSheet("QLabel {font-size: 15px; color: #95a5a6; margin-left: 1px;}")
            self.exchange.setMinimumWidth(250)
            self.exchange.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)

            self.symbolHBox.addWidget(self.ticker, 1, alignment=Qt.AlignRight|Qt.AlignVCenter)
            self.symbolHBox.addWidget(self.exchange, 1, alignment=Qt.AlignLeft|Qt.AlignTop)
            # self.symbolHBox.addLayout(self.tickerLayout)
            # self.symbolHBox.addLayout(self.exchangeLayout)
            self.symbolHBox.setContentsMargins(0, 0, 0, 35)

            self.contractDetailsGrid = QGridLayout()

            self.symbolAttributes1 = QVBoxLayout()
            self.symA1_assetClass = QLabel('Asset Class: ')
            self.symA1_assetClass.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_assetClass, alignment=Qt.AlignRight)
            self.symA1_currency = QLabel('Currency: ')
            self.symA1_currency.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_currency, alignment=Qt.AlignRight)
            self.symA1_secType = QLabel('Security Type: ')
            self.symA1_secType.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_secType, alignment=Qt.AlignRight)
            self.symA1_destExchange = QLabel('Destination Exchange: ')
            self.symA1_destExchange.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_destExchange, alignment=Qt.AlignRight)
            self.symA1_primaryExchange = QLabel('Primary Exchange: ')
            self.symA1_primaryExchange.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_primaryExchange, alignment=Qt.AlignRight)
            self.symA1_includeExpired = QLabel('Continuous: ')
            self.symA1_includeExpired.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_includeExpired, alignment=Qt.AlignRight)
            self.symA1_id = QLabel('Contract ID: ')
            self.symA1_id.setStyleSheet("QLabel {color: #95a5a6;}")
            self.symbolAttributes1.addWidget(self.symA1_id, alignment=Qt.AlignRight)
            # self.symA1_tradingClass = QLabel('Trading Class: ')
            # self.symA1_tradingClass.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes1.addWidget(self.symA1_tradingClass, alignment=Qt.AlignRight)
            # self.symA1_secIdType = QLabel('Security ID Type: ')
            # self.symA1_secIdType.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes1.addWidget(self.symA1_secIdType, alignment=Qt.AlignRight)
            self.symbolAttributes1.setContentsMargins(0, 0, 10, 0)
            self.symbolAttributes1.setSpacing(self.vboxSpacing)

            # self.symbolAttributes2 = QVBoxLayout()
            # self.symA2_currency = QLabel('Currency: ')
            # self.symA2_currency.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_currency, alignment=Qt.AlignRight)
            # self.symA2_issuerID = QLabel('Security Type: ')
            # self.symA2_issuerID.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_issuerID, alignment=Qt.AlignRight)
            # self.symA2_expiration = QLabel('Expiration: ')
            # self.symA2_expiration.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_expiration, alignment=Qt.AlignRight)
            # self.symA2_multiplier = QLabel('Multiplier: ')
            # self.symA2_multiplier.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_multiplier, alignment=Qt.AlignRight)
            # self.symA2_localSymbol = QLabel('Local Symbol: ')
            # self.symA2_localSymbol.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_localSymbol, alignment=Qt.AlignRight)
            # self.symA2_includeExpired = QLabel('Continuous: ')
            # self.symA2_includeExpired.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_includeExpired, alignment=Qt.AlignRight)
            # self.symA2_id = QLabel('Contract ID: ')
            # self.symA2_id.setStyleSheet("QLabel {color: #95a5a6;}")
            # self.symbolAttributes2.addWidget(self.symA2_id, alignment=Qt.AlignRight)
            # self.symbolAttributes2.setContentsMargins(0, 0, 0, 0)
            # self.symbolAttributes2.setSpacing(self.vboxSpacing)


            self.symbolProperties1 = QVBoxLayout()
            self.symP1_assetClass = QLabel(self.dash(self.assetClass(contractDescription.contract.secType)))
            self.symP1_assetClass.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_assetClass)
            self.symP1_currency = QLabel(self.dash(contractDescription.contract.currency))
            self.symP1_currency.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_currency)
            self.symP1_secType = QLabel(self.dash(contractDescription.contract.secType))
            self.symP1_secType.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_secType)
            self.symP1_destExchange = QLabel(self.dash(self.get_exchange(contractDescription.contract.exchange)))
            self.symP1_destExchange.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_destExchange)
            self.symP1_primExchange = QLabel(self.dash(contractDescription.contract.primaryExchange))
            self.symP1_primExchange.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_primExchange)
            self.symP1_continuous = QLabel(self.dash(self.bool_to_string(contractDescription.contract.includeExpired)))
            self.symP1_continuous.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_continuous)
            self.symP1_conId = QLabel(self.dash(str(contractDescription.contract.conId)))
            self.symP1_conId.setStyleSheet("QLabel {color: #ecf0f1;}")
            self.symbolProperties1.addWidget(self.symP1_conId)
            # self.symP1_tradingClass = QLabel(self.dash(contractDescription.contract.tradingClass))
            # self.symP1_tradingClass.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties1.addWidget(self.symP1_tradingClass)
            # self.symP1_secIdType = QLabel(self.dash(contractDescription.contract.secIdType))
            # self.symP1_secIdType.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties1.addWidget(self.symP1_secIdType)
            self.symbolProperties1.setContentsMargins(10, 0, 0, 0)
            self.symbolProperties1.setSpacing(self.vboxSpacing)

            # self.symbolProperties2 = QVBoxLayout()
            # self.symP2_currency = QLabel(self.dash(contractDescription.contract.currency))
            # self.symP2_currency.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_currency)
            # self.symP2_issuerID = QLabel(self.dash(contractDescription.contract.secId))
            # self.symP2_issuerID.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_issuerID)
            # self.symP2_expiration = QLabel(self.dash(contractDescription.contract.lastTradeDateOrContractMonth))
            # self.symP2_expiration.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_expiration)
            # self.symP2_multiplier = QLabel(self.dash(contractDescription.contract.multiplier))
            # self.symP2_multiplier.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_multiplier)
            # self.symP2_localSymbol = QLabel(self.dash(contractDescription.contract.localSymbol))
            # self.symP2_localSymbol.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_localSymbol)
            # self.symP2_continuous = QLabel(self.dash(self.bool_to_string(contractDescription.contract.includeExpired)))
            # self.symP2_continuous.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_continuous)
            # self.symP2_conId = QLabel(self.dash(str(contractDescription.contract.conId)))
            # self.symP2_conId.setStyleSheet("QLabel {color: #ecf0f1;}")
            # self.symbolProperties2.addWidget(self.symP2_conId)
            # self.symbolProperties2.setSpacing(self.vboxSpacing)

            self.resultLayout = QHBoxLayout()
            self.resultLabel = QLabel("Symbol {}/{}".format(1, self.nContracts))
            self.resultLabel.setStyleSheet("QLabel {color: #ecf0f1; text-align: left; font-style: italic;}")
            self.resultLayout.addWidget(self.resultLabel)
            self.resultLayout.setContentsMargins(0, 0, 0, 75)

            self.hint = QVBoxLayout()
            self.hintLabel1 = QLabel("Ctrl+N: Next")
            self.hintLabel2 = QLabel("Ctrl+B: Previous")
            self.hintLabel3 = QLabel("Ctrl+Q: Close   ")
            enterHint = 'Chart   ' if source == 'chart' else 'Add to Portfolio'
            self.hintLabel4 = QLabel("Enter: " + enterHint)
            self.hintLabel1.setStyleSheet("QLabel {color: #95a5a6; font-style: italic;}")
            self.hintLabel2.setStyleSheet("QLabel {color: #95a5a6; font-style: italic;}")
            self.hintLabel3.setStyleSheet("QLabel {color: #95a5a6; font-style: italic;}")
            self.hintLabel4.setStyleSheet("QLabel {color: #95a5a6; font-style: italic;}")
            self.hint.addWidget(self.hintLabel1)
            self.hint.addWidget(self.hintLabel2)
            self.hint.addWidget(self.hintLabel3)
            self.hint.addWidget(self.hintLabel4)
            self.hint.setContentsMargins(0, 0, 0, 75)

            self.buttonPanel = QHBoxLayout()

            self.prevButton = QPushButton("Previous")
            self.prevButton.setFixedSize(100,30)
            self.prevButton.clicked.connect(self.previous, Qt.DirectConnection)
            self.prevButton.setEnabled(False)

            if source == 'chart':
                self.addButton = QPushButton("Chart")
                self.addButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
                self.addButton.setFixedSize(100,30)
                self.addButton.setEnabled(True)
                self.addButton.clicked.connect(self.ok, Qt.DirectConnection)
            else:
                self.addButton = QPushButton("Add to Portfolio")
                self.addButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
                self.addButton.setFixedSize(150,30)
                self.addButton.setEnabled(True)
                self.addButton.clicked.connect(self.ok, Qt.DirectConnection)

            self.nextButton = QPushButton("Next")
            self.nextButton.setFixedSize(100,30)
            self.nextButton.clicked.connect(self.next, Qt.DirectConnection)
            if self.nContracts > 1:
                self.nextButton.setEnabled(True)
            else: self.nextButton.setEnabled(False)

            self.buttonPanel.addWidget(self.prevButton)
            self.buttonPanel.addWidget(self.addButton)
            self.buttonPanel.addWidget(self.nextButton)

            self.buttonPanel.setContentsMargins(0, 50, 0, 75)


            self.contractDetailsGrid.addLayout(self.resultLayout, 0, 0, alignment=Qt.AlignLeft|Qt.AlignTop)
            self.contractDetailsGrid.addLayout(self.hint, 0, 1, alignment=Qt.AlignRight|Qt.AlignTop)
            self.contractDetailsGrid.addLayout(self.symbolHBox, 1, 0, 1, 2, alignment=Qt.AlignCenter|Qt.AlignVCenter)
            # self.contractDetailsGrid.addLayout(self.resultLayout, 1, 0, alignment=Qt.AlignLeft|Qt.AlignVCenter)
            self.contractDetailsGrid.addLayout(self.symbolAttributes1, 2, 0, alignment=Qt.AlignRight|Qt.AlignVCenter)
            self.contractDetailsGrid.addLayout(self.symbolProperties1, 2, 1, alignment=Qt.AlignLeft|Qt.AlignVCenter)
            # self.contractDetailsGrid.addLayout(self.symbolAttributes2, 2, 2, alignment=Qt.AlignCenter|Qt.AlignTop)
            # self.contractDetailsGrid.addLayout(self.symbolProperties2, 2, 3, alignment=Qt.AlignCenter|Qt.AlignTop)
            self.contractDetailsGrid.addLayout(self.buttonPanel, 3, 0, 1, 2, alignment=Qt.AlignCenter|Qt.AlignVCenter)




            # self.infoBoxContainer.addLayout(self.symbolHBox, 0, 0, alignment=Qt.AlignCenter|Qt.AlignVCenter)
            # self.infoBoxContainer.addWidget(self.resultsWrapper, 0, 0, alignment=Qt.AlignLeft|Qt.AlignTop)
            self.infoBoxContainer.addLayout(self.contractDetailsGrid, 0, 0, alignment=Qt.AlignCenter|Qt.AlignVCenter)
            # self.infoBoxContainer.addLayout(self.buttonPanel, 2, 0, alignment=Qt.AlignCenter|Qt.AlignTop)
            self.infoBox.layout.addLayout(self.infoBoxContainer)


        # print("Contract: conId:%s, symbol:%s, secType:%s primExchange:%s, currency:%s, derivativeSecTypes:%s, description:%s, issuerId:%s" % (
        #         contractDescription.contract.conId,
        #         contractDescription.contract.symbol,
        #         contractDescription.contract.secType,
        #         contractDescription.contract.primaryExchange,
        #         contractDescription.contract.currency, derivSecTypes,
        #         contractDescription.contract.description,
        #         contractDescription.contract.issuerId))

    # def showContractInfo(self, n):





    @pyqtSlot()
    def update_view(self):
        contractDescription = self.contractDescriptions[self.activeContract-1]

        self.ticker.setText(self.no_symbol(contractDescription.contract.symbol.upper()))
        self.ticker.adjustSize()
        self.ticker.repaint()
        self.ticker.update()
        self.exchange.setText(self.no_symbol(contractDescription.contract.primaryExchange.upper()))
        self.exchange.adjustSize()
        self.exchange.repaint()
        self.exchange.update()
        self.ticker.adjustSize()
        self.ticker.repaint()
        self.ticker.update()

        self.symP1_assetClass.setText(self.dash(self.assetClass(contractDescription.contract.secType)))
        self.symP1_assetClass.adjustSize()
        self.symP1_assetClass.repaint()
        self.symP1_assetClass.update()

        self.symP1_currency.setText(self.dash(contractDescription.contract.currency))
        self.symP1_currency.adjustSize()
        self.symP1_currency.repaint()
        self.symP1_currency.update()

        self.symP1_secType.setText(self.dash(contractDescription.contract.secType))
        self.symP1_secType.adjustSize()
        self.symP1_secType.repaint()
        self.symP1_secType.update()

        self.symP1_destExchange.setText(self.dash(self.get_exchange(contractDescription.contract.exchange)))
        self.symP1_destExchange.adjustSize()
        self.symP1_destExchange.repaint()
        self.symP1_destExchange.update()

        self.symP1_primExchange.setText(self.dash(contractDescription.contract.primaryExchange))
        self.symP1_primExchange.adjustSize()
        self.symP1_primExchange.repaint()
        self.symP1_primExchange.update()

        self.symP1_continuous.setText(self.dash(self.bool_to_string(contractDescription.contract.includeExpired)))
        self.symP1_continuous.adjustSize()
        self.symP1_continuous.repaint()
        self.symP1_continuous.update()

        self.symP1_conId.setText(self.dash(str(contractDescription.contract.conId)))
        self.symP1_conId.adjustSize()
        self.symP1_conId.repaint()
        self.symP1_conId.update()

        self.resultLabel.setText("Symbol {}/{}".format(self.activeContract, self.nContracts))
        self.resultLabel.adjustSize()
        self.resultLabel.repaint()
        self.resultLabel.update()

        if self.activeContract >= self.nContracts:
            self.nextButton.setEnabled(False)
        else: self.nextButton.setEnabled(True)
        if self.activeContract > 1:
            self.prevButton.setEnabled(True)
        else: self.prevButton.setEnabled(False)

        self.nextButton.repaint()
        self.nextButton.update()
        self.prevButton.repaint()
        self.prevButton.update()

        self.infoBox.update()


    def no_symbol(self, s):
        return 'N/A' if s == '' or s == ' ' else s


    @pyqtSlot()
    def next(self):
        if self.activeContract >= self.nContracts:
            return
        else:
            self.activeContract += 1
            self.update_view()

    @pyqtSlot()
    def previous(self):
        if self.activeContract <= 1:
            return
        else:
            self.activeContract -= 1
            self.update_view()

    @pyqtSlot()
    def ok(self):
        if not self.nothingFound and self.source == 'chart': self.sendContractToChart.emit(self.contractDescriptions[self.activeContract-1], 'unspecified')
        if not self.nothingFound and self.source == 'watchlist': self.sendContractToWatchlist.emit(self.contractDescriptions[self.activeContract-1])
        self.close()



    def assetClass(self, code):
        if code == "STK":
            return "Stock/ETF"
        elif code == "OPT":
            return "Option"
        elif code == "FUT":
            return "Future"
        elif code == "IND":
            return "Index"
        elif code == "FOP":
            return "Futures Option"
        elif code == "CASH":
            return "Forex"
        elif code == "BAG":
            return "Combo"
        elif code == "WAR":
            return "Warrant"
        elif code == "BOND":
            return "Bond"
        elif code == "CMDTY":
            return "Commodity"
        elif code == "NEWS":
            return "News"
        elif code == "FUND":
            return "Mutual Fund"

    def get_exchange(self, exchange):
        return exchange if exchange != "" else "SMART"

    def dash(self, value):
        return '-' if value == '' or value == ' ' else value

    def bool_to_string(self, b):
        return 'Yes' if b else 'No'


    @pyqtSlot()
    def close_window(self):
        self.close()

    @pyqtSlot()
    def on_ctrl_q(self):
        print('Exiting')
        self.hide()

    def infoReceived(self, contractDescriptions):
        self.defailtMsg.deleteLater()


        # self.Msg = QLabel("Label...")
        # self.Msg.setAlignment(Qt.AlignCenter)
        # self.Msg.setStyleSheet("QLabel {color: white; font-size: 14px;}")
        # self.layout.addWidget(self.defailtMsg, 1, 0)
        #
        # for contractDescription in contractDescriptions:
        #     derivSecTypes = ""
        #     for derivSecType in contractDescription.derivativeSecTypes:
        #         derivSecTypes += " "
        #         derivSecTypes += derivSecType
        #
        #     print(derivSecTypes)

            # self.msg = QLabel("Label...")
            # self.msg.setAlignment(Qt.AlignCenter)
            # self.msg.setStyleSheet("QLabel {color: white; font-size: 14px;}")
            # self.layout.addWidget(self.msg)
            #
            # self.buttonPanel = QHBoxLayout()
            # self.buttonPanel.addWidget(self.msg)
            #
            # self.layout.addLayout(self.buttonPanel, 1, 0, alignment=Qt.AlignRight)

            # self.vlayout = QVBoxLayout()
            #
            # self.symInfo = QLabel("QuantTrader")
            # self.symInfo.setAlignment(Qt.AlignCenter)
            # # self.title.setStyleSheet("QLabel {font-weight: bold; color: black; font-size: 18px;}")
            # self.vlayout.addWidget(self.symInfo)
            #
            # self.layout.addLayout(self.vlayout)
