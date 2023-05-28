from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QApplication, QLineEdit, QShortcut, QLabel
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QKeySequence

import plotly.graph_objects as go
import plotly.express as px

import pandas as pd
from datetime import datetime
import os
import time

from ibapi.contract import Contract

from search import SearchWindow
from msgboxes import InfoMessageBox


class WebPage(QWebEnginePage):
    def __init__(self, root_url):
        super(WebPage, self).__init__()
        self.root_url = root_url

    def home(self):
        self.load(QUrl(self.root_url))

    def acceptNavigationRequest(self, url, kind, is_main_frame):
        """Open external links in browser and internal links in the webview"""
        ready_url = url.toEncoded().data().decode()
        is_clicked = kind == self.NavigationTypeLinkClicked
        if is_clicked and self.root_url not in ready_url:
            QDesktopServices.openUrl(url)
            return False
        return super(WebPage, self).acceptNavigationRequest(url, kind, is_main_frame)


class Chart(QWidget):

    transmitWindowSize = pyqtSignal(int, int)
    resized = pyqtSignal()
    amIConnected = pyqtSignal()
    lookupRequest = pyqtSignal(str, str)
    requestHistData = pyqtSignal(int, object, str)
    tellDashToChangeState = pyqtSignal(str)
    sendDataToDash = pyqtSignal(object, str)
    quitDash = pyqtSignal()

    isConnected = False
    lookupQuery = ''
    histDataReqId = 10000

    contractDescription = Contract()
    period = 'daily'


    def __init__(self, parent=None):
        super().__init__(parent)

        self.activeSymbol = 'MSFT'
        self.activeExchange = 'NYSE'
        self.activePrice = 135.35
        self.newSymbol = ''
        self.newExchange = ''

        self.controlPanelHeight = 35
        self.leftControlPanel = QHBoxLayout()
        self.lookupButton = QPushButton('Lookup', self)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff; margin-right: 0px;}")
        self.lookupButton.setFixedSize(100, 25)
        self.symbolInfoPanel = QHBoxLayout()
        self.symbolName = QLabel(self.activeSymbol)
        self.symbolName.setFixedHeight(self.controlPanelHeight)
        self.symbolName.setStyleSheet("QLabel {font-size: 20px; font-weight: bold; color: #eeeeee;}")
        self.symbolExchange = QLabel(self.activeExchange)
        self.symbolExchange.setFixedHeight(self.controlPanelHeight)
        self.symbolExchange.setStyleSheet("QLabel {font-size: 14px; font-weight: normal; color: #aaaaaa; margin-bottom: 5px;}")
        self.symbolPrice = QLabel(str(self.activePrice))
        self.symbolPrice.setFixedHeight(self.controlPanelHeight)
        self.symbolPrice.setStyleSheet("QLabel {font-size: 16px; font-weight: normal; color: #eeeeee;}")
        self.symbolName.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.symbolExchange.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.symbolPrice.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.symbolSerachText = QLineEdit()
        self.symbolSerachText.setMaxLength(30)
        self.symbolSerachText.setAlignment(Qt.AlignLeft)
        self.symbolSerachText.setFixedSize(250,25)
        self.symbolSerachText.setTextMargins(10, 1, 10, 1)

        self.leftControlPanelSpacer = QLabel('')
        self.leftControlPanelSpacer.setFixedWidth(35)

        self.periodWeeklyBtn = QPushButton('Weekly', self)
        self.periodWeeklyBtn.setFixedSize(75, 25)
        self.periodWeeklyBtn.setEnabled(False)

        self.periodDailyBtn = QPushButton('Daily', self)
        # self.periodDailyBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.periodDailyBtn.setFixedSize(75, 25)
        self.periodDailyBtn.setEnabled(True)

        self.period1HBtn = QPushButton('1 hour', self)
        # self.period1HBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.period1HBtn.setFixedSize(75, 25)
        self.period1HBtn.setEnabled(False)

        self.period30minBtn = QPushButton('30 min', self)
        # self.period30minBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.period30minBtn.setFixedSize(75, 25)
        self.period30minBtn.setEnabled(False)

        self.period5minBtn = QPushButton('5 min', self)
        # self.period5minBtn.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.period5minBtn.setFixedSize(75, 25)
        self.period5minBtn.setEnabled(False)

        self.leftControlPanel.addWidget(self.symbolSerachText)
        self.leftControlPanel.addWidget(self.lookupButton)
        self.leftControlPanel.addWidget(self.leftControlPanelSpacer)
        self.leftControlPanel.addWidget(self.periodWeeklyBtn)
        self.leftControlPanel.addWidget(self.periodDailyBtn)
        self.leftControlPanel.addWidget(self.period1HBtn)
        self.leftControlPanel.addWidget(self.period30minBtn)
        self.leftControlPanel.addWidget(self.period5minBtn)

        self.symbolInfoPanel.addWidget(self.symbolName)
        self.symbolInfoPanel.addWidget(self.symbolExchange)
        self.symbolInfoPanel.addWidget(self.symbolPrice)



        self.lookupButton.clicked.connect(self.openSearchWindow)
        self.periodWeeklyBtn.clicked.connect(self.getDataWeekly)
        self.periodDailyBtn.clicked.connect(self.getDataDaily)
        self.period1HBtn.clicked.connect(self.getData1H)
        self.period30minBtn.clicked.connect(self.getData30min)
        self.period5minBtn.clicked.connect(self.getData5min)


        self.shortcut_close = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.shortcut_close.activated.connect(self.closeWindow)

        self.browser = QWebEngineView(self)
        self.port = 8050

        self.controlPanelWidget = QWidget()
        self.controlPanel = QGridLayout()
        self.controlPanel.addLayout(self.leftControlPanel, 0, 0, alignment=Qt.AlignLeft|Qt.AlignVCenter)
        self.controlPanel.addLayout(self.symbolInfoPanel, 0, 1, alignment=Qt.AlignRight|Qt.AlignVCenter)
        self.controlPanelWidget.setLayout(self.controlPanel)
        self.controlPanelWidget.setFixedHeight(self.controlPanelHeight)



        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.controlPanelWidget, stretch=1)
        vlayout.addWidget(self.browser, stretch=1)
        vlayout.setContentsMargins(0, 0, 0, 0)

        self.screen = QApplication.primaryScreen()
        self.screenWidth = self.screen.size().width()
        self.screenHeight = self.screen.size().height()
        self.chartToScreenRatio = .8
        self.browserWidth = self.screenWidth
        self.browserHeight = self.screenHeight - self.controlPanelHeight

        # self.lookupButton.clicked.connect(self.show_graph)
        # Use self.resize() instead of self.setFixedSize() to enable resizing
        self.resize(int(self.chartToScreenRatio*self.screenWidth), int(self.chartToScreenRatio*self.screenHeight))
        self.move(int((1.-self.chartToScreenRatio)*self.screenWidth/4.),  int((1.-self.chartToScreenRatio)*self.screenHeight/2.))
        self.setWindowTitle("Chart")

        self.width  = self.frameGeometry().width()
        self.height = self.frameGeometry().height()


    def openSearchWindow(self):
        self.disable_lookup_button()
        self.amIConnected.emit()
        if not self.isConnected:
            msgBox = InfoMessageBox('Error', 'Please establish connection')
            self.enable_lookup_button()
        elif self.symbolSerachText.text() == '':
            msgBox = InfoMessageBox('Error', 'Request cannot be empty')
            self.enable_lookup_button()
        else:
            self.lookupQuery = self.symbolSerachText.text()
            self.lookupRequest.emit(self.lookupQuery, 'chart')
            self.symbolSerachText.setText('')

    def lookupResultsReceived(self, code, contractDescriptions):
        if code == 1:
            self.lookupWindow = SearchWindow(self.lookupQuery, contractDescriptions, 'chart')
            self.lookupWindow.sendContractToChart.connect(self.getHistData, Qt.DirectConnection)
            self.lookupWindow.show()
        else: msgBox = InfoMessageBox('Error', 'Lookup request failed')
        self.enable_lookup_button()

    def getDataWeekly(self):
        self.getHistData(self.contractDescription, 'weekly')
    def getDataDaily(self):
        self.getHistData(self.contractDescription, 'daily')
    def getData1H(self):
        self.getHistData(self.contractDescription, '1H')
    def getData30min(self):
        self.getHistData(self.contractDescription, '30min')
    def getData5min(self):
        self.getHistData(self.contractDescription, '5min')

    def getHistData(self, contractDescription, period):

        self.periodWeeklyBtn.setEnabled(False)
        self.periodDailyBtn.setEnabled(False)
        self.period1HBtn.setEnabled(False)
        self.period30minBtn.setEnabled(False)
        self.period5minBtn.setEnabled(False)
        self.contractDescription = contractDescription
        self.period = period if period != 'unspecified' else self.period
        self.histDataReqId += 1
        self.requestHistData.emit(self.histDataReqId, contractDescription, self.period)
        self.newSymbol = contractDescription.contract.symbol.upper()
        self.newExchange = contractDescription.contract.primaryExchange.upper()
        self.tellDashToChangeState.emit('loading_data')

    def newDataReceived(self, data):
        self.sendDataToDash.emit(data, self.period)
        self.activeSymbol = self.newSymbol
        self.activeExchange = self.newExchange
        self.activePrice = data['Close'][-1]
        if self.period != 'weekly':
            self.periodWeeklyBtn.setEnabled(True)
        else: self.periodWeeklyBtn.setEnabled(False)
        if self.period != 'daily':
            self.periodDailyBtn.setEnabled(True)
        else: self.periodDailyBtn.setEnabled(False)
        if self.period != '1H':
            self.period1HBtn.setEnabled(True)
        else: self.period1HBtn.setEnabled(False)
        if self.period != '30min':
            self.period30minBtn.setEnabled(True)
        else: self.period30minBtn.setEnabled(False)
        if self.period != '5min':
            self.period5minBtn.setEnabled(True)
        else: self.period5minBtn.setEnabled(False)
        self.updateSymbolLabel()

    def updateSymbolLabel(self):
        self.symbolName.setText(self.activeSymbol)
        self.symbolExchange.setText(self.activeExchange)
        self.symbolPrice.setText(str(self.activePrice))

    def updateConnectionStatus(self, status):
        self.isConnected = status

    def resizeEvent(self, event):
        self.resized.emit()
        return super(Chart, self).resizeEvent(event)

    def enable_lookup_button(self):
        self.lookupButton.setEnabled(True)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #4a4a4a; color: #ffffff}")
        self.lookupButton.setText('Lookup')

    def disable_lookup_button(self):
        self.lookupButton.setEnabled(False)
        self.lookupButton.setStyleSheet("QPushButton {background-color: #3a3a3a; color: #6a6a6a}")
        self.lookupButton.setText('Please wait...')


    def get_browser_size(self):
        self.geometry = self.frameGeometry()
        self.width = self.geometry.width()
        self.height = self.geometry.height()
        self.browserWidth = self.width
        self.browserHeight = self.height - self.controlPanelHeight
        self.transmitWindowSize.emit(self.browserWidth, self.browserHeight)


    def closeWindow(self):
        self.close()

    def close(self):
        # self.quitDash.emit()
        super().close()

    def show_graph(self):

        self.page = WebPage('http://localhost:{}'.format(self.port))
        self.page.home()
        self.page.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
        self.browser.setPage(self.page)
        self.show()


        """
        dir = os.path.dirname(os.path.abspath(__file__))
        df = pd.read_csv(dir+'/finance-charts-apple.csv')
        fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                open=df['AAPL.Open'],
                high=df['AAPL.High'],
                low=df['AAPL.Low'],
                close=df['AAPL.Close']
                # increasing_line_color= '#aaaaaa', decreasing_line_color= '#f39c12'
                )])
        fig.update_layout(plot_bgcolor="#2c3e50",
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="#2c3e50")

        fig.update_xaxes(
        rangeslider_visible=True,
        rangebreaks=[dict(bounds=["sat", "mon"])
                # NOTE: Below values are bound (not single values), ie. hide x to y
                # dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
                # dict(bounds=[16, 9.5], pattern="hour"),  # hide hours outside of 9.30am-4pm
                # dict(values=["2019-12-25", "2020-12-24"])  # hide holidays (Christmas and New Year's, etc)
                ],
        spikesnap='cursor'
            )
        # fig.update_xaxes(
        #         mirror=True,
        #         ticks='outside',
        #         showline=True,
        #         linecolor='black',
        #         gridcolor='lightgrey')
        # fig.update_yaxes(
        #         mirror=False,
        #         showline=False,
        #         linecolor='black',
        #         gridcolor='lightgrey',
        #         spikesnap='cursor')
        fig.update_layout({'plot_bgcolor': "#21201f", 'paper_bgcolor': "#21201f", 'legend_orientation': "h"},
                  legend=dict(y=1, x=0),
                  font=dict(color='#dedddc'), dragmode='pan', hovermode='x unified',
                  margin=dict(b=0, t=0, l=0, r=0))
        fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False,
                 showspikes=True, spikemode='across', spikesnap='cursor', showline=False, spikedash='dash')
        fig.update_xaxes(showgrid=False, zeroline=False, rangeslider_visible=False, showticklabels=False,
                 showspikes=True, spikemode='across', spikesnap='cursor', showline=False, spikedash='dash')
        fig.update_layout(hoverdistance=0)
        self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))
        """




