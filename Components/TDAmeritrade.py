import os
import math
import json
import tdameritrade
from tdameritrade import auth
import requests
from dotenv import load_dotenv,find_dotenv

load_dotenv(find_dotenv())

#TODO Create decorator for client session
class TDAmeritrade:

    def __init__(self):
        self.td_client = None
        self.access_token = None

    def get_client_session(self):
        return self.td_client

    def start_client_session(self):
        self.get_ameritrade_access_token_from_refresh_token()
        self.td_client = tdameritrade.TDClient(self.access_token)

    def get_ameritrade_access_token(self):
        # TODO copy chromedriver to "/usr/local/bin/chromedriver" if doesn't exist
        consumer_key=os.getenv("TDAMERITRADE_CLIENT_ID")
        uri = os.getenv("TDAMERITRADE_URI")
        response = auth.authentication(consumer_key, uri, os.getenv("TDAMERITRADE_USERNAME"), os.getenv("TDAMERITRADE_PASSWORD"))
        self.access_token = response['access_token']
        return self.access_token

    def get_ameritrade_access_token_from_refresh_token(self):
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

    def buy_stock_with_cash_limit(self, symbol, cash_limit):
        """
        Buys as many stock as possible with the given cash limit at market value
        :param symbol: the stock symbol
        :param cash_limit: cash limit as float
        :return: stock order quantity placed or raise exception if cant order
        """
        quote = self.get_stock_quote(symbol)
        ask_price = quote["askPrice"]
        stock_order_quantity = math.floor(cash_limit / ask_price)
        try:
            self.place_stock_order(symbol, stock_order_quantity, "Buy")
            return stock_order_quantity
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
            raise Exception("Order Status Not Complete. Status Code: {}".format(response.status_code))
        return True

    def get_all_positions(self):
        """
        Gets all positions currently in account
        :return: dict of all positions found
        """
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
    my_tdameritrade = TDAmeritrade()
    # quote = my_tdameritrade.get_stock_quote("LK")
    # positions = my_tdameritrade.get_all_positions()
    # position = my_tdameritrade.get_single_position("CCL")
    # print(position)
    # order = my_tdameritrade.place_stock_order("CCL", position['longQuantity'], "Sell")
    # print(order)
    BUY_CASH_LIMIT = 100.00
    PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT = 0.05
    # trans_dict = my_tdameritrade.execute_transaction_from_dict(test_transaction, PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT, BUY_CASH_LIMIT)
    # print(json.dumps(trans_dict, indent=4))


