import os
from dotenv import load_dotenv, find_dotenv
from alpha_vantage.timeseries import TimeSeries
import matplotlib.pyplot as plt
import pandas as pd

load_dotenv(find_dotenv())

class AlphaVantage:
    # 5 API requests per minute and 500 requests per day
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    def get_intraday(self, symbol, interval='1min', clip_date_from=False):
        """
        Gets the intraday data with the given symbol
        :param symbol:
        :param interval:
        :param clip_date_from: enter yyyy-mm-dd for where to clip data from or False
        :return:
        """
        ts = TimeSeries(key=self.api_key, output_format='pandas')
        data, meta_data = ts.get_intraday(symbol=symbol, interval=interval, outputsize='full')
        data = data.iloc[::-1]
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        if clip_date_from:
            data = data[(data.index > clip_date_from)]
        return data

if __name__ == '__main__':
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 150)

    my_alpha_vantage = AlphaVantage()
    data = my_alpha_vantage.get_intraday("SQ", clip_date_from='2020-08-04')
    print(data)
