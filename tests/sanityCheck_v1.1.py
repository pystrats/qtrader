"""
This script generates synthetic price data, computes buy/sell signals and saves
data into CSV files. Import CSV files into Excel, replace price data and compare
CSV signals against signals computed natively by Excel.


CUDA Toolkit must be installed and GPU device enabled in order to run this script.
(https://developer.nvidia.com/cuda-toolkit)
"""

VERSION                 = '1.1'

# SETTINGS #####################################################################
NUMBER_OF_STOCKS        = 100
NUMBER_OF_DATAPOINTS    = 10000
API_KEY                 = '2DZUMLKMRJ5NCJP7'

# CUDA
CUDA_DEVICE_ID          = 0
THREADS_PER_BLOCK       = 128

# Standard Deviation Parameters
_input_2_min            = 0.0016
_input_2_max            = 1.
_input_3_min            = 0.
_input_3_max            = 1.
_input_12_min           = 0.
_input_12_max           = 1.
_input_avg_min          = 0.
_input_avg_max          = 1.

# Other Parameters
SD_Periods = [101, 151, 301, 401, 501, 601, 701, 801, 901, 1001, 1401, 1501]

AVG_Periods = [18, 130, 625, 1181, 1181, 1181, 1181, 1181, 1181, 1181, 1181, 1181]

################################################################################


import sys, math, csv
import numpy as np
import requests

from numba import cuda
from time import time
from copy import deepcopy
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")


@cuda.jit(device=True)
def STD(returns, n, period, sample=True):
    mean, sum_squared_deviations = .0, .0
    for i in range(period): mean += returns[n - i]
    mean /= period
    for i in range(period): sum_squared_deviations += (returns[n - i] - mean) ** 2
    divisor = period - 1 if sample else period
    return (sum_squared_deviations / divisor) ** .5


@cuda.jit(device=True)
def AVG(STDs_1D, n, period):
    avg = .0
    for i in range(period): avg += STDs_1D[n - i]
    return avg / period


@cuda.jit
def compute_standard_deviations(returns, STDs, Periods):

    # Thread Index
    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x

    # Kill if out of bounds
    if ix >= returns.shape[0]:
        return

    for n in range(returns.shape[1]):
        for k in range(len(Periods)):
            period = Periods[k]
            if n < period - 1: continue
            STDs[ix][k][n] = STD(returns[ix], n, period, True)


@cuda.jit
def compute_averages(STDs, Averages, SD_Periods, AVG_Periods):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= STDs.shape[0]:
        return

    for n in range(STDs.shape[2]):
        for k in range(len(AVG_Periods)):
            period = AVG_Periods[k]
            if n < period + SD_Periods[k] - 2: continue
            Averages[ix][k][n] = AVG(STDs[ix][k], n, period)


@cuda.jit
def compute_signals(Averages, Signals, InputVector, FIRST_VALID_INDEX: int):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= Averages.shape[0]:
        return

    for n in range(Signals.shape[1]):
        if n < FIRST_VALID_INDEX: continue
        buy = Averages[ix][1][n] > InputVector[0] and Averages[ix][1][n] < InputVector[1] and \
                Averages[ix][2][n] > InputVector[2] and Averages[ix][2][n] < InputVector[3] and \
                Averages[ix][11][n] > InputVector[4] and Averages[ix][11][n] < InputVector[5] and \
                Averages[ix][12][n] > InputVector[6] and Averages[ix][12][n] < InputVector[7] and \
                Averages[ix][11][n] > Averages[ix][0][n] and \
                Averages[ix][11][n] > Averages[ix][1][n] and \
                Averages[ix][11][n] > Averages[ix][2][n]

        if buy: Signals[ix][n] = True


