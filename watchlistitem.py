from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QVariantAnimation, QAbstractAnimation, pyqtSignal, pyqtSlot
import random
from time import time
import functools


class AnimatedWidget(QLabel):
    def __init__(self):
        super().__init__()

        self._animationIncreasing = QVariantAnimation(
            self,
            valueChanged=self._animateIncreasing,
            startValue=0.0001,
            endValue=0.9999,
            duration=500
        )

        self._animationDecreasing = QVariantAnimation(
            self,
            valueChanged=self._animateDecreasing,
            startValue=0.0001,
            endValue=0.9999,
            duration=500
        )

        self.last = .0
        self.prevLast = .0

        self.setText('-')
        self.setStyleSheet("color: #eeeeee;")

    def reset(self):
        self.setText('-')
        self.setStyleSheet("color: #eeeeee;")

    def _animateIncreasing(self, value):
        qss = "background-color:rgba(0, 230, 118, {value}); color:rgba(0, 230, 118, {valueInversed});".format(value=round(value, 2), valueInversed=round(1.-value, 2))
        self.setStyleSheet(qss)

    def _animateDecreasing(self, value):
        qss = "background-color:rgba(255, 82, 82, {value}); color:rgba(255, 82, 82, {valueInversed});".format(value=round(value, 2), valueInversed=round(1.-value, 2))
        self.setStyleSheet(qss)

    def animateIncreasing(self):
        if self._animationIncreasing.state() == QAbstractAnimation.Running: self._animationIncreasing.stop()
        if self._animationDecreasing.state() == QAbstractAnimation.Running: self._animationDecreasing.stop()

        self._animationIncreasing.setDirection(QAbstractAnimation.Backward)
        self._animationIncreasing.start()


    def animateDecreasing(self):
        if self._animationIncreasing.state() == QAbstractAnimation.Running: self._animationIncreasing.stop()
        if self._animationDecreasing.state() == QAbstractAnimation.Running: self._animationDecreasing.stop()
        self._animationDecreasing.setDirection(QAbstractAnimation.Backward)
        self._animationDecreasing.start()

    def animate(self):
        if not self.prevLast == .0:
            if self.last > self.prevLast:
                self.animateIncreasing()
            elif self.last < self.prevLast:
                self.animateDecreasing()
        self.prevLast = self.last


