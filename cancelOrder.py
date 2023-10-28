from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os


class CancelOrder(QWidget):

    cancel_order = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.orders = {}

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 350
        self.height = 130
        self.colWidth = 80

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
        
        self.title = QLabel('Cancel Order')
        self.title.setStyleSheet('QLabel{color:#aaaaaa; font-size: 14px; margin-bottom: 20px;}')

        self.setWindowTitle("Cancel Order")

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


    def abort(self):
        self.close()

    def cancel(self):
        id_str, id = self.selector.currentText(), -1
        try:
            id = int(id_str)
        except:
            self.close()
            return
        if id > 0: self.cancel_order.emit(id)
        self.close()
    
    def repopulate_selector(self):
        self.selector.clear()
        for _, order in self.orders.items():
            if order['orderId'] != 0 and order['status'] != 'Cancelled' and order['remaining'] != 0:
                self.selector.addItem(str(order['orderId']))