def main(argv):

    NUMBER_OF_STOCKS = 1
    if len(argv) > 1:
        SYMBOL = argv[1]
    else:
        SYMBOL = ''
        print('Please specify symbol')
        sys.exit()

    print('{} Fetching {} price history...'.format(datetime.now(), SYMBOL), end=' ', flush=True)
    url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={}&interval=5min&datatype=json&outputsize=full&apikey=2DZUMLKMRJ5NCJP7'.format(SYMBOL)
    j = requests.get(url).json()
    print('done')
    key = 'Time Series (5min)'
    data, d = j[key], {}
    keys, values = [], []
    for key, value in data.items():
        v = value['4. close']
        d[key] = v
        keys.append(key)
        values.append(round(float(v), 2))
    NUMBER_OF_DATAPOINTS = len(keys)
    values.reverse()
    keys.reverse()

    """
    # Generate synthetic price data from normally distributed random variables
    rng = np.random.default_rng( int(time()//1) )  # Initialize random number generator

    # Generate returns
    returns = rng.normal(loc=0.0, scale=1.0, size=(NUMBER_OF_STOCKS, NUMBER_OF_DATAPOINTS))
    returns = np.cumsum(returns, axis=1)

    price_adjustments = [ min(returns[i]) * -1. + 1. if min(returns[i]) < .0 else 1. for i in range(NUMBER_OF_STOCKS) ]
    for n in range(NUMBER_OF_STOCKS): returns[n][:] += price_adjustments[n]
    prices = np.around(returns, decimals=2)
    """

    prices = np.array(values).reshape((1, len(values)))

    returns = np.zeros(shape=(NUMBER_OF_STOCKS, NUMBER_OF_DATAPOINTS), dtype='float64')
    for n in range(NUMBER_OF_STOCKS):
        for k in range(1, NUMBER_OF_DATAPOINTS): returns[n][k] = (prices[n][k] - prices[n][k-1]) / prices[n][k-1]

    # Compute Standard Deviations
    STDs = np.zeros(shape=(NUMBER_OF_STOCKS, len(SD_Periods), NUMBER_OF_DATAPOINTS), dtype='float64')

    BLOCKS_PER_GRID = math.floor(returns.shape[0] / THREADS_PER_BLOCK + 1)
    cuda.select_device(CUDA_DEVICE_ID)
    context = cuda.current_context(0)
    stream = cuda.stream()

    cuda_returns = cuda.to_device(returns, stream=stream)
    cuda_STDs = cuda.to_device(STDs, stream=stream)
    cuda_Periods = cuda.to_device(np.array(SD_Periods, dtype='int'), stream=stream)

    print('{} Computing standard deviations...'.format(datetime.now()), end = ' ', flush = True)
    compute_standard_deviations[BLOCKS_PER_GRID, THREADS_PER_BLOCK, stream](cuda_returns, cuda_STDs, cuda_Periods)
    print('done')

    cuda_STDs.copy_to_host(STDs, stream=stream)
    stream.synchronize()

    # Compute Average Standard Deviations
    Averages = np.zeros(shape=(NUMBER_OF_STOCKS, len(AVG_Periods) + 1, NUMBER_OF_DATAPOINTS), dtype='float64')

    stream = cuda.stream()
    cuda_STDs = cuda.to_device(STDs, stream=stream)
    cuda_Averages = cuda.to_device(Averages, stream=stream)
    cuda_SD_Periods = cuda.to_device(np.array(SD_Periods, dtype='int'), stream=stream)
    cuda_AVG_Periods = cuda.to_device(np.array(AVG_Periods, dtype='int'), stream=stream)

    print('{} Computing averages...'.format(datetime.now()), end = ' ', flush = True)
    compute_averages[BLOCKS_PER_GRID, THREADS_PER_BLOCK, stream](cuda_STDs, cuda_Averages, cuda_SD_Periods, cuda_AVG_Periods)
    print('done')

    cuda_Averages.copy_to_host(Averages, stream=stream)
    stream.synchronize()

    # Average of averages
    MIN_DATAPOINTS = SD_Periods[-1] + AVG_Periods[-1] - 1
    FIRST_VALID_INDEX = MIN_DATAPOINTS - 1
    for n in range(NUMBER_OF_DATAPOINTS):
        if n < FIRST_VALID_INDEX: continue
        for k in range(NUMBER_OF_STOCKS):
            avg = .0
            for i in range(len(AVG_Periods)): avg += Averages[k][i][n]
            avg /= len(AVG_Periods)
            Averages[k][len(AVG_Periods)][n] = avg

    # Compute Signals
    InputVector = [_input_2_min, _input_2_max, _input_3_min,  _input_3_max, _input_12_min,  _input_12_max,  _input_avg_min, _input_avg_max]
    Signals = np.zeros(shape=(NUMBER_OF_STOCKS, NUMBER_OF_DATAPOINTS), dtype='bool')

    stream = cuda.stream()
    cuda_Averages = cuda.to_device(Averages, stream=stream)
    cuda_Signals = cuda.to_device(Signals, stream=stream)
    cuda_InputVector = cuda.to_device(np.array(InputVector, dtype='float64'), stream=stream)

    print('{} Computing signals...'.format(datetime.now()), end = ' ', flush = True)
    compute_signals[BLOCKS_PER_GRID, THREADS_PER_BLOCK, stream](cuda_Averages, cuda_Signals, cuda_InputVector, FIRST_VALID_INDEX)
    print('done')

    cuda_Signals.copy_to_host(Signals, stream=stream)
    stream.synchronize()

    # Save Data
    print('{} Saving data file...'.format(datetime.now()), end = ' ', flush = True)
    header = ['datetime', 'price', 'signal']
    for stockNumber in range(NUMBER_OF_STOCKS):
        stockSignal = []
        for n in range(NUMBER_OF_DATAPOINTS):
            if n < FIRST_VALID_INDEX:
                stockSignal.append('')
            else:
                stockSignal.append('buy' if Signals[stockNumber][n] else 'sell')

        stockPrice = list(deepcopy(prices[stockNumber]))
        stockDatetime = list(deepcopy(np.array(keys)))

        stockSignal.reverse()
        stockPrice.reverse()
        stockDatetime.reverse()

        data = []
        for n in range(NUMBER_OF_DATAPOINTS): data.append([stockDatetime[n], stockPrice[n], stockSignal[n]])

        prefix = '00' if stockNumber < 10 else '0'
        if stockNumber >= 100: prefix = ''

        fileName = '{} {}.csv'.format(SYMBOL.upper(), str(datetime.now()).replace(':', '.'))
        with open(fileName, 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        print("saved as {}".format(fileName))


if __name__ == '__main__':
    main(sys.argv)