class WatchlistItem(QWidget):

    remove = pyqtSignal(int)
    requestMarketState = pyqtSignal()

    def __init__(self, reqId, contract, parent=None):
        super().__init__(parent)

        self.MIN_TIME_BETWEEN_ANIMATIONS = .5

        self.reqId = reqId

        self.symbol = contract.symbol
        self.exchange = contract.primaryExchange if contract.primaryExchange not in ['', ' '] else contract.exchange
        self.prevClose = .0
        self.change = .0
        self.dayHigh = .0
        self.dayLow = .0
        self.auction = 'Halted'
        self.session = 'Closed'
        self.history = 'Pending'
        self.position = 0
        self.risk = 0
        self.margin = 0
        self.dayDirection = 0
        self.lastKnownDayDirection = 0
        self.auctionState = -1
        self.prevAnimationTime = time()
        self.colWidth = 80
        self.rowHeight = 25

        self.layout = QHBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._symbol = QLabel(self.symbol)
        self._exchange = QLabel(self.exchange)
        self._prevClose = QLabel('-')
        self._change = QLabel('-')
        self._dayHigh = QLabel('-')
        self._dayLow = QLabel('-')
        self._bid = AnimatedWidget()
        self._last = AnimatedWidget()
        self._ask = AnimatedWidget()
        self._position = QLabel('0')
        self._risk = QLabel('0')
        self._margin = QLabel('0')
        self._auction = QLabel(self.auction)
        self._session = QLabel(self.session)
        self._history = QLabel(self.history)

        self._symbol.setAlignment(Qt.AlignCenter)
        self._exchange.setAlignment(Qt.AlignCenter)
        self._prevClose.setAlignment(Qt.AlignCenter)
        self._change.setAlignment(Qt.AlignCenter)
        self._dayHigh.setAlignment(Qt.AlignCenter)
        self._dayLow.setAlignment(Qt.AlignCenter)
        self._bid.setAlignment(Qt.AlignCenter)
        self._last.setAlignment(Qt.AlignCenter)
        self._ask.setAlignment(Qt.AlignCenter)
        self._auction.setAlignment(Qt.AlignCenter)
        self._session.setAlignment(Qt.AlignCenter)
        self._history.setAlignment(Qt.AlignCenter)
        self._position.setAlignment(Qt.AlignCenter)
        self._risk.setAlignment(Qt.AlignCenter)
        self._margin.setAlignment(Qt.AlignCenter)

        self._symbol.setFixedWidth(self.colWidth)
        self._exchange.setFixedWidth(self.colWidth)
        self._prevClose.setFixedWidth(self.colWidth)
        self._change.setFixedWidth(self.colWidth)
        self._dayHigh.setFixedWidth(self.colWidth)
        self._dayLow.setFixedWidth(self.colWidth)
        self._bid.setFixedWidth(self.colWidth)
        self._last.setFixedWidth(self.colWidth)
        self._ask.setFixedWidth(self.colWidth)
        self._auction.setFixedWidth(self.colWidth)
        self._session.setFixedWidth(self.colWidth)
        self._history.setFixedWidth(self.colWidth)
        self._position.setFixedWidth(self.colWidth)
        self._risk.setFixedWidth(self.colWidth)
        self._margin.setFixedWidth(self.colWidth)

        self._symbol.setFixedHeight(self.rowHeight)
        self._exchange.setFixedHeight(self.rowHeight)
        self._prevClose.setFixedHeight(self.rowHeight)
        self._change.setFixedHeight(self.rowHeight)
        self._dayHigh.setFixedHeight(self.rowHeight)
        self._dayLow.setFixedHeight(self.rowHeight)
        self._bid.setFixedHeight(self.rowHeight)
        self._last.setFixedHeight(self.rowHeight)
        self._ask.setFixedHeight(self.rowHeight)
        self._auction.setFixedHeight(self.rowHeight)
        self._session.setFixedHeight(self.rowHeight)
        self._history.setFixedHeight(self.rowHeight)
        self._position.setFixedHeight(self.rowHeight)
        self._risk.setFixedHeight(self.rowHeight)
        self._margin.setFixedHeight(self.rowHeight)

        self._symbol.setStyleSheet("QLabel{color:#f39c12; font-weight: bold; font-size: 17px;}")
        self._exchange.setStyleSheet("QLabel{color:#aaaaaa; font-weight: normal;}")
        self._history.setStyleSheet("QLabel{color:#6a6a6a; font-weight: normal;}")
        self._change.setStyleSheet("QLabel{color:#aaaaaa;}")
        self._position.setStyleSheet("QLabel{color:#777777;}")
        self._risk.setStyleSheet("QLabel{color:#777777;}")
        self._margin.setStyleSheet("QLabel{color:#777777;}")
        self._session.setStyleSheet("QLabel{color:#777777;}")
        self._auction.setStyleSheet("QLabel{color:#777777;}")

        self.removeBtn = QPushButton('Remove')
        self.removeBtn.setStyleSheet("QPushButton { border: 1px solid #2a2a2a; border-radius: 3px; background-color: '#4a4a4a'; color: '#eeeeee'; font-size: 12px; }")
        self.removeBtn.setEnabled(True)
        self.removeBtn.clicked.connect(self._remove)
        self.removeBtn.setFixedSize(75,25)

        self.animateLast = QPushButton('')
        self.animateLast.clicked.connect(self._last.animate)
        self.animateBid = QPushButton('')
        self.animateBid.clicked.connect(self._bid.animate)
        self.animateAsk = QPushButton('')
        self.animateAsk.clicked.connect(self._ask.animate)

        self.layout.addWidget(self._symbol)
        self.layout.addWidget(self._exchange)
        self.layout.addWidget(self._prevClose)
        self.layout.addWidget(self._change)
        self.layout.addWidget(self._bid)
        self.layout.addWidget(self._last)
        self.layout.addWidget(self._ask)
        self.layout.addWidget(self._position)
        self.layout.addWidget(self._risk)
        self.layout.addWidget(self._margin)
        self.layout.addWidget(self._auction)
        self.layout.addWidget(self._session)
        self.layout.addWidget(self._history)
        self.layout.addWidget(self.removeBtn)

        self.setLayout(self.layout)

    def mktStateUpdate(self, state):
        print('Market state update ')
        if state == 0:
            self.resetAllFields()
        elif state == 1:
            self._auction.setText('Open')
            self._auction.setStyleSheet("QLabel{color:#00E676;}")
            self._session.setText('Post-market')
            self._session.setStyleSheet("QLabel{color:#f39c12;}")
        elif state == 2:
            self._auction.setText('Open')
            self._auction.setStyleSheet("QLabel{color:#00E676;}")
            self._session.setText('Regular')
            self._session.setStyleSheet("QLabel{color:#aaaaaa;}")
        elif state == 3:
            self._auction.setText('Open')
            self._auction.setStyleSheet("QLabel{color:#00E676;}")
            self._session.setText('After market')
            self._session.setStyleSheet("QLabel{color:#f39c12;}")


    def updateChangeField(self):
        prefix = "+" if self.change > .0 else ""
        self._change.setText( "{}{}{}".format(prefix, round(self.change, 2), "%") )
        if self.change > .0:
            self.dayDirection = 1
            if self.dayDirection != self.lastKnownDayDirection: self._change.setStyleSheet("QLabel{color:rgba(0, 230, 118, 1);}")
        elif self.change < .0:
            self.dayDirection = -1
            if self.dayDirection != self.lastKnownDayDirection: self._change.setStyleSheet("QLabel{color:rgba(255, 82, 82, 1);}")
        else:
            self.dayDirection = 0
            self._change.setStyleSheet("QLabel{color:#aaaaaa;}")
        self.lastKnownDayDirection = self.dayDirection


    def resetAllFields(self):
        self.prevClose = .0
        self.change = .0
        self.dayHigh = .0
        self.dayLow = .0
        self.auction = 'Halted'
        self.session = 'Closed'
        self.dayDirection = 0
        self.lastKnownDayDirection = 0
        self.auctionState = -1
        self._prevClose.setText('-')
        self._change.setText('-')
        self._bid.reset()
        self._last.reset()
        self._ask.reset()
        self._auction.setText('Halted')
        self._auction.setStyleSheet("QLabel{color:#777777;}")
        self._session.setText('Closed')
        self._session.setStyleSheet("QLabel{color:#777777;}")


    def _update(self, tickType, value):
        if value == -1:
            self.resetAllFields()
            return
        if tickType == 4:
            self._last.last = value
            self._last.setText(str(self._last.last))
            self.animateLast.click()
            if self.prevClose != .0:
                self.change = 100. * (value - self.prevClose) / self.prevClose
                self.updateChangeField()
            if self.auctionState == -1:
                self.requestMarketState.emit()
                self.auctionState = 1
        elif tickType == 1:
            self._bid.last = value
            self._bid.setText(str(self._bid.last))
            self.animateBid.click()
        elif tickType == 2:
            self._ask.last = value
            self._ask.setText(str(self._ask.last))
            self.animateAsk.click()
        elif tickType == 9:
            self.prevClose = value
            self._prevClose.setText(str(self.prevClose))


    def _remove(self):
        self.remove.emit(self.reqId)
