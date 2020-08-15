from finviz.screener import Screener

class StockSceener:

    def __init__(self):
        self.filters = None
        self.URL_str = None

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

if __name__ == '__main__':
    my_stock_screener = StockSceener()
    stocks = my_stock_screener.get_top_gainers()
    print(stocks)

# Export the screener results to .csv
# stock_list.to_csv()
# print(stock_list)

# Create a SQLite database
# stock_list.to_sqlite("stock.sqlite3")

# # Add more filters
# stock_list.add(filters=['fa_div_high'])  # Show stocks with high dividend yield
# # or just stock_list(filters=['fa_div_high'])