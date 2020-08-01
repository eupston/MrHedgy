from datetime import datetime
import pandas as pd
from iexfinance.stocks import get_historical_intraday
import os
from dotenv import load_dotenv,find_dotenv

load_dotenv(find_dotenv())

class IEX:

    def __init__(self):
        self.token = os.getenv("IEX_API_TOKEN")

    def get_historical_intraday(self, symbol, date=None):
        """
        Function to obtain intraday one-minute pricing data for one
        symbol on a given date (defaults to current date) FREE
        Parameters
        ----------
        symbol: str
            A single ticker
        date: datetime.datetime, default current date
            Desired date for intraday retrieval, defaults to today
            Can be three months prior to the current day
        Returns
        -------
        list or DataFrame
            Intraday pricing data for specified symbol on given date
        """

        dataframe = get_historical_intraday(symbol, date=date, output_format='pandas', token=self.token)
        return dataframe


if __name__ == '__main__':
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 150)
    my_idex = IEX()
    date = datetime(2020, 7, 30)
    data = my_idex.get_historical_intraday("SQ", date=date)
    data["date"] = pd.to_datetime(data.date)
    data.set_index("date")
    print(data)