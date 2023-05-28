from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QVariantAnimation, QAbstractAnimation, pyqtSignal, pyqtSlot
import random
from time import time
import functools




class WatchlistItem(QWidget):

    remove = pyqtSignal(int)

    def __init__(self, reqId, contract, parent=None):
        super().__init__(parent)

        self.MIN_TIME_BETWEEN_ANIMATIONS = .5

        self.reqId = reqId

        self.symbol = contract.symbol
        self.exchange = contract.primaryExchange if contract.primaryExchange not in ['', ' '] else contract.exchange
        self.bid = '-'
        self.prevLast = None
        self.last = .0
        self.ask = '-'
        self.auction = 'Halted'
        self.session = 'Closed'
        self.prevAnimationTime = time()
        self.colWidth = 80
        self.rowHeight = 25

        # self.setStyleSheet("color: red;")

        self.layout = QHBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._symbol = QLabel(self.symbol)
        self._exchange = QLabel(self.exchange)
        self._bid = QLabel(self.bid)
        self._last = QLabel('-')
        self._ask = QLabel(self.ask)
        self._auction = QLabel(self.auction)
        self._session = QLabel(self.session)

        self._symbol.setAlignment(Qt.AlignCenter)
        self._exchange.setAlignment(Qt.AlignCenter)
        self._bid.setAlignment(Qt.AlignCenter)
        self._last.setAlignment(Qt.AlignCenter)
        self._ask.setAlignment(Qt.AlignCenter)
        self._auction.setAlignment(Qt.AlignCenter)
        self._session.setAlignment(Qt.AlignCenter)

        self._symbol.setFixedWidth(self.colWidth)
        self._exchange.setFixedWidth(self.colWidth)
        self._bid.setFixedWidth(self.colWidth)
        self._last.setFixedWidth(self.colWidth)
        self._ask.setFixedWidth(self.colWidth)
        self._auction.setFixedWidth(self.colWidth)
        self._session.setFixedWidth(self.colWidth)

        self._symbol.setFixedHeight(self.rowHeight)
        self._exchange.setFixedHeight(self.rowHeight)
        self._bid.setFixedHeight(self.rowHeight)
        self._last.setFixedHeight(self.rowHeight)
        self._ask.setFixedHeight(self.rowHeight)
        self._auction.setFixedHeight(self.rowHeight)
        self._session.setFixedHeight(self.rowHeight)

        self._symbol.setStyleSheet("QLabel{color:#f39c12; font-weight: bold; font-size: 17px;}")
        self._exchange.setStyleSheet("QLabel{color:#aaaaaa; font-weight: normal;}")

        self.removeBtn = QPushButton('Remove')
        self.removeBtn.setStyleSheet("QPushButton { border: 1px solid #2a2a2a; border-radius: 3px; background-color: '#4a4a4a'; color: '#eeeeee'; font-size: 12px; }")
        self.removeBtn.setEnabled(True)
        self.removeBtn.clicked.connect(self._remove)
        self.removeBtn.setFixedSize(75,25)

        self.layout.addWidget(self._symbol)
        self.layout.addWidget(self._exchange)
        self.layout.addWidget(self._bid)
        self.layout.addWidget(self._last)
        self.layout.addWidget(self._ask)
        self.layout.addWidget(self._auction)
        self.layout.addWidget(self._session)
        self.layout.addWidget(self.removeBtn)

        self.setLayout(self.layout)

        # self.setFixedSize(30, 75)
        # self.setAlignment(Qt.AlignCenter|Qt.AlignVCenter)

        self._animationIncreasing = QVariantAnimation(
            self,
            valueChanged=self._animateIncreasing,
            startValue=0.0001,
            endValue=0.9999,
            duration=750
        )

        self._animationDecreasing = QVariantAnimation(
            self,
            valueChanged=self._animateDecreasing,
            startValue=0.0001,
            endValue=0.9999,
            duration=750
        )

    def helper_function(self, widget, color):
        widget.setStyleSheet("background-color: {}".format(color))


    def apply_color_animation(self, widget, start_color, end_color, duration=750):
        anim = QVariantAnimation(
            widget,
            duration=duration,
            startValue=start_color,
            endValue=end_color,
            loopCount=2,
        )
        anim.valueChanged.connect(functools.partial(self.helper_function, widget))
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    def _animateIncreasing(self, value):
        qss = "background-color:rgba(0, 230, 118, {value});".format(value=round(value, 2))
        self.setStyleSheet(qss)

    def _animateDecreasing(self, value):
        qss = "background-color:rgba(255, 82, 82, {value});".format(value=round(value, 2))
        self.setStyleSheet(qss)


    def animateIncreasing(self):
        self._animationDecreasing.stop()
        self._animationIncreasing.stop()
        self._animationIncreasing.setDirection(QAbstractAnimation.Backward)
        self._animationIncreasing.start()


    def animateDecreasing(self):
        self._animationDecreasing.stop()
        self._animationIncreasing.stop()
        self._animationDecreasing.setDirection(QAbstractAnimation.Backward)
        self._animationDecreasing.start()

    def animate(self):
        if random.random() < .5:
            self.animateIncreasing()
        else: self.animateDecreasing()


    def _update(self, tickType, value):
        if tickType == 4:
            self.prevLast = self.last
            self.last = value
            self._last.setText(str(self.last))
            if self.prevLast != .0:
                if self.last > self.prevLast:
                    self._last.setStyleSheet("color: rgb(0, 230, 118);")
                elif self.last < self.prevLast:
                    self._last.setStyleSheet("color: rgb(255, 82, 82);")

    def _remove(self):
        self.remove.emit(self.reqId)
