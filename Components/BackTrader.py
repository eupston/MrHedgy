from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import datetime
import math
import multiprocessing
from functools import partial

import backtrader as bt
import json
import pandas as pd
from Components.IEX import IEX

# Create a Strategy
from Components.TDAmeritrade import TDAmeritrade
my_td_ameritrade = TDAmeritrade()

class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        time = self.datas[0].datetime.time()
        print('%s, %s %s' % (dt.isoformat(), time, txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma_s = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=3)

        self.sma_l = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=15)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])
        current_position_size = self.getposition(self.datas[0]).size

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        buy_stock_signal = self.sma_s[-1] < self.sma_l[-1] and self.sma_s[0] > self.sma_l[0]
        sell_stock_signal = self.sma_s[0] < self.sma_l[0]

        if not self.position:

            if buy_stock_signal:
                    # BUY, BUY, BUY!!! (with all possible default parameters)
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    stock_slippage_buffer_perc = 0.02
                    current_cash = self.broker.getcash()
                    current_stock_price = self.dataclose[0]
                    current_stock_price_buff = current_stock_price + (current_stock_price * stock_slippage_buffer_perc)
                    order_size = math.floor(current_cash / current_stock_price_buff) - 1
                    order_size_small = order_size / 4
                    self.order = self.buy(size=order_size)
        else:
            if sell_stock_signal:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order

                self.order = self.sell(size=current_position_size)

        i = list(range(0, len(self.datas)))
        for (d, j) in zip(self.datas, i):
            if len(d) == (d.buflen()-1):
                self.order = self.close(exectype=bt.Order.Market, size=current_position_size)

def main(symbol):
    CASH_AMOUNT = 1000.0
    try:
        # Create a cerebro entity
        cerebro = bt.Cerebro()

        # Add a strategy
        cerebro.addstrategy(TestStrategy)

        # Create a Data Feed
        previous_data = my_td_ameritrade.get_historical_data_DF(symbol, frequency=1, frequencyType="minute", period=10, periodType="day")
        my_idex = IEX()
        realtime_data = my_idex.get_historical_intraday(symbol)
        realtime_data = realtime_data.fillna(method='ffill')
        realtime_data["date"] = pd.to_datetime(realtime_data.date)

        data = merge_realtime_data_and_previous_data(realtime_data, previous_data)
        # data = data.resample('30Min').first()
        data.drop(['date'], axis=1)
        print(data)

        data = bt.feeds.PandasData(dataname=data)

        # Add the Data Feed to Cerebro
        cerebro.adddata(data)

        # Set our desired cash start
        cerebro.broker.setcash(CASH_AMOUNT)

        # Print out the starting conditions
        print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
        # Run over everything
        cerebro.run()

        # Print out the final result
        print('Final Portfolio Value: %.2f for %s' % (cerebro.broker.getvalue(), symbol))
        # if CASH_AMOUNT != cerebro.broker.getcash():
        #     # # Plot the result
        #     cerebro.plot()
        return [symbol, cerebro.broker.getvalue()]
    except IndexError as e:
        error = str(e)
        return [symbol, error]
    except KeyError as e:
        error = str(e)
        return [symbol, error]
    except Exception as e:
        error = str(e)
        return [symbol, error]

def threaded_main():
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = "YES"
    my_idex = IEX()
    # all_symbols = my_idex.supported_symbols
    all_symbols = ["AAPL"]
    strategy_results = {}
    with multiprocessing.Pool() as pool:
        results = pool.map(main, all_symbols)
    for result in results:
        strategy_results[result[0]] = result[1]
    strategy_results_sorted = {k: v for k, v in sorted(strategy_results.items(), key=lambda item: item[1] if type(item[1])!=str else 0, reverse=True)}
    print(json.dumps(strategy_results_sorted, indent=4))

def merge_realtime_data_and_previous_data(realtime_data, previous_data):
    """
    Merges Realtime Data from IEX and Previous days data from TD ameritrade
    :return: merged dataframe
    """
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', 10)

    previous_data = previous_data.rename(columns={'datetime': 'date'})
    previous_data.set_index("date", inplace=True, drop=True)

    merged_data = pd.concat([previous_data, realtime_data])
    return merged_data

if __name__ == '__main__':
    threaded_main()
