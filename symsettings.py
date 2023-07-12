from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
import json


class SymbolSettings(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 600
        self.widthSpacing = 100

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

        title = QLabel('Settings')
        title.setStyleSheet('QLabel{color:"#aaaaaa"; font-size:16px; font-weight: normal; margin-bottom: 15px;}')

        strategy = QLabel('Strategy')
        strategy_separator = QWidget()
        strategy_separator.setFixedSize(self.width - self.widthSpacing, 1)
        strategy_separator.setStyleSheet('QWidget{background-color: "#aaaaaa"; text-align: left; width:100%;}')

        connection = QLabel('Connection')
        connection.setStyleSheet("QLabel{margin-top: 25px;}")

        separator = QWidget()
        separator.setFixedSize(self.width - self.widthSpacing, 1)
        separator.setStyleSheet('QWidget{background-color: "#aaaaaa"; text-align: left; width:100%;}')

        port_name = QLabel('Port')
        self.port_value = QLineEdit( str(self.settings['connection']['port']) )
        self.port_value.setMaxLength(4)
        self.port_value.setAlignment(Qt.AlignLeft)
        self.port_value.setFixedSize(75,28)
        self.port_value.setTextMargins(10, 1, 10, 1)

        clientID_n = QLabel('Client ID')
        self.clientID_v = QLineEdit( str(self.settings['connection']['clientId']) )
        self.clientID_v.setMaxLength(10)
        self.clientID_v.setAlignment(Qt.AlignLeft)
        self.clientID_v.setFixedSize(75,28)
        self.clientID_v.setTextMargins(10, 1, 10, 1)

        server = QLabel('Server')
        server.setStyleSheet("QLabel{margin-top: 25px;}")
        server_separator = QWidget()
        server_separator.setFixedSize(self.width - self.widthSpacing, 1)
        server_separator.setStyleSheet('QWidget{background-color: "#aaaaaa"; text-align: left; width:100%;}')

        timeframe = QLabel('Timeframe')
        self.timeframe_spinbox = QSpinBox()
        self.timeframe_spinbox.setRange(1,60)
        self.timeframe_spinbox.setMaximum(60)
        self.timeframe_spinbox.setValue( self.settings['strategy']['timeframe'] )
        self.timeframe_spinbox.setSuffix(" minutes")

        onlyRTH_history = QLabel('Only RTH data in analyses')
        self.use_only_RTH_data = QCheckBox()
        self.use_only_RTH_data.setChecked( self.settings['strategy']['onlyRTH_history'] )

        onlyRTH_trading = QLabel('Trade only during regular hours')
        self.use_only_RTH_trading = QCheckBox()
        self.use_only_RTH_trading.setChecked( self.settings['strategy']['onlyRTH_trading'] )

        trade_all = QLabel('Trade all strategies by default')
        self.trade_all = QCheckBox()
        self.trade_all.setChecked( self.settings['strategy']['trade_all'] )

        default_pos_size = QLabel('Default position size')
        self.default_pos_size = QSpinBox()
        self.default_pos_size.setRange(0,1000000)
        self.default_pos_size.setMaximum(1000000)
        self.default_pos_size.setValue( self.settings['strategy']['pos_size'] )
        self.default_pos_size.setPrefix("$ ")

        server_address = QLabel('Address')
        self.server_value = QLineEdit(self.settings['server']['address'])
        self.server_value.setInputMask( "000.000.000.000" )
        # port_value.setMaxLength(4)
        self.server_value.setAlignment(Qt.AlignLeft)
        self.server_value.setFixedSize(150,28)
        self.server_value.setTextMargins(10, 1, 10, 1)

        auth = QLabel('Authentication Key')
        self.auth_value = QLineEdit(self.settings['server']['key'])
        self.auth_value.setAlignment(Qt.AlignLeft)
        self.auth_value.setFixedSize(150,28)
        self.auth_value.setTextMargins(10, 1, 10, 1)

        role = QLabel('Role')
        self.role_value = QComboBox()
        if self.settings['server']['role'] == 'Client':
            self.role_value.setCurrentIndex(0)
        else: self.role_value.setCurrentIndex(1)
        self.role_value.addItem('Client')
        self.role_value.addItem('Server')
        # self.role_value.setFixedWidth(100)

        margin = QLabel('Margin')
        margin.setStyleSheet("QLabel{margin-top: 25px;}")
        margin_separator = QWidget()
        margin_separator.setFixedSize(self.width - self.widthSpacing, 1)
        margin_separator.setStyleSheet('QWidget{background-color: "#aaaaaa"; text-align: left; width:100%;}')

        intraday_margin = QLabel('Intraday Margin')
        self.intraday_margin = QSpinBox()
        self.intraday_margin.setRange(1,100)
        self.intraday_margin.setMaximum(100)
        self.intraday_margin.setValue( self.settings['margin']['intraday'] )
        self.intraday_margin.setSuffix('%')

        overnight_margin = QLabel('Overnight Margin')
        self.overnight_margin = QSpinBox()
        self.overnight_margin.setRange(1,100)
        self.overnight_margin.setMaximum(100)
        self.overnight_margin.setValue( self.settings['margin']['overnight'] )
        self.overnight_margin.setSuffix('%')

        common = QLabel('Common')
        common.setStyleSheet("QLabel{margin-top: 25px;}")
        common_separator = QWidget()
        common_separator.setFixedSize(self.width - self.widthSpacing, 1)
        common_separator.setStyleSheet('QWidget{background-color: "#aaaaaa"; text-align: left; width:100%;}')

        check_updates = QLabel('Check for updates on startup')
        self.check_updates_checkbox = QCheckBox()
        self.check_updates_checkbox.setChecked( self.settings['common']['checkUpdates'] )

        default_risk = QLabel('Default risk per trade')
        self.default_risk = QSpinBox()
        self.default_risk.setRange(0,10000)
        self.default_risk.setMaximum(10000)
        self.default_risk.setValue( self.settings['common']['risk'] )
        self.default_risk.setPrefix("$ ")

        button_panel = QHBoxLayout()
        button_panel.setContentsMargins(0, 50, 0, 0)
        cancelBtn = QPushButton('Cancel')
        cancelBtn.setFixedSize(100, 30)
        cancelBtn.clicked.connect(self.cancel)
        cancelBtn.setEnabled(True)
        padding = QLabel('')
        saveBtn = QPushButton('Save')
        saveBtn.setFixedSize(100, 30)
        saveBtn.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a;}")
        saveBtn.clicked.connect(self.save)
        saveBtn.setEnabled(True)
        button_panel.addWidget(cancelBtn)
        button_panel.addWidget(padding)
        button_panel.addWidget(saveBtn)

        _l.addWidget(title, 0, 0, 1, 2, alignment=Qt.AlignTop|Qt.AlignRight)
        _l.addWidget(strategy, 1, 0, 1, 2, alignment=Qt.AlignBottom|Qt.AlignLeft)
        _l.addWidget(strategy_separator, 2, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(timeframe, 3, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.timeframe_spinbox, 3, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(onlyRTH_history, 4, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.use_only_RTH_data, 4, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(onlyRTH_trading, 5, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.use_only_RTH_trading, 5, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(trade_all, 6, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.trade_all, 6, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(default_pos_size, 7, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.default_pos_size, 7, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)

        _l.addWidget(connection, 10, 0, 1, 2, alignment=Qt.AlignBottom|Qt.AlignLeft)
        _l.addWidget(separator, 11, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(port_name, 12, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.port_value, 12, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(clientID_n, 13, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.clientID_v, 13, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(server, 14, 0, 1, 2, alignment=Qt.AlignBottom|Qt.AlignLeft)
        _l.addWidget(server_separator, 15, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(server_address, 16, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.server_value, 16, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(auth, 17, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.auth_value, 17, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(role, 18, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.role_value, 18, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(margin, 19, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(margin_separator, 20, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(intraday_margin, 21, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.intraday_margin, 21, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(overnight_margin, 22, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.overnight_margin, 22, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(common, 23, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(common_separator, 24, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(check_updates, 25, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.check_updates_checkbox, 25, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(default_risk, 26, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.default_risk, 26, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addLayout(button_panel, 27, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)


        self.setWindowTitle("Settings")


        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/7.)

        self.setFixedWidth(self.width)
        # self.setMinimumWidth(500)
        self.setFixedHeight(self.screenHeight*.75)
