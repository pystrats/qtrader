import threading, time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order


class Connection(EWrapper, EClient):
    def __init__(self, host='127.0.0.1', port=7497, clientID=1):
        # EWrapper.__init__(self)
        EClient.__init__(self, self)

        self.port = 4002
        self.reg_only = True
        self.host = '127.0.0.1'
        self.clientID = 1

        self.connectionEstablished = False


    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        # print("Error {} {} {}".format(reqId,errorCode,errorString))
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)

    # def connect(self, host, port, clientID):
    #     EClient.connect(self, host, port, clientID)

    # def run(self):
    #     print('Starting program')
    #     self.run()
    #     print('Program started')

    # def error(self, reqId, errorCode, errorString):
    #     super().error(reqId, errorCode, errorString)


class Singleton(type):
    def __init__(cls, name, bases, dct):
        super(Singleton, cls).__init__(name, bases, dct)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class Trader(Connection):

    def __init__(self):
        super().__init__('127.0.0.1', 7497, 0)
        self.port = 7497
        self.reg_only = True
        self.host = '127.0.0.1'
        self.clientID = 0


    # def clientID(self):
    #     return random.randint(1, pow(2, 16) - 1)

    def initiate_connection(self):
        print("Initiating connection")
        self.connect(self.host, self.port, self.clientID)
        time.sleep(1.5)
        self.thread = threading.Thread(target=self.run_process(self), daemon=True)
        self.thread.start()

    # def disconnect(self):
    #     self.disconnect()

    @staticmethod
    def run_process(self):
        self.run()
