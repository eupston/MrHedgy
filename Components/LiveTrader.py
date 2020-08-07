import datetime
import json
import multiprocessing
import time
import os

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
        self.stock_order_times_bought = []
        self.stock_order_times_sold = []
        self.query_market_seconds = 300

    def run_strategy_on_live_market(self):
        """
        Run the loaded strategy on all the stock market gappers
        :return:
        """
        # stock_gappers = self.get_premarket_stock_gappers()
        stock_gappers = ['SQ', 'MARA', 'AVCT']

        # my_trading_strategies = TradingStrategies()
        # cycle_count = 0
        # while True:
        #     print(cycle_count)
        #     tz = timezone('EST')
        #     now = dt.now(tz)
        #     stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
        #     if now > stock_market_opening_time:
        #         time.sleep(1)
        #         cycle_count += 1
        #         continue
        #     with open("../Data/transaction_data_08_06.json", 'r') as f:
        #         all_transaction_data = json.load(f)
        #     for stock in stock_gappers:
        #         result = my_trading_strategies.simple_moving_average_daily_strategy(stock)
        #         symbol_transactions = all_transaction_data.setdefault(result["symbol"], [])
        #         if result['transaction_data']:
        #             symbol_transactions.append(result["transaction_data"])
        #
        #     with open("../Data/transaction_data_08_06.json", 'w') as f:
        #         f.write(json.dumps(all_transaction_data, indent=4))
        #     cycle_count += 1
        #     time.sleep(1)

        while True:
            my_back_trader = BackTrader(self.strategy, self.buy_callback, self.sell_callback)
            my_back_trader.run_strategy_multiple_symbols(symbol_list=stock_gappers)
            time.sleep(self.query_market_seconds)

    def buy_callback(self, symbol, order_datetime):
        """
        The buy callback to for loaded strategy
        :return:
        """
        tz = timezone('EST')
        now = dt.now(tz)
        print("MY BUY CALLBACK for " + symbol + " " + order_datetime)
        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
        if now > stock_market_opening_time and order_datetime not in self.stock_order_times_bought:
            self.stock_order_times_bought.append(order_datetime)
            quote = self.td_ameritrade.get_stock_quote(symbol)
            ask_price = quote["askPrice"]
            transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
            if not os.path.exists(transaction_json_path):
                with open(transaction_json_path, 'w') as outfile:
                    json.dump({}, outfile)
            with open(transaction_json_path, 'r') as f:
                transaction_data = json.load(f)
            transaction_data[str(now)] = {
                "Symbol": symbol,
                "Bought": ask_price,
                "order_time": order_datetime

            }
            with open(transaction_json_path, 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))

    def sell_callback(self, symbol, order_datetime):
        """
        The sell callback to for loaded strategy
        :return:
        """
        tz = timezone('EST')
        now = dt.now(tz)
        print("MY SELL CALLBACK for " + symbol + " " + order_datetime)
        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
        if now > stock_market_opening_time and order_datetime not in self.stock_order_times_sold:
            self.stock_order_times_sold.append(order_datetime)
            quote = self.td_ameritrade.get_stock_quote(symbol)
            bid_price = quote["bidPrice"]
            transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
            if not os.path.exists(transaction_json_path):
                with open(transaction_json_path, 'w') as outfile:
                    json.dump({}, outfile)
            with open(transaction_json_path, 'r') as f:
                transaction_data = json.load(f)
            transaction_data[str(now)] = {
                "Symbol": symbol,
                "Sold": bid_price,
                "order_time": order_datetime
            }
            with open(transaction_json_path, 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))

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
