from PyQt5.QtCore import QObject, pyqtSignal

from time import sleep


class Reconnector(QObject):
    TIMEOUT_BETWEEN_CONNECTION_ATTEMPTS_SECONDS = 3
    MAX_RECONNECTION_ATTEMPTS = 6
    isConnected = False

    log = pyqtSignal(str, str)
    reconnectSignal = pyqtSignal()
    terminateSelf = pyqtSignal()

    def reconnect(self):
        attemptNumber = 1
        while attemptNumber <= self.MAX_RECONNECTION_ATTEMPTS and not self.isConnected:
            # self.log.emit('info', 'Reestablishing connection. Attempt {}'.format(attemptNumber))
            print('Reconnecting')
            self.reconnectSignal.emit()
            sleep(self.TIMEOUT_BETWEEN_CONNECTION_ATTEMPTS_SECONDS)
            attemptNumber += 1
        if not self.isConnected: self.log.emit('info', 'Giving up trying to reestablish connection')
        self.terminateSelf.emit()

