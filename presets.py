from PyQt5.QtWidgets import (QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget,
                    QScrollArea, QGridLayout, QApplication, QLineEdit, QShortcut, QComboBox, QCheckBox, QSpinBox, QHBoxLayout, QDoubleSpinBox)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from copy import deepcopy
import os
import json


class PresetItem(QWidget):

    modify = pyqtSignal(str, object)
    remove = pyqtSignal(str)

    def __init__(self, item, parent=None):
        super().__init__(parent)

        self.colWidth = 80
        self.rowHeight = 25

        self.item = item

        self.layout = QHBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._name = QLabel(item['name'])
        self._2min = QLabel(str(item['2min']))
        self._2max = QLabel(str(item['2max']))
        self._3min = QLabel(str(item['3min']))
        self._3max = QLabel(str(item['3max']))
        self._12min = QLabel(str(item['12min']))
        self._12max = QLabel(str(item['12max']))
        self._avgmin = QLabel(str(item['avgmin']))
        self._avgmax = QLabel(str(item['avgmax']))

        self._name.setAlignment(Qt.AlignCenter)
        self._2min.setAlignment(Qt.AlignCenter)
        self._2max.setAlignment(Qt.AlignCenter)
        self._3min.setAlignment(Qt.AlignCenter)
        self._3max.setAlignment(Qt.AlignCenter)
        self._12min.setAlignment(Qt.AlignCenter)
        self._12max.setAlignment(Qt.AlignCenter)
        self._avgmin.setAlignment(Qt.AlignCenter)
        self._avgmax.setAlignment(Qt.AlignCenter)

        self._name.setFixedWidth(self.colWidth)
        self._2min.setFixedWidth(self.colWidth)
        self._2max.setFixedWidth(self.colWidth)
        self._3min.setFixedWidth(self.colWidth)
        self._3max.setFixedWidth(self.colWidth)
        self._12min.setFixedWidth(self.colWidth)
        self._12max.setFixedWidth(self.colWidth)
        self._avgmin.setFixedWidth(self.colWidth)
        self._avgmax.setFixedWidth(self.colWidth)

        self._name.setFixedHeight(self.rowHeight)
        self._2min.setFixedHeight(self.rowHeight)
        self._2max.setFixedHeight(self.rowHeight)
        self._3min.setFixedHeight(self.rowHeight)
        self._3max.setFixedHeight(self.rowHeight)
        self._12min.setFixedHeight(self.rowHeight)
        self._12max.setFixedHeight(self.rowHeight)
        self._avgmin.setFixedHeight(self.rowHeight)
        self._avgmax.setFixedHeight(self.rowHeight)

        self.modifyBtn = QPushButton('Modify')
        self.modifyBtn.setStyleSheet("QPushButton { border: 1px solid #2a2a2a; border-radius: 3px; background-color: '#4a4a4a'; color: '#eeeeee'; font-size: 12px;}")
        self.modifyBtn.setEnabled(True)
        self.modifyBtn.clicked.connect(self._modify)
        self.modifyBtn.setFixedSize(75,25)
        self.modifyBtn.setContentsMargins(9, 0, 0, 4)

        self.spacer = QLabel(' ')
        self.spacer.setStyleSheet('QLabel{min-width: 5px;}')

        self.removeBtn = QPushButton('Remove')
        self.removeBtn.setStyleSheet("QPushButton { border: 1px solid #2a2a2a; border-radius: 3px; background-color: '#4a4a4a'; color: '#eeeeee'; font-size: 12px; }")
        self.removeBtn.setEnabled(True)
        self.removeBtn.clicked.connect(self._remove)
        self.removeBtn.setFixedSize(75,25)

        self.layout.addWidget(self._name)
        self.layout.addWidget(self._2min)
        self.layout.addWidget(self._2max)
        self.layout.addWidget(self._3min)
        self.layout.addWidget(self._3max)
        self.layout.addWidget(self._12min)
        self.layout.addWidget(self._12max)
        self.layout.addWidget(self._avgmin)
        self.layout.addWidget(self._avgmax)
        self.layout.addWidget(self.modifyBtn)
        self.layout.addWidget(self.spacer)
        self.layout.addWidget(self.removeBtn)

        self.setLayout(self.layout)

    def redraw(self, item):
        self._2min.setText(str(item['2min']))
        self._2max.setText(str(item['2max']))
        self._3min.setText(str(item['3min']))
        self._3max.setText(str(item['3max']))
        self._12min.setText(str(item['12min']))
        self._12max.setText(str(item['12max']))
        self._avgmin.setText(str(item['avgmin']))
        self._avgmax.setText(str(item['avgmax']))

        self._2min.repaint()
        self._2min.update()
        self._2max.repaint()
        self._2max.update()
        self._3min.repaint()
        self._3min.update()
        self._3max.repaint()
        self._3max.update()
        self._12min.repaint()
        self._12min.update()
        self._12max.repaint()
        self._12max.update()
        self._avgmin.repaint()
        self._avgmin.update()
        self._avgmin.repaint()
        self._avgmin.update()
        self._avgmax.repaint()
        self._avgmax.update()
        self._avgmax.repaint()
        self._avgmax.update()


    def _modify(self):
        self.modify.emit(str(self._name.text()), self.item)

    def _remove(self):
        self.remove.emit(str(self._name.text()))


