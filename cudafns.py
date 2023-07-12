SD_Periods = [101, 151, 301, 401, 501, 601, 701, 801, 901, 1001, 1401, 1501]
AVG_Periods = [18, 130, 625, 1181, 1181, 1181, 1181, 1181, 1181, 1181, 1181, 1181]
MIN_DATAPOINTS = SD_Periods[-1] + AVG_Periods[-1]

import sys, math, csv
import numpy as np

from numba import cuda
from time import time
from copy import deepcopy
from datetime import datetime


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
def compute_standard_deviations_realtime(returns, STDs, Periods, NThreads:int, NStocks:int):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= NThreads: return

    stockIX = ix % NStocks
    stdIX = ix // NStocks

    N = STDs.shape[2]
    period = Periods[stdIX]
    if N < period - 1: return

    STDs[stockIX][stdIX][-1] = STD(returns[stockIX], N-1, period, True)


@cuda.jit
def compute_averages_realtime(STDs, Averages, SD_Periods, AVG_Periods, NThreads:int, NStocks:int):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= NThreads: return

    stockIX = ix % NStocks
    avgIX = ix // NStocks

    period = AVG_Periods[avgIX]

    if STDs.shape[2] < period + SD_Periods[avgIX] - 1: return

    Averages[stockIX][avgIX][-1] = AVG(STDs[stockIX][avgIX], STDs.shape[2] - 1, period)


@cuda.jit
def compute_signals_realtime(Averages, Signals, InputMatrix, FIRST_VALID_INDEX: int, NThreads: int, NStocks:int):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= NThreads:
        return

    stockIX = ix % NStocks
    algoIX = ix // NStocks

    n = Signals.shape[2] - 1
    if n < FIRST_VALID_INDEX: return

    buy = Averages[stockIX][1][n] > InputMatrix[algoIX][0] and Averages[stockIX][1][n] < InputMatrix[algoIX][1] and \
            Averages[stockIX][2][n] > InputMatrix[algoIX][2] and Averages[stockIX][2][n] < InputMatrix[algoIX][3] and \
            Averages[stockIX][11][n] > InputMatrix[algoIX][4] and Averages[stockIX][11][n] < InputMatrix[algoIX][5] and \
            Averages[stockIX][12][n] > InputMatrix[algoIX][6] and Averages[stockIX][12][n] < InputMatrix[algoIX][7] and \
            Averages[stockIX][11][n] > Averages[stockIX][0][n] and \
            Averages[stockIX][11][n] > Averages[stockIX][1][n] and \
            Averages[stockIX][11][n] > Averages[stockIX][2][n]

    Signals[stockIX][algoIX][n] = 1 if buy else -1


@cuda.jit
def compute_standard_deviations_init(returns, STDs, Periods):

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
def compute_averages_init(STDs, Averages, SD_Periods, AVG_Periods):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= STDs.shape[0]:
        return

    for n in range(STDs.shape[2]):
        for k in range(len(AVG_Periods)):
            period = AVG_Periods[k]
            if n < period + SD_Periods[k] - 2: continue
            Averages[ix][k][n] = AVG(STDs[ix][k], n, period)


@cuda.jit
def compute_signals_init(Averages, Signals, InputMatrix, FIRST_VALID_INDEX: int, N_THREADS: int, N_STOCKS:int):

    ix = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
    if ix >= N_THREADS:
        return

    stockIX = ix % N_STOCKS
    algoIX = ix // N_STOCKS

    for n in range(Signals.shape[2]):
        if n < FIRST_VALID_INDEX: continue
        buy = Averages[stockIX][1][n] > InputMatrix[algoIX][0] and Averages[stockIX][1][n] < InputMatrix[algoIX][1] and \
                Averages[stockIX][2][n] > InputMatrix[algoIX][2] and Averages[stockIX][2][n] < InputMatrix[algoIX][3] and \
                Averages[stockIX][11][n] > InputMatrix[algoIX][4] and Averages[stockIX][11][n] < InputMatrix[algoIX][5] and \
                Averages[stockIX][12][n] > InputMatrix[algoIX][6] and Averages[stockIX][12][n] < InputMatrix[algoIX][7] and \
                Averages[stockIX][11][n] > Averages[stockIX][0][n] and \
                Averages[stockIX][11][n] > Averages[stockIX][1][n] and \
                Averages[stockIX][11][n] > Averages[stockIX][2][n]

        value = 1 if buy else -1
        Signals[stockIX][algoIX][n] = value
