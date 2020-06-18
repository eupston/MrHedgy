import os
import re
from Components.Outlook import Outlook
from Components.TDAmeritrade import TDAmeritrade
from dotenv import load_dotenv, find_dotenv
import time
import json
from datetime import datetime

load_dotenv(find_dotenv())


def main():
    my_tdameritrade = TDAmeritrade()
    my_outlook = Outlook()
    time_interval_seconds = 10
    current_datetime = datetime.now()
    # current_date = str(current_datetime.date())
    current_date = "2020-06-16"
    trigger_words = ["bought", "sold"]
    while True:
        with open("Data/transaction_data.json", 'r') as f:
            json_transaction_data = json.load(f)

            messages = my_outlook.get_email_body_messages("eupston130@hotmail.com", "Kyle Dennis",
                                                          f"subject:TWK AND received>={current_date}")
            ids_not_entered_yet = [id for id in messages.keys() if id  in json_transaction_data.keys()]
            for id in ids_not_entered_yet:
                json_transaction_data[id] = messages[id]
                current_message = messages[id]
                body_preview = current_message["body_preview"]
                found_trigger_words = [word for word in trigger_words if word in body_preview]
                if found_trigger_words:
                    # print(body_preview)
                    trigger_word_onward = body_preview[body_preview.find(found_trigger_words[0]):]
                    stock_symbols = re.findall('\w*[A-Z]\w*[A-Z]\w*', trigger_word_onward)
                    if stock_symbols:
                        print("stock symbol found :",  stock_symbols[0])
                        quote = my_tdameritrade.get_stock_quote(stock_symbols[0])
                        if quote:
                            print(quote)


        with open("Data/transaction_data.json", 'w') as f:
            f.write(json.dumps(json_transaction_data, indent=4))

        time.sleep(time_interval_seconds)





if __name__ == '__main__':
    main()




