from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import multiprocessing
import backtrader as bt
import json
import pandas as pd
from Components.APIs.IEX import IEX

from Components.APIs.TDAmeritrade import TDAmeritrade
from Components.TradingStrategies import SMAStrategy

class BackTrader:
    """Class for Back testing Strategies"""
    def __init__(self, strategy, buy_callback=None, sell_callback=None):
        self.my_td_ameritrade = TDAmeritrade()
        self.my_idex = IEX()
        self.all_symbols = self.my_idex.supported_symbols
        self.strategy = strategy
        self.cash_amount = 1000.0
        self.strategy_result = strategy
        self.buy_callback = buy_callback
        self.sell_callback = sell_callback

    def run_strategy(self, symbol):
        """
        Run the strategy on the given stock symbol
        :param symbol:
        :return:
        """
        try:
            # Create a cerebro entity
            cerebro = bt.Cerebro()
            # Add a strategy
            cerebro.addstrategy(self.strategy, symbol, buy_callback=self.buy_callback, sell_callback=self.sell_callback)

            # Create a Data Feed
            market_data = self.create_data_feed(symbol)
            data = bt.feeds.PandasData(dataname=market_data)

            # Add the Data Feed to Cerebro
            cerebro.adddata(data)

            # Set our desired cash start
            cerebro.broker.setcash(self.cash_amount)

            # Print out the starting conditions
            print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
            # Run over everything
            cerebro.run()

            # Print out the final result
            print('Final Portfolio Value: %.2f for %s' % (cerebro.broker.getvalue(), symbol))
            # if CASH_AMOUNT != cerebro.broker.getcash():
            #     # # Plot the result
            #     cerebro.plot()
            return {"symbol": symbol, "result": cerebro.broker.getvalue()}
        except IndexError as e:
            error = str(e)
            return {"symbol": symbol, "result": error}
        except KeyError as e:
            error = str(e)
            return {"symbol": symbol, "result": error}
        except Exception as e:
            error = str(e)
            return {"symbol": symbol, "result": error}

    def run_strategy_multiple_symbols(self, symbol_list=None, run_all_symbols=False):
        """
        Run the strategy with the given symbol list
        :param symbol_list:
        :param run_all_symbols:
        :return:
        """
        if symbol_list:
            symbols_to_run = symbol_list
        elif run_all_symbols:
            symbols_to_run = self.all_symbols
        else:
            raise Exception("No Symbols provided to run strategy")
        strategy_results = {}
        with multiprocessing.Pool(processes=5) as pool:
            results = pool.map(self.run_strategy, symbols_to_run)
        for result in results:
            strategy_results[result["symbol"]] = result["result"]
        strategy_results_sorted = {k: v for k, v in sorted(strategy_results.items(), key=lambda item: item[1] if type(item[1]) != str else 0, reverse=True)}
        self.strategy_results = strategy_results_sorted
        return strategy_results_sorted

    def create_data_feed(self, symbol):
        """
        Create the data feed for the given symbol
        :return:
        """

        previous_data = self.my_td_ameritrade.get_historical_data_DF(symbol, frequency=1, frequencyType="minute", period=2,
                                                                     periodType="day")
        realtime_data = self.my_idex.get_historical_intraday(symbol)
        realtime_data = realtime_data.fillna(method='ffill')
        realtime_data["date"] = pd.to_datetime(realtime_data.date)

        data = self.merge_realtime_data_and_previous_data(realtime_data, previous_data)
        data = data.resample('30Min').first()
        data.drop(['date'], axis=1)
        return data

    def merge_realtime_data_and_previous_data(self, realtime_data, previous_data):
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

    def write_results_to_json(self, json_path):
        """
        Writes out Results of the strategy to a json
        :param json_path:
        :return:
        """
        with open(json_path, 'w') as f:
            f.write(json.dumps(self.strategy_results, indent=4))

if __name__ == '__main__':
    all_symbols = ['AAPL']
    my_back_trader = BackTrader(SMAStrategy)
    my_back_trader.run_strategy_multiple_symbols(symbol_list=all_symbols, run_all_symbols=False)
    my_back_trader.write_results_to_json("../Data/strategy_results.json")
