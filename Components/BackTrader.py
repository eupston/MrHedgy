from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import multiprocessing
from Components.APIs.AlphaVantage import AlphaVantage
from Components.TradingStrategies import *
import datetime
import logging
import sys

logging.basicConfig(filename=f"../logs/{__name__}.log", level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class BackTrader:
    """Class for Back testing Strategies"""
    def __init__(self, strategy, buy_callback=None, sell_callback=None, live_trading=False):
        self.my_td_ameritrade = TDAmeritrade()
        self.my_idex = IEX()
        self.my_alpha_vantage = AlphaVantage()
        self.all_symbols = self.my_idex.supported_symbols
        self.strategy = strategy
        self.cash_amount = 1000.0
        self.strategy_result = strategy
        self.buy_callback = buy_callback
        self.sell_callback = sell_callback
        self.resample_amt = "30T"
        self.live_trading = live_trading
        self.use_historical_data = True
        self.use_live_intraday_data = False
        today = datetime.datetime.utcnow().date()
        three_days_ago = today - datetime.timedelta(days=3)
        self.clip_date_from = str(three_days_ago)
        self.look_back_days = 60
        self.minute_frequency = 15
        self.show_plot = False

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
            cerebro.addstrategy(self.strategy,
                                symbol=symbol,
                                buy_callback=self.buy_callback,
                                sell_callback=self.sell_callback,
                                live_trading=self.live_trading)

            # Create a Data Feed
            if self.use_live_intraday_data:
                market_data = self.create_live_data_feed(symbol)
            elif self.use_historical_data:
                market_data = self.create_historical_data_feed(symbol)
            print(market_data)
            data = bt.feeds.PandasData(dataname=market_data)

            # Add the Data Feed to Cerebro
            cerebro.adddata(data)

            # Set our desired cash start
            cerebro.broker.setcash(self.cash_amount)

            # Print out the starting conditions
            logger.info('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
            # Run over everything
            cerebro.run()

            # Print out the final result
            logger.info('Final Portfolio Value: %.2f for %s' % (cerebro.broker.getvalue(), symbol))
            if self.show_plot:
                cerebro.plot()
            return {"symbol": symbol, "result": cerebro.broker.getvalue()}
        except Exception as e:
            error = str(e)
            logger.exception(e)
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
        with multiprocessing.Pool() as pool:
            results = pool.map(self.run_strategy, symbols_to_run)
        for result in results:
            strategy_results[result["symbol"]] = result["result"]
        strategy_results_sorted = {k: v for k, v in sorted(strategy_results.items(), key=lambda item: item[1] if type(item[1]) != str else 0, reverse=True)}
        self.strategy_results = strategy_results_sorted
        return strategy_results_sorted

    def create_live_data_feed(self, symbol):
        """
        Creates a live data feed from alpha vantage api
        :return:
        """
        data = self.my_alpha_vantage.get_intraday(symbol, clip_date_from=self.clip_date_from)

        data = data.resample(self.resample_amt).first()
        print(symbol, data)

        return data

    def create_historical_data_feed(self, symbol):
        """
        Create the historical data feed for the given symbol from  td ameritrade data
        :return:
        """
        data = self.my_td_ameritrade.get_historical_data_DF(symbol, minute_frequency=self.minute_frequency, look_back_days=self.look_back_days)
        return data

    def write_results_to_json(self, json_path):
        """
        Writes out Results of the strategy to a json
        :param json_path:
        :return:
        """
        with open(json_path, 'w') as f:
            f.write(json.dumps(self.strategy_results, indent=4))

if __name__ == '__main__':
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 150)
    all_symbols = ['SQ', "AAPL", "SPY", "GOOG", "TSLA", "FB", "MSFT", "SONN", 'MARA', 'AVCT']
    all_symbols = ['RMED', 'SNSS', 'PECK', 'PEIX', 'FBIO']

    my_back_trader = BackTrader(SMAStrategy)
    # all_symbols = my_back_trader.my_idex.supported_symbols
    my_back_trader.run_strategy_multiple_symbols(symbol_list=all_symbols, run_all_symbols=False)
    # my_back_trader.show_plot = True
    # my_back_trader.run_strategy(symbol="SONN")
    my_back_trader.write_results_to_json("../Data/strategy_results.json")