class PresetEdit(QWidget):

    saveSignal = pyqtSignal(object)

    def __init__(self, name='', item=None, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 300
        self.height = 600
        self.colWidth = 80

        self.item = item

        self.data = {}

        self.modify = True if name != '' and name != False else False

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

        # _l.addWidget(__w, 0, 0, 1, 1, alignment=Qt.AlignCenter|Qt.AlignTop)
        # _l.addWidget(line, 1, 0, 1, 1, alignment=Qt.AlignCenter|Qt.AlignTop)
        # l.addWidget(addButton, alignment=Qt.AlignRight)

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/2. - self.height/2.)

        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)

        if self.modify:
            self.setWindowTitle("Modify Preset")
            self.title = QLabel('Modify Preset')
        else:
            self.setWindowTitle("New Preset")
            self.title = QLabel('Add New Preset')

        self.title.setStyleSheet('QLabel{color:#aaaaaa; font-size: 14px; margin-bottom: 20px;}')

        ttl = 'New'
        if name != '' and name != False:
            ttl = str(name)
        self.name = QLabel('Name')
        self.name_value = QLineEdit(ttl)
        self.name_value.setAlignment(Qt.AlignLeft)
        self.name_value.setFixedSize(150,28)
        self.name_value.setTextMargins(10, 1, 10, 1)
        if name != '' and name != False:
            self.name_value.setEnabled(False)
            self.name_value.setStyleSheet('QLineEdit{color: #f39c12}')

        self._2min = QLabel('2-Min')
        self._2min_value = QDoubleSpinBox()
        self._2min_value.setRange(0.,1.)
        self._2min_value.setDecimals(4)
        self._2min_value.setSingleStep(0.0001)
        self._2min_value.setMaximum( 1. )
        self._2min_value.setValue( 0.  if not self.modify else self.item['2min'] )
        self._2min_value.setFixedSize(150,28)

        self._2max = QLabel('2-Max')
        self._2max_value = QDoubleSpinBox()
        self._2max_value.setRange(0.,1.)
        self._2max_value.setDecimals(4)
        self._2max_value.setSingleStep(0.0001)
        self._2max_value.setMaximum(1.)
        self._2max_value.setValue( 1. if not self.modify else self.item['2max'] )
        self._2max_value.setFixedSize(150,28)

        self._3min = QLabel('3-Min')
        self._3min_value = QDoubleSpinBox()
        self._3min_value.setRange(0.,1.)
        self._3min_value.setDecimals(4)
        self._3min_value.setSingleStep(0.0001)
        self._3min_value.setMaximum(1.)
        self._3min_value.setValue( 0. if not self.modify else self.item['3min'] )
        self._3min_value.setFixedSize(150,28)

        self._3max = QLabel('3-Max')
        self._3max_value = QDoubleSpinBox()
        self._3max_value.setRange(0.,1.)
        self._3max_value.setDecimals(4)
        self._3max_value.setSingleStep(0.0001)
        self._3max_value.setMaximum(1.)
        self._3max_value.setValue( 1. if not self.modify else self.item['3max'] )
        self._3max_value.setFixedSize(150,28)

        self._12min = QLabel('12-Min')
        self._12min_value = QDoubleSpinBox()
        self._12min_value.setRange(0.,1.)
        self._12min_value.setDecimals(4)
        self._12min_value.setSingleStep(0.0001)
        self._12min_value.setMaximum(1.)
        self._12min_value.setValue( 0. if not self.modify else self.item['12min'] )
        self._12min_value.setFixedSize(150,28)

        self._12max = QLabel('12-Max')
        self._12max_value = QDoubleSpinBox()
        self._12max_value.setRange(0.,1.)
        self._12max_value.setDecimals(4)
        self._12max_value.setSingleStep(0.0001)
        self._12max_value.setMaximum(1.)
        self._12max_value.setValue( 1. if not self.modify else self.item['12max'] )
        self._12max_value.setFixedSize(150,28)

        self._avg_min = QLabel('Avg-Min')
        self._avg_min_value = QDoubleSpinBox()
        self._avg_min_value.setRange(0.,1.)
        self._avg_min_value.setDecimals(4)
        self._avg_min_value.setSingleStep(0.0001)
        self._avg_min_value.setMaximum(1.)
        self._avg_min_value.setValue( 0. if not self.modify else self.item['avgmin'] )
        self._avg_min_value.setFixedSize(150,28)

        self._avg_max = QLabel('Avg-Max')
        self._avg_max_value = QDoubleSpinBox()
        self._avg_max_value.setRange(0.,1.)
        self._avg_max_value.setDecimals(4)
        self._avg_max_value.setSingleStep(0.0001)
        self._avg_max_value.setMaximum(1.)
        self._avg_max_value.setValue( 1. if not self.modify else self.item['avgmax'] )
        self._avg_max_value.setFixedSize(150,28)

        self.saveBtn_margin = QLabel('')
        self.saveBtn_margin.setStyleSheet('height:25px;')
        self.saveBtn = QPushButton('Save')
        self.saveBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        self.saveBtn.setEnabled(True)
        self.saveBtn.setFixedSize(100,30)
        self.saveBtn.clicked.connect(self.save, Qt.DirectConnection)


        _l.addWidget(self.title, 0, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.name, 1, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.name_value, 1, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._2min, 2, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._2min_value, 2, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._2max, 3, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._2max_value, 3, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._3min, 4, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._3min_value, 4, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._3max, 5, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._3max_value, 5, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._12min, 6, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._12min_value, 6, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._12max, 7, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._12max_value, 7, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._avg_min, 8, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._avg_min_value, 8, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self._avg_max, 9, 0, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self._avg_max_value, 9, 1, alignment=Qt.AlignVCenter|Qt.AlignLeft)
        _l.addWidget(self.saveBtn_margin, 10, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)
        _l.addWidget(self.saveBtn, 11, 1, alignment=Qt.AlignVCenter|Qt.AlignRight)


        self.show()

    def save(self):
        self.data = {}
        self.data['name'] = str(self.name_value.text())
        self.data['2min'] = float(self._2min_value.value())
        self.data['2max'] = float(self._2max_value.value())
        self.data['3min'] = float(self._3min_value.value())
        self.data['3max'] = float(self._3max_value.value())
        self.data['12min'] = float(self._12min_value.value())
        self.data['12max'] = float(self._12max_value.value())
        self.data['avgmin'] = float(self._avg_min_value.value())
        self.data['avgmax'] = float(self._avg_max_value.value())
        self.saveSignal.emit(self.data)
        self.close()


