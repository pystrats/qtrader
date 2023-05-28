import json
from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
from time import sleep

API_KEY = "<API_KEY>"

class SuggestionPlaceModel(QtGui.QStandardItemModel):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    dataRequest = QtCore.pyqtSignal(str, int)
    dataRequestFinished = False
    data = {}
    # the second argument specifies request origin, autocompleter = 1

    def __init__(self, parent=None):
        super(SuggestionPlaceModel, self).__init__(parent)
        self._manager = QtNetwork.QNetworkAccessManager(self)
        self._reply = None

    @QtCore.pyqtSlot(str)
    def search(self, text):
        self.clear()
        if self._reply is not None:
            self._reply.abort()
        if text:
            print(text)
            self.create_request(text)
            # self._reply = self._manager.get(r)
            # self._reply = r
            self.on_finished()
        loop = QtCore.QEventLoop()
        self.finished.connect(loop.quit)
        loop.exec_()

    def dataReceived(self, data):
        self.dataRequestFinished = True
        self.data = data


    def create_request(self, text):
        self.dataRequestFinished = False
        self.data = {}
        self.dataRequest.emit(text, 1)

        # url = QtCore.QUrl("https://maps.googleapis.com/maps/api/place/autocomplete/json")
        # query = QtCore.QUrlQuery()
        # query.addQueryItem("key", API_KEY)
        # query.addQueryItem("input", text)
        # query.addQueryItem("types", "geocode")
        # query.addQueryItem("language", "en")
        # url.setQuery(query)
        # request = QtNetwork.QNetworkRequest(url)

        # return self.data

    @QtCore.pyqtSlot()
    def on_finished(self):
        reply = self.sender()

        for symbol in self.data.keys():
            self.appendRow(QtGui.QStandardItem( '{} {} {} {} {}'.format(
                self.data[symbol]['symbol'],
                self.data[symbol]['exchange'],
                self.data[symbol]['currency'],
                self.data[symbol]['secType'],
                self.data[symbol]['ID']
            )))

        # if reply.error() == QtNetwork.QNetworkReply.NoError:
        #     data = json.loads(reply.readAll().data())
        #     if data['status'] == 'OK':
        #         for prediction in data['predictions']:
        #             self.appendRow(QtGui.QStandardItem(prediction['description']))
        #     self.error.emit(data['status'])

        self.finished.emit()
        reply.deleteLater()
        self._reply = None

class Completer(QtWidgets.QCompleter):
    def splitPath(self, path):
        self.model().search(path)
        return super(Completer, self).splitPath(path)

class LineCompleterWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LineCompleterWidget, self).__init__(parent)
        self._model = SuggestionPlaceModel(self)
        completer = Completer(self, caseSensitivity=QtCore.Qt.CaseInsensitive)
        completer.setModel(self._model)
        lineedit = QtWidgets.QLineEdit()
        lineedit.setCompleter(completer)
        label = QtWidgets.QLabel()
        self._model.error.connect(label.setText)
        lay = QtWidgets.QFormLayout(self)
        lay.addRow("Location: ", lineedit)
        lay.addRow("Error: ", label)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = Widget()
    w.resize(400, w.sizeHint().height())
    w.show()
    sys.exit(app.exec_())
