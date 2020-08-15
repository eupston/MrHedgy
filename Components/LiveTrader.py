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
from Components.StockScreener import StockSceener
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

#TODO Create stock gap scanner
class LiveTrader:

    def __init__(self, strategy):
        self.td_ameritrade = TDAmeritrade()
        self.iex = IEX()
        self.stock_screener = StockSceener()
        self.strategy = strategy
        self.cash_limit = 100
        self.stock_order_times_bought = []
        self.stock_order_times_sold = []
        self.query_market_seconds = 2

    def run_strategy_on_live_market(self):
        """
        Run the loaded strategy on all the stock market gappers
        :return:
        """
        stock_gappers = self.get_premarket_stock_gappers(watch_list_name="2020-08-14")
        # stock_gappers =['HTBX', 'NTN', 'IGC', 'FAT', 'SNDL']
        # stock_gappers = self.stock_screener.get_top_gainers()
        logger.info(stock_gappers)
        cycle_count = 0
        now = dt.now()
        while True:
            try:
                my_back_trader = BackTrader(self.strategy, self.buy_callback, self.sell_callback, live_trading=True)
                my_back_trader.live_trading = True
                my_back_trader.run_strategy_multiple_symbols(symbol_list=stock_gappers)
                my_back_trader.write_results_to_json(f"../Data/{str(now.date())}.json")
            except Exception as e:
                logger.exception(e)
            time.sleep(self.query_market_seconds)
            cycle_count += 1
            logger.info(f"cycle_count {cycle_count}")

    def buy_callback(self, symbol, order_datetime):
        """
        The buy callback to for loaded strategy
        :return:
        """
        tz = timezone('EST')
        now = dt.now(tz)
        transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
        if not os.path.exists(transaction_json_path):
            with open(transaction_json_path, 'w') as outfile:
                json.dump({}, outfile)
        with open(transaction_json_path, 'r') as f:
            transaction_data = json.load(f)
        transaction_data.setdefault(symbol, {})
        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0).replace(tzinfo=None)
        order_datetime_obj = dt.strptime(order_datetime, '%Y-%m-%d %H:%M:%S')
        if order_datetime_obj > stock_market_opening_time and order_datetime not in transaction_data[symbol].keys() and self.is_stock_market_open():
            quote = self.td_ameritrade.get_stock_quote(symbol)
            ask_price = quote["askPrice"]
            logger.info(f"BUY CALLBACK: Order Place for {symbol} order datetime is order_datetime_obj={order_datetime_obj} & stock_market_opening_time={stock_market_opening_time} for ${ask_price}")
            transaction_data[symbol][order_datetime] = {
                "transaction_type": "Bought",
                "price": ask_price,
                "transaction_time_EST": str(now),
                "transaction_time_NZST": str(dt.now())
            }
            with open(transaction_json_path, 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))

    def sell_callback(self, symbol, order_datetime):
        """
        The sell callback to for loaded strategy
        :return:
        """
        #TODO fix bug where if it'll sell even if no stocks have been bought yet
        tz = timezone('EST')
        now = dt.now(tz)
        transaction_json_path = f"../Data/transaction_data_{str(now.date())}.json"
        if not os.path.exists(transaction_json_path):
            with open(transaction_json_path, 'w') as outfile:
                json.dump({}, outfile)
        with open(transaction_json_path, 'r') as f:
            transaction_data = json.load(f)
        transaction_data.setdefault(symbol, {})

        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0).replace(tzinfo=None)
        order_datetime_obj = dt.strptime(order_datetime, '%Y-%m-%d %H:%M:%S')
        if order_datetime_obj > stock_market_opening_time.replace(tzinfo=None) and order_datetime not in transaction_data[symbol].keys() and self.is_stock_market_open():
            quote = self.td_ameritrade.get_stock_quote(symbol)
            bid_price = quote["bidPrice"]
            logger.info(f"SELL CALLBACK: Order Place for {symbol} order datetime is {order_datetime} for ${bid_price}")
            transaction_data[symbol][order_datetime] = {
                "transaction_type": "Sold",
                "price": bid_price,
                "transaction_time_EST": str(now),
                "transaction_time_NZST": str(dt.now())
            }
            with open(transaction_json_path, 'w') as f:
                f.write(json.dumps(transaction_data, indent=4))

    def is_stock_market_open(self, include_after_hours=False):
        """
        Checks to if the stock market is currently open
        :param include_after_hours:
        :return: True or False
        """
        tz = timezone('EST')
        now = dt.now(tz)
        current_time = now.replace(microsecond=0).replace(tzinfo=None)
        stock_market_opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0).replace(tzinfo=None)
        open_weekday_list = [0, 1, 2, 3, 4]
        current_weekday = stock_market_opening_time.weekday()
        if include_after_hours:
            opening_time = now.replace(hour=4, minute=0, second=0, microsecond=0).replace(tzinfo=None)
            closing_time = now.replace(hour=20, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        else:
            opening_time = now.replace(hour=8, minute=29, second=0, microsecond=0).replace(tzinfo=None)
            closing_time = now.replace(hour=4, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        if current_weekday in open_weekday_list and opening_time < current_time and current_time < closing_time:
            return True
        else:
            return False



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
