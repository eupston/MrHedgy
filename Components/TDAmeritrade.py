import os
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
        self.start_client_session()
        quote = self.td_client.quote(symbol)

        if quote:
            return quote[symbol]
        else:
            return {}

    def place_stock_order(self, symbol, quantity, instructions):
        """
        places an order with the given symbol. For more details visits:
        https://developer.tdameritrade.com/content/place-order-samples
        :param symbol: the company symbol
        :param quantity: how many stock to place in the order
        :param instructions: Buy or Sell
        :return:
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
        # order = self.td_client.orders(account_id=accountId, json_order=order)
        if not response.status_code == 201:
            raise Exception("Order Status Not Complete. Status Code: {}".format(response.status_code))

if __name__ == '__main__':
    my_tdameritrade = TDAmeritrade()
    quote = my_tdameritrade.get_stock_quote("LK")
    print(quote)
    # my_tdameritrade.start_client_session()
    # td = my_tdameritrade.get_client_session()
    # order = my_tdameritrade.place_stock_order("LK", 1)
    # print(order)

