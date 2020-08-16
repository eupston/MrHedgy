from finviz.screener import Screener
from Components.APIs.IEX import IEX
from Components.APIs.TDAmeritrade import TDAmeritrade
from datetime import datetime
import logging
import sys
import multiprocessing
import os
import json

logging.basicConfig(filename=f"../../logs/{os.path.splitext(os.path.basename(__file__))[0]}.log", level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class StockSceener:

    def __init__(self):
        self.filters = None
        self.URL_str = None
        self.iex = IEX()
        self.td_ameritrade = TDAmeritrade()
        self.look_back_days = 0
        self.top_gainers = {}

    def get_top_gainers(self, filter_num=20):
        """
        Get the stop gainers for the previous day
        :param filter_num: number of stocks to filter
        :return: a list of stocks
        """
        str = "https://finviz.com/screener.ashx?v=141&s=ta_topgainers&o=-change"
        stock_list = Screener.init_from_url(str)
        stock_gainers = []
        for stock in stock_list[0:filter_num]:
            stock_gainers.append(stock['Ticker'])
        return stock_gainers

    def get_historical_top_gainer(self, date_str="2020-08-14", clip_top_gainers=20):
        """
        Writes all the historical top gainers to a json
        :return:
        """
        all_stock_symbols = self.iex.supported_symbols
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        requested_datetime_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if requested_datetime_obj >= current_date:
            raise ValueError(f"{date_str} is invalid. Date must be in the past.")
        look_back_days_obj = current_date - requested_datetime_obj
        self.look_back_days = int(str(look_back_days_obj).split(" ")[0])
        all_stock_percentage_change = {}
        with multiprocessing.Pool() as pool:
            results = pool.map(self.get_percentage_change, all_stock_symbols)
        for result in results:
            all_stock_percentage_change[list(result.keys())[0]] = result[list(result.keys())[0]]
        all_stocks_percentage_change_sorted = {k: v for k, v in sorted(all_stock_percentage_change.items(), key=lambda item: item[1]['percentage_change'], reverse=True)}
        logger.info(f"Total all_stocks_percentage_change are {len(all_stocks_percentage_change_sorted.keys())}")
        self.top_gainers = {k: v for(k, v) in [x for x in all_stocks_percentage_change_sorted.items()][:clip_top_gainers]}
        return self.top_gainers

    def get_percentage_change(self, symbol):
        """
        Gets the percentage change of the given symbol
        :param symbol:
        :return:
        """
        stock_percentage_change = {}
        logger.info(f"Currently Processing {symbol}")
        try:
            data = self.td_ameritrade.get_historical_data_DF(symbol, minute_frequency=30, look_back_days=self.look_back_days)
            data = data.fillna(method='ffill')
            opening_price = data['close'][0]
            closing_price = data['close'][-1]
            opening_time = str(data.index[0])
            closing_time = str(data.index[-1])
            percentage_change = (closing_price - opening_price) / opening_price
            stock_percentage_change[symbol] = {
                "percentage_change": percentage_change,
                "opening_time": opening_time,
                "closing_time": closing_time,
                "opening_price": opening_price,
                "closing_price": closing_price
            }
            return stock_percentage_change
        except Exception as e:
            logger.exception(e)
            stock_percentage_change[symbol] = {
                "percentage_change": float('-inf'),
                "exception": str(e)
            }
            return stock_percentage_change

    def write_top_gainers_json(self, json_path):
        """
        Writes all the top gainers to a json file
        :return:
        """
        with open(json_path, 'w') as f:
            f.write(json.dumps(self.top_gainers, indent=4))

if __name__ == '__main__':
    requested_date = "2020-08-14"
    my_stock_screener = StockSceener()
    top_gainers = my_stock_screener.get_historical_top_gainer(date_str=requested_date)
    my_stock_screener.write_top_gainers_json(f"../../Data/TopGainers/Top_gainers_{requested_date}.json")

# Export the screener results to .csv
# stock_list.to_csv()
# print(stock_list)

# Create a SQLite database
# stock_list.to_sqlite("stock.sqlite3")

# # Add more filters
# stock_list.add(filters=['fa_div_high'])  # Show stocks with high dividend yield
# # or just stock_list(filters=['fa_div_high'])