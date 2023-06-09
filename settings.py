from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
import json


class Settings(QWidget):

    success = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 500
        self.widthSpacing = 60

        self.settings = {"connection": {"port": 4002, "clientId": 1}, "server": {"address": "000.000.000.000", "key": "", "role": "Client"}, "common": {"checkUpdates": True, "risk": 100}, "margin": {"intraday" : 50, "overnight" : 25}}

        fileName = path = '{}{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/', 'settings.json')
        if os.path.isfile(fileName):
            with open(fileName) as f:
                self.settings = json.load(f)

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

        connection = QLabel('Connection')

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
        self.default_risk.setPrefix("$")

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
        _l.addWidget(connection, 1, 0, 1, 2, alignment=Qt.AlignBottom|Qt.AlignLeft)
        _l.addWidget(separator, 2, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(port_name, 3, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.port_value, 3, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(clientID_n, 4, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.clientID_v, 4, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(server, 5, 0, 1, 2, alignment=Qt.AlignBottom|Qt.AlignLeft)
        _l.addWidget(server_separator, 6, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(server_address, 7, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.server_value, 7, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(auth, 8, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.auth_value, 8, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(role, 9, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.role_value, 9, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(margin, 10, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(margin_separator, 11, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(intraday_margin, 12, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.intraday_margin, 12, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(overnight_margin, 13, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.overnight_margin, 13, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(common, 14, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(common_separator, 15, 0, 1, 2, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(check_updates, 16, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.check_updates_checkbox, 16, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(default_risk, 17, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.default_risk, 17, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addLayout(button_panel, 18, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)


        self.setWindowTitle("Settings")


        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/7.)

        self.setFixedWidth(self.width)
        # self.setMinimumWidth(500)
        self.setFixedHeight(self.screenHeight*.75)

        # qtRectangle = self.frameGeometry()
        # centerPoint = QDesktopWidget().availableGeometry().center()
        # qtRectangle.moveCenter(centerPoint)
        # self.move(qtRectangle.topLeft())

    def cancel(self):
        self.close()

    def save(self):
        self.settings = {}
        self.settings['connection'] = {}
        self.settings['connection']['port'] = int(self.port_value.text())
        self.settings['connection']['clientId'] = int(self.clientID_v.text())
        self.settings['server'] = {}
        self.settings['server']['address'] = str(self.server_value.text())
        self.settings['server']['key'] = str(self.auth_value.text())
        self.settings['server']['role'] = str(self.role_value.currentText())
        self.settings['common'] = {}
        self.settings['common']['checkUpdates'] = self.check_updates_checkbox.isChecked()
        self.settings['common']['risk'] = int(self.default_risk.value())
        self.settings['margin'] = {}
        self.settings['margin']['intraday'] = int(self.intraday_margin.value())
        self.settings['margin']['overnight'] = int(self.overnight_margin.value())
        try:
            path = '{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/' )
            if not os.path.isdir(path): os.mkdir(path)
            fileName = '{}{}'.format(path, 'settings.json')
            with open(fileName, 'w') as f:
                f.write(json.dumps(self.settings))
            self.success.emit(True)
        except: self.success.emit(False)
        self.close()
