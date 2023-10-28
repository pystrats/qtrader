import threading, time

import logging
import queue

logger = logging.getLogger(__name__)

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

from ibapi import (decoder, reader, comm)
from ibapi.utils import (current_fn_name, BadMessage)

from customClient import CustomEClient

MAX_MSG_LEN = 1024


class QTraderConnection(EWrapper, CustomEClient):
    def __init__(self):
        # EWrapper.__init__(self)
        EClient.__init__(self, self)

        '''
        self.port = 4002
        self.reg_only = True
        self.host = '127.0.0.1'
        self.clientID = 1
        '''

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

    def _run(self):
        """This is the function that has the message loop."""

        try:
            while self.isConnected() or not self.msg_queue.empty():
                try:
                    try:
                        text = self.msg_queue.get(block=True, timeout=1.0)
                        if len(text) > MAX_MSG_LEN:
                            # self.wrapper.error(NO_VALID_ID, BAD_LENGTH.code(),
                            #     "%s:%d:%s" % (BAD_LENGTH.msg(), len(text), text))
                            break
                    except queue.Empty:
                        logger.debug("queue.get: empty")
                        self.msgLoopTmo()
                    else:
                        fields = comm.read_fields(text)
                        logger.debug("fields %s", fields)
                        self.decoder.interpret(fields)
                        self.msgLoopRec()
                except (KeyboardInterrupt, SystemExit):
                    logger.info("detected KeyboardInterrupt, SystemExit")
                    self.keyboardInterrupt()
                    self.keyboardInterruptHard()
                except BadMessage:
                    logger.info("BadMessage")

                logger.debug("conn:%d queue.sz:%d",
                             self.isConnected(),
                             self.msg_queue.qsize())
        finally:
            self.disconnect()


class Singleton(type):
    def __init__(cls, name, bases, dct):
        super(Singleton, cls).__init__(name, bases, dct)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

"""
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
        # print("Initiating connection")
        self.connect(self.host, self.port, self.clientID)
        time.sleep(1.5)
        self.thread = threading.Thread(target=self.run_process(self), daemon=True)
        self.thread.start()

    # def disconnect(self):
    #     self.disconnect()

    @staticmethod
    def run_process(self):
        self.run()

"""

"""
XRDP @ Centos 7
https://serverspace.us/support/help/installing-the-gnome-gui-on-centos-7/
https://bobcares.com/blog/how-to-install-xrdp-on-centos-7-or-rhel-7/

Fedora
https://tecadmin.net/how-to-install-xrdp-on-fedora/
https://stackoverflow.com/questions/29683510/linux-chcon-cant-apply-partial-context-to-unlabeled-file

 
sudo chcon -h system_u:object_r:httpd_sys_content_t /usr/sbin/xrdp
instead of
sudo chcon --type=bin_t /usr/sbin/xrdp

"""