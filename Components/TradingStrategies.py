import json
from Components.TDAmeritrade import TDAmeritrade
from Components.IEX import IEX
import time
from datetime import datetime, timedelta, date
import pandas as pd


class TradingStrategies:

    def __init__(self):
        self.my_tdameritrade = TDAmeritrade()
        self.my_iex = IEX()

    # TODO find better ways to fill NaN values such as query another api
    # TODO get previous days data to be able to trade right away
    def simple_moving_average_daily_strategy(self, symbol, short_interval=9, long_interval=20):
        """
        executes the simple moving average daily strategy based one minutes intervals
        :param symbol:
        :param short_interval:
        :param long_interval:
        :return:
        """
        cycle_count = 0
        while True:
            with open("transaction_data.json", 'r') as f:
                transaction_data = json.load(f)
            today = date.today()
            yesterday = today - timedelta(days=2)
            print(yesterday)
            # previous_day_minute_interval = self.my_iex.get_historical_intraday(symbol, date=yesterday)
            current_day_minute_interval = self.my_iex.get_historical_intraday(symbol)
            # current_day_minute_interval = pd.concat([previous_day_minute_interval, current_day_minute_interval])
            current_day_minute_interval = current_day_minute_interval.fillna(method='ffill')

            short_rolling = current_day_minute_interval.rolling(window=short_interval).mean()
            long_rolling = current_day_minute_interval.rolling(window=long_interval).mean()

            short_sma_previous = float(short_rolling.iloc[-2]['close'])
            long_sma_previous = float(long_rolling.iloc[-2]['close'])
            short_sma_current = float(short_rolling.iloc[-1]['close'])
            long_sma_current = float(long_rolling.iloc[-1]['close'])

            buy_stock_signal = short_sma_previous < long_sma_previous and short_sma_current > long_sma_current
            sell_stock_signal = short_sma_current < long_sma_current
            if buy_stock_signal:
                quote = self.my_tdameritrade.get_stock_quote(symbol)
                transaction_data[str(datetime.now)] = {
                    "bought": quote['askPrice']
                }
            if sell_stock_signal:
                quote = self.my_tdameritrade.get_stock_quote(symbol)
                transaction_data[str(datetime.now)] = {
                    "sold": quote['bidPrice']
                }
            print(f"Cycle Count: {cycle_count}")
            transaction_data['cycle_count'] = cycle_count
            with open("transaction_data.json", 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))
            cycle_count += 1

            # print(current_day_minute_interval)
            # import matplotlib.pyplot as plt
            # fig, ax = plt.subplots(figsize=(16, 9))
            # ax.plot(current_day_minute_interval.loc[:, :].index, current_day_minute_interval.loc[:, 'close'], label='Price')
            # ax.plot(short_rolling.loc[:, :].index, short_rolling.loc[:, 'close'], label='100-days SMA')
            # ax.plot(long_rolling.loc[:, :].index, long_rolling.loc[:, 'close'], label='100-days SMA')
            # plt.show()

            time.sleep(1)

if __name__ == '__main__':
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 150)

    my_trading_strategies = TradingStrategies()
    my_trading_strategies.simple_moving_average_daily_strategy("CCL")