class Presets(QWidget):

    send_presets_to_app = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_esc.activated.connect(self.close)

        self.width = 970
        self.colWidth = 80

        self.presets = {}
        self.presetItems = {}
        self.presetWidgetLine = 2

        w = QWidget()
        l = QVBoxLayout()
        self.setLayout(l)


        scroll = QScrollArea(w)

        __w = QWidget()
        title = QHBoxLayout()
        title.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        title.setContentsMargins(20, 0, 0, 0)
        title.setSpacing(0)
        for column in ['Name', '2-Min', '2-Max', '3-Min', '3-Max', '12-Min', '12-Max', 'Avg-Min', 'Avg-Max']:
            widget = QLabel(column)
            widget.setFixedWidth(self.colWidth)
            widget.setStyleSheet("QLabel{color:#cccccc}")
            widget.setAlignment(Qt.AlignCenter|Qt.AlignTop)
            title.addWidget(widget)
        __w.setLayout(title)

        line = QWidget()
        line.setFixedSize(80*9, 1)
        line.setStyleSheet("QWidget{background-color:#aaaaaa; text-align: left}")

        l.addWidget(__w)
        # l.addWidget(line)

        l.addWidget(scroll)
        scroll.setWidgetResizable(True)
        scrollContent = QWidget(scroll)
        scrollLayout = QVBoxLayout(scrollContent)
        scrollLayout.setAlignment(Qt.AlignTop)
        scrollContent.setLayout(scrollLayout)
        _w = QWidget()
        self._l = QGridLayout()
        self._l.setHorizontalSpacing(15)
        self._l.setVerticalSpacing(10)
        _w.setLayout(self._l)
        scrollLayout.addWidget(_w)
        scroll.setWidget(scrollContent)





        addButton = QPushButton('New')
        addButton.setStyleSheet("QPushButton {background-color: #f39c12; color: #2a2a2a; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        addButton.setEnabled(True)
        addButton.setFixedSize(100,30)
        addButton.clicked.connect(self.add, Qt.DirectConnection)

        okButton = QPushButton('Ok')
        okButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #eeeeee; font-weight: bold; border: 1px solid #2a2a2a; font-size: 15px;}")
        okButton.setEnabled(True)
        okButton.setFixedSize(100,30)
        okButton.clicked.connect(self.ok, Qt.DirectConnection)

        btnPannel = QHBoxLayout()
        btnPannel.addWidget(okButton)
        btnPannel.addWidget(addButton)
        btnPannel.setAlignment(Qt.AlignRight)

        # self._l.addWidget(__w, 0, 0, 1, 1, alignment=Qt.AlignLeft|Qt.AlignTop)
        # self._l.addWidget(line, 1, 0, 1, 1, alignment=Qt.AlignLeft|Qt.AlignTop)
        l.addLayout(btnPannel)

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.move(self.screenWidth/2. - self.width/2., self.screenHeight/7.)

        self.setFixedWidth(self.width)
        self.setFixedHeight(self.screenHeight*.75)

        self.setWindowTitle("Strategy Presets")

        self.load_presets()

    def ok(self):
        self.close()

    def load_presets(self):
        self.presets = {}
        filename = '{}{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/', 'presets.json' )
        if os.path.isfile(filename):
            with open(filename) as f:
                self.presets = json.load(f)

        for name, item in self.presets.items():
            self.presets[name] = item
            presetItem = PresetItem(item)
            presetItem.modify.connect(self.modify, Qt.DirectConnection)
            presetItem.remove.connect(self.remove, Qt.DirectConnection)
            self.presetItems[name] = presetItem
            self._l.addWidget(presetItem, self.presetWidgetLine, 0, 1, 1, alignment=Qt.AlignLeft|Qt.AlignTop)
            self.presetWidgetLine += 1


    def save_presets(self):
        path = '{}{}'.format( os.path.dirname(os.path.abspath(__file__)), '/config/' )
        if not os.path.isdir(path): os.mkdir(path)
        fileName = '{}{}'.format(path, 'presets.json')
        with open(fileName, 'w') as f:
            f.write(json.dumps(self.presets))
        self.send_presets_to_app.emit(self.presets)


    def new_item_received(self, data):

        item = {
            'name' : data['name'],
            '2min' : round(data['2min'], 4),
            '2max' : round(data['2max'], 4),
            '3min' : round(data['3min'], 4),
            '3max' : round(data['3max'], 4),
            '12min' : round(data['12min'], 4),
            '12max' : round(data['12max'], 4),
            'avgmin' : round(data['avgmin'], 4),
            'avgmax' : round(data['avgmax'], 4)
        }

        if data['name'] in self.presets:
            name = data['name']
            self.presetItems[name].redraw(item)
            self.presetItems[name].item = item
        else:
            presetItem = PresetItem(item)
            presetItem.modify.connect(self.modify, Qt.DirectConnection)
            presetItem.remove.connect(self.remove, Qt.DirectConnection)
            self.presetItems[data['name']] = presetItem
            self._l.addWidget(presetItem, self.presetWidgetLine, 0, 1, 1, alignment=Qt.AlignLeft|Qt.AlignTop)
            self.presetWidgetLine += 1

        self.presets[data['name']] = item
        self.save_presets()

    def modify(self, name, item):
        self.add(name=name, item=item)

    def remove(self, name):
        self.presetItems[name].deleteLater()
        self.presetItems.pop(name, None)
        self.presets.pop(name, None)
        self.save_presets()

    def add(self, name='New', item=None):
        self.preset = PresetEdit(name=name, item=item, parent=None)
        self.preset.saveSignal.connect(self.new_item_received, Qt.DirectConnection)
