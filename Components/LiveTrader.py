import datetime
import json
import multiprocessing
import time

from pytz import timezone
from datetime import datetime as dt

from Components.APIs.IEX import IEX
from Components.APIs.TDAmeritrade import TDAmeritrade
from Components.BackTrader import BackTrader
from Components.TradingStrategies import SMAStrategy, TradingStrategies


class LiveTrader:

    def __init__(self,strategy):
        self.td_ameritrade = TDAmeritrade()
        self.iex = IEX()
        self.strategy = strategy
        self.cash_limit = 100

    def run_strategy_on_live_market(self):
        """
        Run the loaded strategy on all the stock market gappers
        :return:
        """
        stock_gappers = self.get_premarket_stock_gappers()
        print(stock_gappers)
        my_trading_strategies = TradingStrategies()
        cycle_count = 0
        while True:
            print(cycle_count)
            tz = timezone('EST')
            now = dt.now(tz)
            stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
            if now < stock_market_opening_time:
                time.sleep(1)
                cycle_count += 1
                continue
            with open("../Data/transaction_data.json", 'r') as f:
                all_transaction_data = json.load(f)
            for stock in stock_gappers:
                result = my_trading_strategies.simple_moving_average_daily_strategy(stock)
                symbol_transactions = all_transaction_data.setdefault(result["symbol"], [])
                symbol_transactions.append(result["transaction_data"])

            with open("../Data/transaction_data.json", 'w') as f:
                f.write(json.dumps(all_transaction_data, indent=4))
            cycle_count += 1
            time.sleep(1)

        #TODO implement backtrader solution
        # my_back_trader = BackTrader(self.strategy, self.buy_callback, self.sell_callback)
        # my_back_trader.run_strategy_multiple_symbols(symbol_list=stock_gappers)

    def buy_callback(self, symbol):
        """
        The buy callback to for loaded strategy
        :return:
        """
        print("MY BUYYY CALLBACK for " + symbol)
        # stocks_bought = self.td_ameritrade.buy_stock_with_cash_limit(symbol, cash_limit=self.cash_limit, simulation=True)

    def sell_callback(self, symbol):
        """
        The sell callback to for loaded strategy
        :return:
        """
        print("MY SELL CALLBACK for " + symbol)

    def get_premarket_stock_gappers(self):
        """
        gets all the current premarket stock gappers
        :return: A list of the stock symbols
        """
        stock_gappers = []
        today = datetime.datetime.utcnow().date()
        yesterday = today - datetime.timedelta(days=1)
        watch_list = self.td_ameritrade.get_watch_list(str(yesterday))

        for stock in watch_list['watchlistItems']:
            stock_gappers.append(stock['instrument']['symbol'])
        return stock_gappers

if __name__ == '__main__':
    my_live_trader = LiveTrader(SMAStrategy)
    my_live_trader.run_strategy_on_live_market()
