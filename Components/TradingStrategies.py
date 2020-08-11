import json
from Components.APIs.TDAmeritrade import TDAmeritrade
from Components.APIs.IEX import IEX
import time
from datetime import datetime, timedelta, date
import pandas as pd
import backtrader as bt
import math
from pytz import timezone

class TradingStrategies:

    def __init__(self):
        self.my_tdameritrade = TDAmeritrade()
        self.my_iex = IEX()

    # TODO find better ways to fill NaN values such as query another api
    # TODO get previous days data to be able to trade right away
    def simple_moving_average_daily_strategy(self, symbol, short_interval=3, long_interval=15):
        """
        executes the simple moving average daily strategy based one minutes intervals
        :param symbol:
        :param short_interval:
        :param long_interval:
        :return:
        """
        transaction_data = {}
        tz = timezone('EST')
        print(f"runnning simple_moving_average_daily_strategy on {symbol} at {datetime.now(tz)} ")
        try:
            current_day_minute_interval = self.my_iex.get_historical_intraday(symbol)
            # current_day_minute_interval = pd.concat([previous_day_minute_interval, current_day_minute_interval])
            current_day_minute_interval = current_day_minute_interval.fillna(method='ffill')
            print(current_day_minute_interval)
            short_rolling = current_day_minute_interval.rolling(window=short_interval).mean()
            long_rolling = current_day_minute_interval.rolling(window=long_interval).mean()

            short_sma_previous = float(short_rolling.iloc[-2]['close'])
            long_sma_previous = float(long_rolling.iloc[-2]['close'])
            short_sma_current = float(short_rolling.iloc[-1]['close'])
            long_sma_current = float(long_rolling.iloc[-1]['close'])
            print("short_sma_previous ", short_sma_previous)
            print("long_sma_previous ", long_sma_previous)
            print("short_sma_current ", short_sma_current)
            print("long_sma_current ", long_sma_current)
            buy_stock_signal = short_sma_previous < long_sma_previous and short_sma_current > long_sma_current
            sell_stock_signal = short_sma_current < long_sma_current
            # buy_stock_signal = True
            # sell_stock_signal = True
            if buy_stock_signal:
                quote = self.my_tdameritrade.get_stock_quote(symbol)
                transaction_data[str(datetime.now(tz))] = {
                    "bought": quote['askPrice']
                }
                print(f"BOUGHT {symbol} at {quote['askPrice']}")
            if sell_stock_signal:
                quote = self.my_tdameritrade.get_stock_quote(symbol)
                transaction_data[str(datetime.now(tz))] = {
                    "sold": quote['bidPrice']
                }
                print(f"SOLD {symbol} at {quote['bidPrice']}")
            return {"symbol": symbol, "transaction_data":transaction_data }
        except Exception as e:
            return {"symbol": symbol, "transaction_data": {str(datetime.now(tz)): str(e)} }


class SMAStrategy(bt.Strategy):
    params = (
        ('symbol', None ),
        ('buy_callback', None),
        ('sell_callback', None),
        ('live_trading', False),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        time = self.datas[0].datetime.time()
        print('%s, %s %s' % (dt.isoformat(), time, txt))

    def __init__(self):
        """
        executes the simple moving average daily strategy
        """
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma_s = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=5)

        self.sma_l = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=21)

        self.symbol = self.params.symbol
        self.buy_callback = self.params.buy_callback
        self.sell_callback = self.params.sell_callback
        self.live_trading = self.params.live_trading

        self.current_percent_increase = None
        self.bought_stock_price = None
        self.momentum_loss_threshold_percent = 0.02
        self.momentum_percentage_peak = 0

    def notify_order(self, order):
        dt = self.datas[0].datetime.date(0)
        time = self.datas[0].datetime.time()
        date_time = str(dt) + " " + str(time)

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
                if self.buy_callback:
                    self.buy_callback(self.symbol, date_time)
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                if self.sell_callback:
                    self.sell_callback(self.symbol, date_time)

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
        sell_stock_signal = False
        sell_stock_signal_two = False
        if self.bought_stock_price:
            # calculate percentage increase
            new_stock_price = self.dataclose[0]
            self.current_percent_increase = ((new_stock_price - self.bought_stock_price) / self.bought_stock_price) * 100
            if self.current_percent_increase > self.momentum_percentage_peak:
                self.momentum_percentage_peak = self.current_percent_increase
            # calculate Momentum loss if any
            current_momentum_loss_threshold = self.momentum_percentage_peak * self.momentum_loss_threshold_percent
            if self.momentum_percentage_peak - current_momentum_loss_threshold < self.current_percent_increase:
                sell_stock_signal_two = True

        if not self.position:
            if buy_stock_signal:
                    # BUY, BUY, BUY!!! (with all possible default parameters)
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    stock_slippage_buffer_perc = 0.02
                    current_cash = self.broker.getvalue()
                    current_stock_price = self.dataclose[0]
                    current_stock_price_buff = current_stock_price + (current_stock_price * stock_slippage_buffer_perc)
                    order_size = math.floor(current_cash / current_stock_price_buff) - 1
                    self.order = self.buy(size=order_size)
                    self.bought_stock_price = self.dataclose[0]
        else:
            if sell_stock_signal_two:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=current_position_size)
            elif sell_stock_signal:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=current_position_size)

        i = list(range(0, len(self.datas)))
        for (d, j) in zip(self.datas, i):
            if len(d) == (d.buflen()-1):
                self.order = self.close(exectype=bt.Order.Market, size=current_position_size)

if __name__ == '__main__':
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 150)
    my_trading_strategies = TradingStrategies()
    results = my_trading_strategies.simple_moving_average_daily_strategy("CCL")
    print(results)






