from PyQt5.QtWidgets import QMessageBox, QLabel, QDialogButtonBox, QPushButton, QDesktopWidget, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QPoint


class CustomMessageBox(QMessageBox):
    def __init__(self, error=False):
        QMessageBox.__init__(self)
        self.error = error

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

        # self.move(int(left+width/2.-150),int(top+height/2.-62))

    def event(self, e):
        result = QMessageBox.event(self, e)

        self.setMinimumWidth(300)
        min_height = 125 if not self.error else 250
        self.setMinimumHeight(min_height)

        return result


class InfoMessageBox(CustomMessageBox):
    def __init__(self, title, txt, error=False):
        CustomMessageBox.__init__(self, error)

        okButton  = QPushButton('OK')
        okButton.setFixedSize(100,30)

        self.addButton(okButton, QMessageBox.AcceptRole)
        self.setWindowTitle(title)
        self.setText(txt)
        self.reinit(self.frameGeometry())
        self.move(QDesktopWidget().availableGeometry().center() - QPoint(100,30))
        ret = self.exec_()

class InfoWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)
        self.move(QDesktopWidget().availableGeometry().center() - QPoint(100,30))
        self.setMinimumWidth(350)
        # self.setMinimumHeight(100)
        self.setWindowTitle('Status')

    def appendMsg(self, msg):
        _msg = QLabel(msg)
        _msg.setStyleSheet('color: #eeeeee;')
        self.layout.addWidget(_msg)
        super().update()


    def show(self):
        super().show()




class StatusMessageBox(CustomMessageBox):
    def __init__(self, title="Status"):
        CustomMessageBox.__init__(self)

        self.setMinimumWidth(350)
        self.setMinimumHeight(150)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self.setWindowTitle(title)
        self.reinit(self.frameGeometry())
        self.move(QDesktopWidget().availableGeometry().center() - QPoint(100,30))
        ret = self.exec_()


    def addInfo(self, info):
        label = QLabel(info)
        self._layout.addWidget(label)
        self._layout.update()
