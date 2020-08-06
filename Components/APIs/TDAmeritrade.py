import os
import shutil
import math
import json
import time
import tdameritrade
from tdameritrade import auth
import requests
from dotenv import load_dotenv,find_dotenv
import pandas as pd

load_dotenv(find_dotenv())

#TODO Create decorator for client session
class TDAmeritrade:

    def __init__(self):
        self.td_client = None
        self.access_token = None
        self.check_install_dependencies()
        self.get_ameritrade_access_token_from_refresh_token()

    def check_install_dependencies(self):
        """
        installs all dependencies if they do not already exist
        :return:
        """
        chrome_driver_dest = "/usr/local/bin/chromedriver"
        if not os.path.exists(chrome_driver_dest):
            script_dir = os.path.dirname(os.path.realpath(__file__))
            dependency_path = os.path.join(script_dir, "../Dependencies")
            chrome_driver_path = os.path.join(dependency_path, "TDAmeritrade/chromedriver")
            shutil.copyfile(chrome_driver_path, chrome_driver_dest)
            os.system(f"chmod +x {chrome_driver_dest}")

    def get_client_session(self):
        return self.td_client

    def start_client_session(self):
        self.td_client = tdameritrade.TDClient(self.access_token)

    def get_ameritrade_access_token(self):
        consumer_key=os.getenv("TDAMERITRADE_CLIENT_ID")
        uri = os.getenv("TDAMERITRADE_URI")
        response = auth.authentication(consumer_key, uri, os.getenv("TDAMERITRADE_USERNAME"), os.getenv("TDAMERITRADE_PASSWORD"))
        self.access_token = response['access_token']
        return self.access_token

    def get_ameritrade_access_token_from_refresh_token(self):
        # https://developer.tdameritrade.com/content/simple-auth-local-apps
        REFRESH_TOKEN = os.getenv('TDAMERITRADE_REFRESH_TOKEN')
        CONSUMER_KEY = os.getenv('TDAMERITRADE_CLIENT_ID')
        ACCESS_TOKEN_ENDPOINT = os.getenv('ACCESS_TOKEN_ENDPOINT')
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': REFRESH_TOKEN,
            'client_id': CONSUMER_KEY
        } #TODO try except catch block incase error
        response = requests.post(url=ACCESS_TOKEN_ENDPOINT, data=payload, verify=True)
        self.access_token = response.json()['access_token']
        return self.access_token

    def get_stock_quote(self, symbol):
        """
        Get the stock Quote with the given symbol
        :param symbol:
        :return:
        """
        self.start_client_session()
        quote = self.td_client.quote(symbol)
        if quote:
            return quote[symbol]
        else:
            return {}

    def get_orders(self):
        result = self.td_client.accounts(orders=True)
        return result

    def get_watch_list(self, watch_list_name):
        """
        Get the given watch list from think or swim account
        :param watch_list_name:
        :return:
        """
        accountId = os.getenv('TDAMERITRADE_ACCOUNT_ID')

        url = f"https://api.tdameritrade.com/v1/accounts/{accountId}/watchlists"
        headers = {'Authorization': 'Bearer ' + self.access_token, "Content-Type": "application/json"}
        response = requests.get(url, headers=headers)
        if not response.status_code == 200:
            print(response.json())
            raise Exception("Order Status Not Complete. Status Code: {}".format(response.status_code))
        all_watch_lists = response.json()
        for item in all_watch_lists:
            if item['name'] == watch_list_name:
                return item
        raise Exception("Could Not Find Watch List")

    def buy_stock_with_cash_limit(self, symbol, cash_limit, simulation=False):
        """
        Buys as many stock as possible with the given cash limit at market value
        :param symbol: the stock symbol
        :param cash_limit: cash limit as float
        :param simulation: True or False if transaction to be made is real or simulated
        :return: stock order quantity placed or raise exception if cant order
        """
        quote = self.get_stock_quote(symbol)
        ask_price = quote["askPrice"]
        stock_order_quantity = math.floor(cash_limit / ask_price)
        if simulation:
            return {"ask_price": ask_price, "stock_order_quantity": stock_order_quantity}
        else:
            try:
                self.place_stock_order(symbol, stock_order_quantity, "Buy")
                return {"ask_price": ask_price, "stock_order_quantity": stock_order_quantity}
            except Exception as e:
                print(e)
                raise Exception(e)

    def place_stock_order(self, symbol, quantity, instructions):
        """
        places an order with the given symbol. For more details visits:
        https://developer.tdameritrade.com/content/place-order-samples
        :param symbol: the company symbol
        :param quantity: how many stock to place in the order
        :param instructions: Buy or Sell
        :return: True if order was placed else raises error
        """
        self.start_client_session()
        accountId = os.getenv('TDAMERITRADE_ACCOUNT_ID')
        order = {
              "orderType": "MARKET",
              "session": "NORMAL",
              "duration": "DAY",
              "orderStrategyType": "SINGLE",
              "orderLegCollection": [
                {
                  "instruction": instructions,
                  "quantity": quantity,
                  "instrument": {
                    "symbol": symbol,
                    "assetType": "EQUITY"
                  }
                }
              ]
        }
        url = f"https://api.tdameritrade.com/v1/accounts/{accountId}/orders"
        headers = {'Authorization': 'Bearer ' + self.access_token, "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=order)
        if not response.status_code == 201:
            print(response.json())
            raise Exception("Order Status Not Complete. Status Code: {}".format(response.status_code))
        return True

    def get_all_positions(self):
        """
        Gets all positions currently in account
        :return: dict of all positions found
        """
        self.start_client_session()
        act = self.td_client.accounts(positions=True)
        positions = act[list(act.keys())[0]]['securitiesAccount']['positions']
        return positions

    def get_single_position(self, symbol):
        """
        Gets a single given position from the account
        :return: the position if found else empty dict
        """
        all_positions = self.get_all_positions()
        found_position = {}
        if not all_positions:
            return found_position
        for position in all_positions:
            if position['instrument']['symbol'] == symbol:
                found_position = position
                break
        return found_position

    def get_movers(self, index="$SPX.X", direction='up', change_type='percent'):
        """
        Get the top ten mover stock with the given percentage and direction
        :param index: $COMPX, $DJI or $SPX.X
        :param direction: up or down
        :param change_type: percent or value
        :return:
        """
        self.start_client_session()
        movers = self.td_client.movers(index, direction, change_type)
        return movers

    def get_historical_data(self, symbol, frequency=1, frequencyType="minute", period=1, periodType="day"):
        """
        Gets the historical data of the given stock
        https://developer.tdameritrade.com/price-history/apis/get/marketdata/%7Bsymbol%7D/pricehistory
        :param symbol:
        :param frequency: int of the frequency ie 1, 2, 3, 4, 5, 10
        :param frequencyType: the frequency interval minute, daily, month, weekly, monthly
        :param period: int of the period ie 1, 2, 3
        :param periodType: type of period day, month, year, ytd
        :return:
        """
        self.start_client_session()
        kwargs = {'frequency': frequency, 'frequencyType': frequencyType, 'period': period, 'periodType': periodType}
        history = self.td_client.history(symbol, **kwargs)
        return history

    def get_historical_data_DF(self, symbol, frequency=1, frequencyType="minute", period=1, periodType="day"):
        """
        Gets the historical dataframe of the given stock
        https://developer.tdameritrade.com/price-history/apis/get/marketdata/%7Bsymbol%7D/pricehistory
        :param symbol:
        :param frequency: int of the frequency ie 1, 2, 3, 4, 5, 10
        :param frequencyType: the frequency interval minute, daily, month, weekly, monthly
        :param period: int of the period ie 1, 2, 3
        :param periodType: type of period day, month, year, ytd
        :return:
        """
        self.start_client_session()
        kwargs = {'frequency': frequency, 'frequencyType': frequencyType, 'period': period, 'periodType': periodType}

        response = requests.get(f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory",
                             headers={'Authorization': 'Bearer ' + self.access_token},
                             params=kwargs)
        if response.status_code == 429:
            time.sleep(1.5)
            self.get_historical_data_DF(symbol, frequency, frequencyType, period, periodType)
        if not response.status_code == 200:
            raise Exception("Could not get historical Data. Status Code: {}".format(response.status_code))
        x = response.json()
        df = pd.DataFrame(x['candles'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        return df

    def execute_transaction_from_dict(self, transaction_dict, percent_range_execute_limit, buy_cash_limit):
        """
        Executes all transactions with the given dictionary Buy or Sell
        :param transaction_dict: dictionary with symbols, found price, and market price
        :param percent_range_execute_limit:
        :param buy_cash_limit:
        :return: the transaction dict that's been updated with success or not
        """
        self.start_client_session()
        for symbol in transaction_dict['found_transactions'].keys():
            transact_data = transaction_dict['found_transactions'][symbol]
            transaction_type = transact_data['transaction_type']
            transaction_price = transact_data['transaction_price']
            askPrice = transact_data['tdameritrade']['askPrice']
            bidPrice = transact_data['tdameritrade']['bidPrice']
            if transaction_type == "Buy":
                percent_diff_from_market = max(askPrice, transaction_price) / min(askPrice, transaction_price) - 1.0
                if percent_diff_from_market < percent_range_execute_limit:
                    try:
                        amt_stock_bought = self.buy_stock_with_cash_limit(symbol, buy_cash_limit)
                        print(f"Bought {amt_stock_bought} of {symbol} for ${askPrice} per Share ")
                        transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = True
                        transaction_dict['found_transactions'][symbol]["amount_stock_bought"] = amt_stock_bought
                    except Exception as err:
                        transaction_dict['found_transactions'][symbol]["transaction_failed_info"] = str(err)
                        transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = False
                else:
                    transaction_dict['found_transactions'][symbol]["transaction_failed_info"] = "Market price outside Percentage execute limit"
                    transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = False
            if transaction_type == "Sell":
                percent_diff_from_market = max(bidPrice, transaction_price) / min(bidPrice, transaction_price) - 1.0
                if percent_diff_from_market < percent_range_execute_limit:
                    found_position = self.get_single_position(symbol)
                    if found_position:
                        all_owned_stock_amt = found_position['longQuantity']
                        trans_success = self.place_stock_order(symbol, all_owned_stock_amt, "Sell")
                        print(f"Sold {all_owned_stock_amt} of {symbol} for ${bidPrice} per Share ")
                        transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = trans_success
                        transaction_dict['found_transactions'][symbol]["amount_stock_sold"] = all_owned_stock_amt
                    else:
                        transaction_dict['found_transactions'][symbol]["transaction_failed_info"] = "No Positions found to Sell"
                        transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = False
                else:
                    transaction_dict['found_transactions'][symbol]["transaction_failed_info"] = "Market price outside Percentage execute limit"
                    transaction_dict['found_transactions'][symbol]["success_submitted_transaction"] = False

        return transaction_dict

if __name__ == '__main__':
    pd.set_option('display.max_rows', None)

    my_tdameritrade = TDAmeritrade()
    data = my_tdameritrade.get_historical_data_DF("AAPL", frequency=1, frequencyType="minute", period=10, periodType="day")
    print(data)
    # watch = my_tdameritrade.get_watch_list("default")
    # print(watch)
    # positions = my_tdameritrade.get_all_positions()
    # position = my_tdameritrade.get_single_position("CCL")
    # print(position)
    # order = my_tdameritrade.place_stock_order("INO", 1, "Sell")
    # print(order)
    # BUY_CASH_LIMIT = 100.00
    # PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT = 0.05
    # trans_dict = my_tdameritrade.execute_transaction_from_dict(test_transaction, PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT, BUY_CASH_LIMIT)
    # print(json.dumps(trans_dict, indent=4))