"""



import dash
from dash import Output, Input, State, dcc, html
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import datetime

class CGraphs:
    def makeCandlestick(self, aSymbolName:str):
        #  Warning, this function reads from disk, so it is slow.
        # print(sys._getframe().f_code.co_name, ": Started. aSymbolName ", aSymbolName)

        # downloader : CDownloader = CDownloader()

        # df_ohlc : pd.DataFrame = downloader.GetHistoricalData(aSymbolName)
        ## load some similar stock data

        df_ohlc = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv')
        df_ohlc.rename(columns=dict(zip(['AAPL.Open', 'AAPL.High', 'AAPL.Low', 'AAPL.Close'],['Open','High','Low','Close'])), inplace=True)

        # print("loading data")
        # print("df_ohlc", df_ohlc)

        graph_candlestick = go.Figure()

        candle = go.Candlestick(x     = df_ohlc['Date'],
                                open  = df_ohlc['Open'],
                                high  = df_ohlc['High'],
                                low   = df_ohlc['Low'],
                                close = df_ohlc['Close'],
                                name  = "Candlestick " + aSymbolName)

        graph_candlestick.add_trace(candle)
        graph_candlestick.update_xaxes(title="Date", rangeslider_visible=True)
        graph_candlestick.update_yaxes(title="Price", autorange=True)

        graph_candlestick.update_layout(
                title               = aSymbolName,
                height              = 600,
                width               = 900,
                showlegend          = True)

        graph_candlestick.update_layout(xaxis_rangebreaks = [ dict(bounds=["sat", "mon"]) ])

        app = dash.Dash()

        app.layout = html.Div(
            html.Div([
                dcc.Graph(id='graph_candlestick',figure=graph_candlestick)
            ])
        )

        #Server side implementation (slow)
        @app.callback(
        Output('graph_candlestick','figure'),
        [Input('graph_candlestick','relayoutData')],[State('graph_candlestick', 'figure')]
        )
        def update_result(relOut,Fig):

            if relOut == None:
                return Fig

            ## if you don't use the rangeslider to adjust the plot, then relOut.keys() won't include the key xaxis.range
            elif "xaxis.range" not in relOut.keys():
                newLayout = go.Layout(
                    title=aSymbolName,
                    height=600,
                    width=800,
                    showlegend=True,
                    yaxis=dict(autorange=True),
                    template="plotly"
                )

                Fig['layout']=newLayout
                return Fig

            else:
                ymin = df_ohlc.loc[df_ohlc['Date'].between(relOut['xaxis.range'][0], relOut['xaxis.range'][1]),'Low'].min()
                ymax = df_ohlc.loc[df_ohlc['Date'].between(relOut['xaxis.range'][0], relOut['xaxis.range'][1]),'High'].max()

                newLayout = go.Layout(
                    title=aSymbolName,
                    height=600,
                    width=800,
                    showlegend=True,
                    xaxis=dict(
                        rangeslider_visible=True,
                        range=relOut['xaxis.range']
                    ),
                    yaxis=dict(range=[ymin,ymax]),
                    template="plotly"
                )

                Fig['layout']=newLayout
                return Fig

        app.run_server(debug=True)

graphs:CGraphs = CGraphs()
graphs.makeCandlestick("MSFT")
"""
