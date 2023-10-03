from PyQt5.QtCore import Qt, pyqtSlot, QObject, QThread, pyqtSignal
from time import sleep
from datetime import datetime
import numpy as np


class Downloader(QObject):
    finished = pyqtSignal()
    statusMag = pyqtSignal(str)
    subscribe = pyqtSignal(int, object)
    data_status_update = pyqtSignal(str)
    cancel_request = pyqtSignal(int)
    status_change = pyqtSignal(int, str)
    api_data_request = pyqtSignal(int, str, bool, object)
    log = pyqtSignal(str, str)
    start_signal = pyqtSignal()
    update_hist_request_time = pyqtSignal()
    download_sequence_finished = pyqtSignal(object, object,  object)

    MAX_SUBSCRIPTION_REQUESTS_PER_SECOND = 10
    MAX_SIMULTANEOUS_HIST_DATA_CONNECTIONS = 10
    MAX_TIMEOUT_SECONDS = 240

    MIN_DATAPOINTS_REQUIRED = 100 # 2680
    HISTORY_EXCESS_TO_LOAD_PERCENT = 30
    TIMEFRAME = 1
    MIN_1MIN_HISTORY_BARS_REQUIRED = MIN_DATAPOINTS_REQUIRED

    reqId = 1000000

    def receive_watchlist(self, watchlist):
        self.watchlist = watchlist

    def receive_datapoint_requirement(self, min_datapoints_required, hist_excess):
        self.MIN_DATAPOINTS_REQUIRED = min_datapoints_required
        self.HISTORY_EXCESS_TO_LOAD_PERCENT = hist_excess

    def receive_settings(self, settings):
        self.settings = settings
        self.TIMEFRAME = int(self.settings['strategy']['timeframe'])
        self.MIN_1MIN_HISTORY_BARS_REQUIRED = int(self.TIMEFRAME * self.MIN_DATAPOINTS_REQUIRED * (100 + self.HISTORY_EXCESS_TO_LOAD_PERCENT)/100.)

    def subscribe_to_streaming(self, reqId, contractDescription):
        self.subscribe.emit(reqId, contractDescription)

    def insert_brownian_motion(self, position):
        normal = np.cumsum(np.random.normal(size=self.MIN_1MIN_HISTORY_BARS_REQUIRED))
        normal = normal + min(normal) * -1. + 1.
        self.closes[position] = list(normal)

    def request_historical_data(self, reqId, endDateTime, RTH_only, contract):
        self.api_data_request.emit(reqId, endDateTime, RTH_only, contract)

    def data_received(self, reqId, bar):
        n = self.reqIds.index(reqId)
        self.temp_timestamps[n].insert(0, bar.date)
        self.temp_closes[n].insert(0, bar.close)


    def subscribe_to_streaming_data_by_index(self, n):
        reqId = list(self.watchlist)[n]
        contractDescription = self.watchlist[reqId]
        symbol = contractDescription.contract.symbol
        self.statusMag.emit('Subscribing to streaming data {}'.format(symbol))
        self.log.emit('info', 'Subscribing to streaming data {}'.format(symbol))
        self.subscribe_to_streaming(reqId, contractDescription)


    def data_end(self, reqId, start, end):
        n = self.reqIds.index(reqId)
        self.timestamps[n] += self.temp_timestamps[n]
        self.closes[n] += self.temp_closes[n]
        self.last_timestamp[n] = start
        if len(self.closes[n]) >= self.MIN_1MIN_HISTORY_BARS_REQUIRED:
            self.finished[n] = True
            self.success[n] = True
            self.status_change.emit( list(self.watchlist)[n] , 'ready')
        self.active_requests[n] = False
        self.active_connections -= 1
        for n in range(len(self.temp_timestamps)):
            self.temp_timestamps[n] = []
            self.temp_closes[n] = []
        # self.subscribe_to_streaming_data_by_index(n)
        self.next_historical_data()


    def next_historical_data(self):

        for n in range(self.nSymbols):
            if not self.finished[n] and not self.active_requests[n]:
                self.request_historical_data(self.reqId, self.last_timestamp[n], self.settings['strategy']['onlyRTH_history'], self.watchlist[list(self.watchlist)[n]].contract)
                self.status_change.emit( list(self.watchlist)[n] , 'loading')
                self.active_requests[n] = True
                self.req_times[n] = datetime.now()
                self.reqIds[n] = self.reqId
                contract = self.watchlist[list(self.watchlist)[n]].contract
                logMsg = 'Requesting historical data {} {} {} {} {} {} {} {}'.format(
                    contract.symbol,
                    contract.exchange,
                    contract.primaryExchange,
                    contract.currency,
                    contract.secType,
                    contract.conId,
                    self.last_timestamp[n],
                    self.reqId )
                self.log.emit('info', logMsg)
                self.reqId += 1
                self.active_connections += 1
                self.update_hist_request_time.emit()
                return
        if sum(self.finished) == len(self.finished):
            self.subscribe_to_all_streaming()
            self.finalize()


    def finalize(self):
        self.data_status_update.emit('ready')
        self.download_sequence_finished.emit(self.success, self.timestamps, self.closes)
        # self.status_change.emit( list(self.watchlist)[n] , 'ready')

    def start_downloader(self):
        self.start_signal.emit()

    def stop_forcefully(self):
        for n in range(self.nSymbols):
            if not self.success[n]:
                self.cancel_request.emit(self.reqIds[n])
                self.insert_brownian_motion(n)
                self.finished[n] = True
                self.status_change.emit( list(self.watchlist)[n] , 'failed')

        self.subscribe_to_all_streaming()
        self.finalize()


    def initiate(self):
        self.symbols, self.active_requests = [], []
        self.finished = []
        self.req_times = []
        self.reqIds = []
        self.timestamps, self.closes = [], []
        self.temp_timestamps, self.temp_closes = [], []
        self.success = []
        self.last_timestamp = []
        self.active_connections = 0
        self.nSymbols = 0
        for reqId in self.watchlist.keys():
            self.symbols.append(self.watchlist[reqId].contract.symbol)
            self.active_requests.append(False)
            self.timestamps.append([])
            self.closes.append([])
            self.temp_timestamps.append([])
            self.temp_closes.append([])
            self.finished.append(False)
            self.req_times.append(0)
            self.reqIds.append(0)
            self.success.append(False)
            self.last_timestamp.append('')
            self.nSymbols += 1
        if len(self.watchlist) == 0:
            self.finalize()
        else: self.data_status_update.emit('loading')

    def subscribe_to_all_streaming(self):
        n = 0
        for reqId, contractDescription in self.watchlist.items():
            if n < len(self.success) and self.success[n]:
                contract = self.watchlist[reqId].contract
                self.statusMag.emit('Subscribing to streaming data [{}]...'.format(self.watchlist[reqId].contract.symbol))
                logMsg = 'Subscribing to streaming data {} {} {} {} {} {} {}'.format(
                    contract.symbol,
                    contract.exchange,
                    contract.primaryExchange,
                    contract.currency,
                    contract.secType,
                    contract.conId,
                    reqId )
                self.log.emit('info', logMsg)
                self.subscribe.emit(reqId, contractDescription)
                sleep(1./self.MAX_SUBSCRIPTION_REQUESTS_PER_SECOND)
            n += 1
        self.statusMag.emit('')

    def first_historical_data(self):
        n = 0
        for finished in self.finished:
            if not finished:
                if not self.active_requests[n]:
                    if self.active_connections <  self.MAX_SIMULTANEOUS_HIST_DATA_CONNECTIONS:
                        self.status_change.emit( list(self.watchlist)[n] , 'loading')
                        self.request_historical_data(self.reqId, self.last_timestamp[n], self.settings['strategy']['onlyRTH_history'], self.watchlist[list(self.watchlist)[n]].contract)
                        self.active_requests[n] = True
                        self.req_times[n] = datetime.now()
                        self.reqIds[n] = self.reqId
                        contract = self.watchlist[list(self.watchlist)[n]].contract
                        logMsg = 'Requesting historical data {} {} {} {} {} {} {} {}'.format(
                            contract.symbol,
                            contract.exchange,
                            contract.primaryExchange,
                            contract.currency,
                            contract.secType,
                            contract.conId,
                            self.last_timestamp[n],
                            self.reqId )
                        self.log.emit('info', logMsg)
                        self.reqId += 1
                        self.active_connections += 1
            n += 1

    def connected(self):
        return


        ready = False
        active_connections = 0
        while not ready:
            n = 0
            for finished in self.finished:
                if not finished:
                    if not self.active_requests[n]:
                        if active_connections <  self.MAX_SIMULTANEOUS_HIST_DATA_CONNECTIONS:
                            self.status_change.emit( list(self.watchlist)[n] , 'loading')
                            self.request_historical_data(self.reqId, self.last_timestamp[n], self.settings['strategy']['onlyRTH_history'], self.watchlist[list(self.watchlist)[n]].contract)
                            self.active_requests[n] = True
                            self.req_times[n] = datetime.now()
                            self.reqIds[n] = self.reqId
                            contract = self.watchlist[list(self.watchlist)[n]].contract
                            logMsg = 'Requesting historical data {} {} {} {} {} {}'.format(
                                contract.symbol,
                                contract.exchange,
                                contract.primaryExchange,
                                contract.currency,
                                contract.secType,
                                contract.conId )
                            self.log.emit('info', logMsg)
                            self.reqId += 1
                    else:
                        if (datetime.now() - self.req_times[n]).seconds > self.MAX_TIMEOUT_SECONDS:
                            self.cancel_request.emit(self.reqIds[n])
                            self.insert_brownian_motion(n)
                            self.finished[n] = True
                            self.success[n] = False
                            self.status_change.emit( list(self.watchlist)[n] , 'failed')

                n += 1
            if sum(self.finished) == len(self.finished): ready = True
            sleep(1)

        # Subscribe to streaming data
        self.data_status_update.emit('loading')


        self.statusMag.emit('')
