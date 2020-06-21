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
    BUY_CASH_LIMIT = 100.00
    PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT = 0.05
    current_datetime = datetime.now()
    current_date_list = str(current_datetime.date()).split("-")
    current_date_minus_one_day = "-".join(current_date_list[0:2]) + "-" + str(int(current_date_list[-1]) - 1)
    # current_date_minus_one_day = "2020-06-14"
    ping_count = 0
    trigger_words = ["bought", "sold", "added"]
    while True:
        with open("Data/transaction_data.json", 'r') as f:
            json_transaction_data = json.load(f)

            messages = my_outlook.get_email_body_messages("eupston130@hotmail.com", "Kyle Dennis",
                                                          f"subject:TWK AND received>={current_date_minus_one_day}")
            ping_count += 1
            ids_not_entered_yet = [id for id in messages.keys() if id not in json_transaction_data.keys()]
            for id in ids_not_entered_yet:
                print("-"*40)
                json_transaction_data[id] = messages[id]
                current_message = messages[id]
                body = current_message["body"]
                subject = current_message["subject"]
                subject_cleaned = re.sub(r'[\,\!\?]', ' ', subject)
                body_cropped = body[:body.find("Cheers")]
                body_cropped = re.sub(r'\.([^0-9])', r' \1', body_cropped)
                body_cropped = re.sub(r'[\,\!\?\+]', ' ', body_cropped)
                found_trigger_words_subject = [word for word in trigger_words if word in subject.lower()]
                found_trigger_words_body = [word for word in trigger_words if word in body_cropped.lower()]

                stock_symbols_subject = re.findall('[A-ZA-Z]{2,}', subject_cleaned)
                verified_symbol = [symbol for symbol in stock_symbols_subject if my_tdameritrade.get_stock_quote(symbol)]

                if not found_trigger_words_subject and not found_trigger_words_body:
                    break
                print(subject)
                found_transaction_dict = {}
                for symbol in verified_symbol:
                    skip_symbol = False
                    cropped_at_symbol_right = body_cropped[body_cropped.find(symbol):]
                    cropped_at_symbol_right_list = cropped_at_symbol_right.split(" ")
                    cropped_at_symbol_left = body_cropped[:body_cropped.find(symbol)]
                    cropped_at_symbol_left_list = reversed(cropped_at_symbol_left.split(" "))
                    for idx, word in enumerate(cropped_at_symbol_right_list):
                        if word == "at":
                            price = cropped_at_symbol_right_list[idx + 1]
                            price_cleaned = re.sub(r'[^0-9|\.|\$]|[^0-9]$', "", price).replace("$", "")
                            if not price_cleaned or not price_cleaned[-1].isdigit():
                                skip_symbol = True
                                break
                            price_float = float(price_cleaned)
                            found_transaction_dict[symbol] = {}
                            found_transaction_dict[symbol]["transaction_price"] = price_float
                            quote = my_tdameritrade.get_stock_quote(symbol)
                            found_transaction_dict[symbol]["tdameritrade"] = {
                                "bidPrice": quote["bidPrice"],
                                "askPrice": quote["askPrice"]
                            }
                            break
                    if skip_symbol:
                        continue
                    transaction_type_found = False
                    for idx, word in enumerate(cropped_at_symbol_left_list):
                        if word in found_trigger_words_subject:
                            if word == "sold":
                                found_transaction_dict[symbol]["transaction_type"] = "Sell"
                            else:
                                found_transaction_dict[symbol]["transaction_type"] = "Buy"
                            transaction_type_found = True
                            break
                    if not transaction_type_found:
                        if found_trigger_words_subject:
                            trigger_word = found_trigger_words_subject[0]
                        else:
                            trigger_word = found_trigger_words_body[0]
                        if trigger_word == "sold":
                            found_transaction_dict[symbol]["transaction_type"] = "Sell"
                        else:
                            found_transaction_dict[symbol]["transaction_type"] = "Buy"
                print(found_transaction_dict)
                json_transaction_data[id]["found_transactions"] = found_transaction_dict
                json_transaction_data[id]["detected_time"] = str(datetime.now())
                # make transaction on tdameritrade
                print(json_transaction_data[id])
                my_tdameritrade.execute_transaction_from_dict(json_transaction_data[id], PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT, BUY_CASH_LIMIT)
                print("-"*40)

        with open("Data/transaction_data.json", 'w') as f:
            f.write(json.dumps(json_transaction_data, indent=4))
        print("Ping: ", ping_count)
        time.sleep(time_interval_seconds)


if __name__ == '__main__':
    main()




