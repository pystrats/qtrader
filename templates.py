from copy import deepcopy

STRATEGY_INFO = {
    'position': 0,
    'vwap': .0,
    'tpActive': False,
    'tpPrice': .0,
    'tpQty': 0,
    'slActive': False,
    'slPrice': .0,
    'slQty': 0,
    'slTrailing': False,
    'state': 'activated',
    'activeOrderId': -1,
    'orderInfo': '',
    'lastPrice': -1
}

STRATEGY_TEMPLATE = {
    'Long Breakout': deepcopy(STRATEGY_INFO),
    'Short Breakout': deepcopy(STRATEGY_INFO)
}

DEFAULT_PORTFOLIO_ENTRY = {
    'Long Breakout': False,
    'Long Breakout Price': .0,
    'Short Breakout': False,
    'Short Breakout Price': .0
}