import os
from datetime import datetime, timedelta
from time import time, sleep
import dateutil.parser as parser

import pandas as pd

import dash
from dash import Output, Input, State, ClientsideFunction, dcc, html

import plotly.graph_objs as go

from PyQt5.QtCore import pyqtSlot, QObject, QThread, pyqtSignal


class DashWorker(QObject):

    finished = pyqtSignal()
    requestWindowSize = pyqtSignal()
    ready = pyqtSignal()
    initiated = False
    windowWidth = 600
    windowHeight = 600
    mysteriousWidthConstant = 0
    mysteriousHeightConstant = 41
    browserResized = False
    state = {}
    period = 'daily'

    wd = os.path.dirname(os.path.abspath(__file__))
    data = pd.read_csv(wd+'/finance-charts-apple.csv')
    data.rename(columns=dict(zip(['AAPL.Open', 'AAPL.High', 'AAPL.Low', 'AAPL.Close'],['Open','High','Low','Close'])), inplace=True)

    graph_candlestick = go.Figure()

    app = dash.Dash()


    def missingDates(self, dates, datetimeFormat='%Y-%m-%d'):
        """
        dates       dtype:list
        datetime format codes:
        https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
        """
        startingDate, endingDate = datetime.strptime(dates[0], datetimeFormat), datetime.strptime(dates[-1], datetimeFormat)
        datetimes = [datetime.strptime(date, datetimeFormat) for date in dates]
        nDays = (endingDate-startingDate).days + 1
        continuousDates = [startingDate + timedelta(days=x) for x in range(nDays)]
        missingDates = []
        for date in continuousDates:
            if date not in datetimes: missingDates.append(date.strftime(datetimeFormat))
        return missingDates

    def missingDatesRaw(self, dates):
        startingDate, endingDate = dates[0], dates[-1]
        datetimes = dates
        nDays = (endingDate-startingDate).days + 1
        continuousDates = [startingDate + timedelta(days=x) for x in range(nDays)]
        missingDates = []
        for date in continuousDates:
            if date not in datetimes: missingDates.append(date)
        return missingDates


    def update_window_size(self, width, height):
        self.windowWidth = width + self.mysteriousWidthConstant
        self.windowHeight = height - self.mysteriousHeightConstant

    def resized(self):
        self.browserResized = True

    def stateChange(self, state):
        self.state['status'] = state

    def newDataReceived(self, data, period):
        self.period = period
        self.data = pd.DataFrame(list(zip(
            data['Date'],
            data['Open'],
            data['High'],
            data['Low'],
            data['Close'],
            data['Volume'])),
            columns =['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.state['status'] = 'data_ready'

    def run(self):
        if not self.initiated:

            self.margin = dict(l=0, r=0, t=0, b=0)
            self.gridcolor = '#596666'
            self.griddash = 'dot'
            self.gridwidth = 1
            self.rangeSliderThickness = 5/100.
            self.barsInDefaultView = 150
            self.rightOffsetBars = 15
            self.datetimeFormat = '%Y-%m-%d'
            self.state = {
                    'n' : 0,
                    'rangeStart' : '',
                    'rangeEnd' : '',
                    'ymin' : None,
                    'ymax' : None,
                    'status': ''
                }

            self.increasingColor = '#00E676'
            self.decreasingColor = '#ff5252'

            self.xaxisFirstBarDate = ''
            self.xaxisLastBarDate = ''

            self.firstDate = ''
            self.lastDate = ''


            dates = self.data['Date'].tolist()
            self.missing_dates = self.missingDates(dates,
                    datetimeFormat='%Y-%m-%d') if self.period == 'daily' else []

            self.graph_candlestick = go.Figure()

            candle = go.Candlestick(x     = self.data['Date'],
                                    open  = self.data['Open'],
                                    high  = self.data['High'],
                                    low   = self.data['Low'],
                                    close = self.data['Close'],
                                    name  = "Candlestick Chart",
                                    increasing=dict(fillcolor=self.increasingColor,
                                                    line_color = self.increasingColor,
                                                    line_width=1
                                                    ),
                                    decreasing=dict(fillcolor=self.decreasingColor,
                                                    line_color = self.decreasingColor,
                                                    line_width=1
                                                    ),
                                    showlegend = False,
                                    )

            # self.graph_candlestick.update_traces(mode="lines+markers+text")
            self.graph_candlestick.add_trace(candle)


            self.xaxisFirstBarDate = dates[-1*self.barsInDefaultView] if len(dates) >= self.barsInDefaultView else dates[0]
            self.xaxisLastBarDate = (datetime.strptime(dates[-1], self.datetimeFormat) + timedelta(days=self.rightOffsetBars)).strftime(self.datetimeFormat)
            self.firstDate, self.lastDate = dates[0], dates[-1]
            self.requestWindowSize.emit()

            ymin = self.data.loc[self.data['Date'].between(self.xaxisFirstBarDate, dates[-1] ),'Low'].min()
            ymax = self.data.loc[self.data['Date'].between(self.xaxisFirstBarDate, dates[-1] ),'High'].max()

            self.graph_candlestick.update_layout(
                    title               = "MSFT",
                    autosize            = True,
                    height              = self.windowHeight,
                    width               = self.windowWidth,
                    showlegend          = False,
                    xaxis=dict(
                        rangeslider_visible=True,
                        rangeslider_thickness=self.rangeSliderThickness,
                        range=[self.xaxisFirstBarDate, self.xaxisLastBarDate],
                        ),
                    # yaxis=dict(autorange=True),
                    yaxis=dict(range=[ymin,ymax]
                                ),
                    plot_bgcolor='#2c3e50',
                    paper_bgcolor='#2c3e50',
                    font_color='#aaaaaa',
                    xaxis_tickfont_size=13,
                    yaxis_tickfont_size=13,
                    margin=self.margin,
                    dragmode='pan',
                    template="plotly",
                    xaxis_gridcolor=self.gridcolor,
                    xaxis_griddash=self.griddash,
                    xaxis_gridwidth=self.gridwidth,
                    yaxis_gridcolor=self.gridcolor,
                    yaxis_griddash=self.griddash,
                    yaxis_gridwidth=self.gridwidth,
                    yaxis_side='right',
                    xaxis_rangeslider_thickness=self.rangeSliderThickness,
                    xaxis_rangebreaks = [dict(values=self.missing_dates)]
                    )


            self.app.layout = html.Div([
                html.Div([ html.Div(id = 'bgContainer', children = [ html.Div(id = 'bg', style={
                    'background-color' : '#2c3e50',
                    'margin-left':'-1000px',
                    'margin-top':'-1000px',
                    'margin-right':'-1000px',
                    'margin-bottom':'-1000px',
                    'width' : '10000px',
                    'height' : '10000px',
                    'position' : 'absolute',
                    'overflow' : 'hidden',
                    'overflow-x':'hidden',
                    'overflow-y':'hidden'
                } ) ]),
                ],style={
                        'position':'absolute',

                        }),
                html.Div([
                    dcc.Graph(id='graph_candlestick',figure=self.graph_candlestick,config={'displayModeBar': False, 'scrollZoom': True})
                ],style={'background-color': '#2c3e50',
                        'margin-left':'-29px',
                        'margin-top':'-10px',
                        'margin-right':'0px',
                        'margin-bottom':'-8px',
                        'overflow': 'hidden',
                        'overflow-x':'hidden',
                        'overflow-y':'hidden',
                        'position':'absolute'
                        }),
                dcc.Interval(
                    id='interval_component',
                    interval=1000,
                    n_intervals=0
                    )

            ])

            self.ready.emit()

            # @app.callback(
            # Output('graph_candlestick','figure'),
            # Input('interval_component','n_intervals')
            # )
            # def update_data(n):
            #     print('updating')
            #     return go.Figure()


            @self.app.callback(
            Output('graph_candlestick','figure'),
            Output('graph_candlestick','relayoutData'),
            Input('graph_candlestick','relayoutData'),
            Input('interval_component','n_intervals'),
            State('graph_candlestick', 'figure')
            )
            def update_result(relOut,n,Fig):

                if self.state['status'] == 'loading_data':
                    first_date = parser.parse(Fig['layout']['xaxis']['range'][0])
                    second_date = parser.parse(Fig['layout']['xaxis']['range'][1])
                    """
                    try:
                        first_date = datetime.strptime(Fig['layout']['xaxis']['range'][0], '%Y-%m-%d')
                        second_date = datetime.strptime(Fig['layout']['xaxis']['range'][1], '%Y-%m-%d')
                    except:
                        try:
                            first_date = datetime.strptime(Fig['layout']['xaxis']['range'][0], '%Y-%m-%dT%H:%M:%S')
                            second_date = datetime.strptime(Fig['layout']['xaxis']['range'][1], '%Y-%m-%dT%H:%M:%S')
                        except:
                            first_date = datetime.strptime(Fig['layout']['xaxis']['range'][0], '%Y-%m-%d %H:%M:%S.%f')
                            second_date = datetime.strptime(Fig['layout']['xaxis']['range'][1], '%Y-%m-%d %H:%M:%S.%f')
                    """

                    xaxis_midpoint = ( first_date + (second_date - first_date) / 2 ).strftime('%Y-%m-%dT%H:%M:%S')

                    [rangeStart, rangeEnd] = Fig['layout']['xaxis']['range'] if relOut == None or "xaxis.range" not in relOut.keys() else [relOut['xaxis.range'][0], relOut['xaxis.range'][1]]
                    ymin = self.data.loc[self.data['Date'].between(rangeStart, rangeEnd),'Low'].min()
                    ymax = self.data.loc[self.data['Date'].between(rangeStart, rangeEnd),'High'].max()

                    yaxis_midpoint = (ymin+ymax) / 2

                    annotation = {
                        'x': xaxis_midpoint,
                        'y': str(yaxis_midpoint),
                        'xref': 'x',
                        'yref': 'y',
                        'text': 'Loading...',
                        'align': 'center',
                        # 'ay': 0,
                        'opacity': 1,
                        'bgcolor': '#2c3e50',
                        'font_color' : '#f39c12',
                        'font_size' : 18,
                        'bordercolor' : '#8a8a8a',
                        'borderpad' : 12
                    }

                    newLayout = go.Layout(
                        title="",
                        autosize            = True,
                        height              = self.windowHeight,
                        width               = self.windowWidth,
                        showlegend          = False,
                        xaxis=dict(
                            rangeslider_visible=True,
                            range=[rangeStart, rangeEnd]
                        ),
                        yaxis=dict(
                            range=[ymin,ymax],
                            # showticklabels = True,
                            # visible = True,
                            # ticks = 'inside',
                            # tickcolor = '#ffffff',
                            # ticklabelposition = 'inside right',
                            # side = 'left'
                        ),
                        template="plotly",
                        plot_bgcolor='#2c3e50',
                        paper_bgcolor='#2c3e50',
                        font_color='#aaaaaa',
                        xaxis_tickfont_size=13,
                        yaxis_tickfont_size=13,
                        margin=self.margin,
                        xaxis_rangebreaks = [dict(values=self.missing_dates)],
                        dragmode='pan',
                        xaxis_gridcolor=self.gridcolor,
                        xaxis_griddash=self.griddash,
                        xaxis_gridwidth=self.gridwidth,
                        yaxis_gridcolor=self.gridcolor,
                        yaxis_griddash=self.griddash,
                        yaxis_gridwidth=self.gridwidth,
                        yaxis_side='right',
                        xaxis_rangeslider_thickness=self.rangeSliderThickness,
                        annotations=(annotation,)
                    )

                    Fig['layout']=newLayout
                    return [Fig, relOut]
                elif self.state['status'] == 'data_ready':
                    self.graph_candlestick = go.Figure()

                    candle = go.Candlestick(x     = self.data['Date'],
                                            open  = self.data['Open'],
                                            high  = self.data['High'],
                                            low   = self.data['Low'],
                                            close = self.data['Close'],
                                            name  = "Candlestick Chart",
                                            increasing=dict(fillcolor=self.increasingColor,
                                                            line_color = self.increasingColor,
                                                            line_width=1
                                                            ),
                                            decreasing=dict(fillcolor=self.decreasingColor,
                                                            line_color = self.decreasingColor,
                                                            line_width=1
                                                            ),
                                            showlegend = False,
                                            )

                    self.graph_candlestick.add_trace(candle)

                    dates = self.data['Date'].tolist()

                    self.xaxisFirstBarDate = dates[-1*self.barsInDefaultView] if len(dates) >= self.barsInDefaultView else dates[0]
                    td = timedelta(days=self.rightOffsetBars)
                    if self.period == 'weekly':
                        td = timedelta(weeks=self.rightOffsetBars)
                    if self.period == '1H':
                        td = timedelta(hours=self.rightOffsetBars)
                    if self.period == '30min':
                        td = timedelta(hours=0.5*self.rightOffsetBars)
                    if self.period == '5min':
                        td = timedelta(minutes=5*self.rightOffsetBars)

                    self.xaxisLastBarDate = dates[-1] + td
                    self.firstDate, self.lastDate = dates[0], dates[-1]
                    self.requestWindowSize.emit()

                    ymin = self.data.loc[self.data['Date'].between(self.xaxisFirstBarDate, dates[-1] ),'Low'].min()
                    ymax = self.data.loc[self.data['Date'].between(self.xaxisFirstBarDate, dates[-1] ),'High'].max()

                    self.missing_dates = self.missingDatesRaw(dates) if self.period == 'daily' else []
                    self.missing_dates = [date.strftime('%Y-%m-%d') for date in self.missing_dates]

                    self.graph_candlestick.update_layout(
                            title               = "",
                            autosize            = True,
                            height              = self.windowHeight,
                            width               = self.windowWidth,
                            showlegend          = False,
                            xaxis=dict(
                                rangeslider_visible=True,
                                rangeslider_thickness=self.rangeSliderThickness,
                                range=[self.xaxisFirstBarDate, self.xaxisLastBarDate],
                                ),
                            # yaxis=dict(autorange=True),
                            yaxis=dict(range=[ymin,ymax]
                                        ),
                            plot_bgcolor='#2c3e50',
                            paper_bgcolor='#2c3e50',
                            font_color='#aaaaaa',
                            xaxis_tickfont_size=13,
                            yaxis_tickfont_size=13,
                            margin=self.margin,
                            dragmode='pan',
                            template="plotly",
                            xaxis_gridcolor=self.gridcolor,
                            xaxis_griddash=self.griddash,
                            xaxis_gridwidth=self.gridwidth,
                            yaxis_gridcolor=self.gridcolor,
                            yaxis_griddash=self.griddash,
                            yaxis_gridwidth=self.gridwidth,
                            yaxis_side='right',
                            xaxis_rangeslider_thickness=self.rangeSliderThickness,
                            xaxis_rangebreaks = [dict(values=self.missing_dates)]
                            )

                    self.state['status'] = ''
                    self.state['ymin'] = ymin
                    self.state['ymax'] = ymax
                    newRelOut = {
                        'xaxis.range[0]':  self.xaxisFirstBarDate.strftime('%Y-%m-%d %H:%M:%S.%f'),
                        'xaxis.range[1]': self.xaxisLastBarDate.strftime('%Y-%m-%d %H:%M:%S.%f')
                        }
                    [ self.state['rangeStart'], self.state['rangeEnd'] ] = [ self.xaxisFirstBarDate,
                            self.xaxisLastBarDate ] if relOut == None or "xaxis.range" not in relOut.keys() else [ newRelOut['xaxis.range[0]'], newRelOut['xaxis.range[1]'] ]
                    return [self.graph_candlestick, newRelOut]

                rangeStart, rangeEnd = '', ''

                if relOut == None:
                    userTriggeredEvent = False
                else:
                    [rangeStart, rangeEnd] = Fig['layout']['xaxis']['range'] if "xaxis.range" not in relOut.keys() else [relOut['xaxis.range'][0], relOut['xaxis.range'][1]]
                    userTriggeredEvent = rangeStart != self.state['rangeStart'] or rangeEnd != self.state['rangeEnd']

                if not userTriggeredEvent:
                    yRangeAdjustmentRequired = False
                    if relOut != None:
                        ymin = self.data.loc[self.data['Date'].between(rangeStart, rangeEnd),'Low'].min()
                        ymax = self.data.loc[self.data['Date'].between(rangeStart, rangeEnd),'High'].max()
                        if ymin != self.state['ymin'] or ymax != self.state['ymax']:
                            yRangeAdjustmentRequired = True
                            self.state['ymin'] = ymin
                            self.state['ymax'] = ymax

                    if self.browserResized or yRangeAdjustmentRequired:
                        self.requestWindowSize.emit()
                        if relOut == None or "xaxis.range" not in relOut.keys():
                            rangeReference = Fig['layout']['xaxis']['range']
                            newRangeStart = rangeReference[0]
                            newRangeEnd = rangeReference[1]
                        else:
                            newRangeStart = relOut['xaxis.range'][0]
                            newRangeEnd = relOut['xaxis.range'][1]

                        self.state['rangeStart'] = newRangeStart
                        self.state['rangeEnd'] = newRangeEnd
                        ymin = self.data.loc[self.data['Date'].between(newRangeStart, newRangeEnd),'Low'].min()
                        ymax = self.data.loc[self.data['Date'].between(newRangeStart, newRangeEnd),'High'].max()
                        newLayout = go.Layout(
                            title="MSFT",
                            autosize            = True,
                            height              = self.windowHeight,
                            width               = self.windowWidth,
                            showlegend          = False,
                            xaxis=dict(
                                rangeslider_visible=True,
                                range=[newRangeStart, newRangeEnd]
                            ),
                            yaxis=dict(
                                range=[ymin,ymax],
                                # showticklabels = True,
                                # visible = True,
                                # ticks = 'inside',
                                # tickcolor = '#ffffff',
                                # ticklabelposition = 'inside right',
                                # side = 'left'
                            ),
                            template="plotly",
                            plot_bgcolor='#2c3e50',
                            paper_bgcolor='#2c3e50',
                            font_color='#aaaaaa',
                            xaxis_tickfont_size=13,
                            yaxis_tickfont_size=13,
                            margin=self.margin,
                            xaxis_rangebreaks = [dict(values=self.missing_dates)],
                            dragmode='pan',
                            xaxis_gridcolor=self.gridcolor,
                            xaxis_griddash=self.griddash,
                            xaxis_gridwidth=self.gridwidth,
                            yaxis_gridcolor=self.gridcolor,
                            yaxis_griddash=self.griddash,
                            yaxis_gridwidth=self.gridwidth,
                            yaxis_side='right',
                            xaxis_rangeslider_thickness=self.rangeSliderThickness
                        )

                        self.browserResized = False
                        Fig['layout']=newLayout
                        return [Fig, relOut]

                    else: return [Fig, relOut]

                else:
                    # User interaction
                    if relOut == None:
                        return [Fig, relOut]

                    elif "xaxis.range" not in relOut.keys():
                        rangeReference = Fig['layout']['xaxis']['range']
                        firstDate = rangeReference[0]
                        lastDate = rangeReference[1]
                        # defaultDtFormat = '%Y-%m-%d %H:%M:%S.%f'
                        self.state['rangeStart'] = firstDate
                        self.state['rangeEnd'] = lastDate
                        ymin = self.data.loc[self.data['Date'].between(firstDate, lastDate),'Low'].min()
                        ymax = self.data.loc[self.data['Date'].between(firstDate, lastDate),'High'].max()
                        newLayout = go.Layout(
                            title="MSFT",
                            autosize            = True,
                            height              = self.windowHeight,
                            width               = self.windowWidth,
                            showlegend          = False,
                            xaxis=dict(
                                rangeslider_visible=True,
                                range=[firstDate, lastDate]
                            ),
                            yaxis=dict(range=[ymin,ymax]),
                            template="plotly",
                            plot_bgcolor='#2c3e50',
                            paper_bgcolor='#2c3e50',
                            font_color='#aaaaaa',
                            xaxis_tickfont_size=13,
                            yaxis_tickfont_size=13,
                            margin=self.margin,
                            xaxis_rangebreaks = [dict(values=self.missing_dates)],
                            dragmode='pan',
                            xaxis_gridcolor=self.gridcolor,
                            xaxis_griddash=self.griddash,
                            xaxis_gridwidth=self.gridwidth,
                            yaxis_gridcolor=self.gridcolor,
                            yaxis_griddash=self.griddash,
                            yaxis_gridwidth=self.gridwidth,
                            yaxis_side='right',
                            xaxis_rangeslider_thickness=self.rangeSliderThickness
                        )

                        Fig['layout']=newLayout
                        return [Fig, relOut]

                    else:
                        newRangeStart = relOut['xaxis.range'][0]
                        newRangeEnd = relOut['xaxis.range'][1]
                        ymin = self.data.loc[self.data['Date'].between(newRangeStart, newRangeEnd),'Low'].min()
                        ymax = self.data.loc[self.data['Date'].between(newRangeStart, newRangeEnd),'High'].max()
                        self.state['rangeStart'] = newRangeStart
                        self.state['rangeEnd'] = newRangeEnd

                        newLayout = go.Layout(
                            title="MSFT",
                            height=self.windowHeight,
                            width=self.windowWidth,
                            autosize=True,
                            showlegend=False,
                            xaxis=dict(
                                rangeslider_visible=True,
                                range=relOut['xaxis.range']
                            ),
                            yaxis=dict(range=[ymin,ymax]),
                            template="plotly",
                            plot_bgcolor='#2c3e50',
                            paper_bgcolor='#2c3e50',
                            font_color='#aaaaaa',
                            xaxis_tickfont_size=13,
                            yaxis_tickfont_size=13,
                            margin=self.margin,
                            xaxis_rangebreaks = [dict(values=self.missing_dates)],
                            dragmode='pan',
                            xaxis_gridcolor=self.gridcolor,
                            xaxis_griddash=self.griddash,
                            xaxis_gridwidth=self.gridwidth,
                            yaxis_gridcolor=self.gridcolor,
                            yaxis_griddash=self.griddash,
                            yaxis_gridwidth=self.gridwidth,
                            yaxis_side='right',
                            xaxis_rangeslider_thickness=self.rangeSliderThickness
                        )

                        # yaxis = {
                        #   'autorange': True, 'color': '#4a4a4a', 'gridcolor': 'red', 'griddash': 'dash', 'gridwidth': 1, 'range': [ymin,ymax]
                        # }

                        Fig['layout']=newLayout
                        # Fig['layout']['yaxis'] =yaxis
                        return [Fig, relOut]

            self.initiated = True
            self.app.run_server(debug=False)
