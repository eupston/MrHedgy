import datetime
import json
import time
import os

from pytz import timezone
from datetime import datetime as dt

from Components.APIs.IEX import IEX
from Components.APIs.TDAmeritrade import TDAmeritrade
from Components.BackTrader import BackTrader
from Components.TradingStrategies import SMAStrategy


class LiveTrader:

    def __init__(self, strategy):
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
        # stock_gappers = self.get_premarket_stock_gappers(watch_list_name="2020-08-11")
        stock_gappers = ['PFNX', 'EQ', 'PECK', 'PLX', 'FBIO']
        print(stock_gappers)
        cycle_count = 0
        while True:
            try:
                my_back_trader = BackTrader(self.strategy, self.buy_callback, self.sell_callback)
                my_back_trader.use_live_intraday_data = True
                my_back_trader.run_strategy_multiple_symbols(symbol_list=stock_gappers)
                my_back_trader.write_results_to_json("../Data/strategy_results_2020-08-11.json")
            except Exception as e:
                print(str(e))
            time.sleep(self.query_market_seconds)
            cycle_count += 1
            print("cycle_count", cycle_count)

    def buy_callback(self, symbol, order_datetime):
        """
        The buy callback to for loaded strategy
        :return:
        """
        tz = timezone('EST')
        now = dt.now(tz)
        print("MY BUY CALLBACK for " + symbol + " " + order_datetime)
        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
        transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
        if not os.path.exists(transaction_json_path):
            with open(transaction_json_path, 'w') as outfile:
                json.dump({}, outfile)
        with open(transaction_json_path, 'r') as f:
            transaction_data = json.load(f)
        transaction_data.setdefault(symbol, {})

        if now > stock_market_opening_time and order_datetime not in transaction_data[symbol].keys():
            quote = self.td_ameritrade.get_stock_quote(symbol)
            ask_price = quote["askPrice"]

            transaction_data[symbol][order_datetime] = {
                "Bought": ask_price,
                "eastern_time": str(now)
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
        transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
        if not os.path.exists(transaction_json_path):
            with open(transaction_json_path, 'w') as outfile:
                json.dump({}, outfile)
        with open(transaction_json_path, 'r') as f:
            transaction_data = json.load(f)
        transaction_data.setdefault(symbol, {})

        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0)
        if now > stock_market_opening_time and order_datetime not in transaction_data[symbol].keys():
            quote = self.td_ameritrade.get_stock_quote(symbol)
            bid_price = quote["bidPrice"]
            transaction_data[symbol][order_datetime] = {
                "Sold": bid_price,
                "eastern_time": str(now)
            }
            with open(transaction_json_path, 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))

    def get_premarket_stock_gappers(self, watch_list_name=None):
        """
        gets all the current premarket stock gappers
        :return: A list of the stock symbols
        """
        stock_gappers = []
        if not watch_list_name:
            today = datetime.datetime.utcnow().date()
            yesterday = today - datetime.timedelta(days=1)
            watch_list_name = str(yesterday)
        watch_list = self.td_ameritrade.get_watch_list(watch_list_name)

        for stock in watch_list['watchlistItems']:
            stock_gappers.append(stock['instrument']['symbol'])
        return stock_gappers

if __name__ == '__main__':
    my_live_trader = LiveTrader(SMAStrategy)
    my_live_trader.run_strategy_on_live_market()
