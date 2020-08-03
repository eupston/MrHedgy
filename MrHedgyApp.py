import sys
import re
from Components.APIs.Outlook import Outlook
from Components.APIs.TDAmeritrade import TDAmeritrade
from Components.Threading import Worker
from dotenv import load_dotenv, find_dotenv
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import QThread
import qdarkstyle


load_dotenv(find_dotenv())

class MrHedgyApp(QWidget):

    def __init__(self):
        """
        An Application for Trading Stock via Email
        """
        super().__init__()
        self.setWindowTitle('Mr. Hedgy')
        self.setGeometry(400, 200, 600, 400)
        self.grid = QGridLayout()

        self.title_label = QLabel("Mr. Hedgy")
        self.title_font = QFont("Helvetica", 24, QFont.Bold)
        self.title_label.setFont(self.title_font)

        self.buy_cash_label = QLabel("Buy Cash Limit")
        self.buy_cash_box = QDoubleSpinBox()
        self.buy_cash_box.setRange(100, 1000)
        self.buy_cash_box.setSingleStep(100)
        self.buy_cash_box.setValue(100)
        self.buy_cash_box.setDecimals(2)

        self.percent_trans_limit_label = QLabel("Percent Range Execute Transaction Limit")
        self.percent_trans_limit_box = QDoubleSpinBox()
        self.percent_trans_limit_box.setRange(1, 10)
        self.percent_trans_limit_box.setSingleStep(1)
        self.percent_trans_limit_box.setValue(5)
        self.percent_trans_limit_box.setDecimals(0)

        self.email_interval_label = QLabel("Email Time Interval Seconds")
        self.email_interval_box = QDoubleSpinBox()
        self.email_interval_box.setRange(1, 10)
        self.email_interval_box.setSingleStep(1)
        self.email_interval_box.setValue(10)
        self.email_interval_box.setDecimals(0)

        self.stock_transactions_label = QLabel("Stock Transactions")
        self.stock_transactions_font = QFont("Helvetica", 16, QFont.Bold)
        self.stock_transactions_label.setFont(self.stock_transactions_font)
        self.stock_report_list = QListWidget()

        self.scanning_button = QPushButton("Start Scanning")
        self.scanning_button.clicked.connect(self.start_stop_scanning_emails)
        self.scanning_button.setCheckable(True)

        self.grid.addWidget(self.title_label, 0, 0,1,0)
        self.grid.addWidget(self.buy_cash_label, 1, 0)
        self.grid.addWidget(self.buy_cash_box, 1, 1)
        self.grid.addWidget(self.percent_trans_limit_label, 2, 0)
        self.grid.addWidget(self.percent_trans_limit_box, 2, 1)
        self.grid.addWidget(self.email_interval_label, 3, 0)
        self.grid.addWidget(self.email_interval_box, 3, 1)
        self.grid.addWidget(self.stock_transactions_label, 4, 0)
        self.grid.addWidget(self.stock_report_list, 5, 0, 1, 0)
        self.grid.addWidget(self.scanning_button, 6, 0, 1, 0)
        self.setLayout(self.grid)
        
        self.scan_emails = False

    def start_stop_scanning_emails(self):
        """
        Function that toggles between Starting Stopping email scanning
        :return:
        """
        if self.scanning_button.isChecked():
            self.scanning_button.setText("Stop Scanning")
            self.start_scanning_emails_thread()
        else:
            self.scanning_button.setText("Start Scanning")
            self.stop_scanning_emails_thread()

    def start_scanning_emails_thread(self):
        """
        Start the scanning email thread
        :return:
        """
        self.scan_emails = True
        self.thread = QThread()
        self.worker = Worker(True, self.start_scanning_emails)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start_working)
        self.thread.start()

    def stop_scanning_emails_thread(self):
        """
        Stops the scanning email thread
        :return:
        """
        self.scan_emails = False
        self.worker.stop_working()
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.thread.wait)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

    def start_scanning_emails(self):
        """
        Starts Scanning email for any stock emails
        and makes trades if any found
        :return:
        """
        self.my_tdameritrade = TDAmeritrade()
        self.my_outlook = Outlook()
        time_interval_seconds = self.email_interval_box.value()
        BUY_CASH_LIMIT = self.buy_cash_box.value()
        PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT = self.percent_trans_limit_box.value() / 100
        # current_utc_datetime = "2020-06-22"
        current_utc_datetime = self.my_outlook.get_current_UTC_datetime()
        ping_count = 0
        trigger_words = ["bought", "sold", "added"]
        while self.scan_emails:
            with open("Data/transaction_data.json", 'r') as f:
                json_transaction_data = json.load(f)

                messages = self.my_outlook.get_email_body_messages("eupston130@hotmail.com", "Kyle Dennis",
                                                              f"subject:TWK AND received>={current_utc_datetime}")
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
                    verified_symbol = [symbol for symbol in stock_symbols_subject if self.my_tdameritrade.get_stock_quote(symbol)]

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
                                quote = self.my_tdameritrade.get_stock_quote(symbol)
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
                    self.my_tdameritrade.execute_transaction_from_dict(json_transaction_data[id], PERCENT_RANGE_EXECUTE_TRANSACTION_LIMIT, BUY_CASH_LIMIT)
                    for stock in json_transaction_data[id]["found_transactions"].keys():
                        stock_trans_info = json_transaction_data[id]["found_transactions"][stock]
                        success_trans = json_transaction_data[id]["found_transactions"][stock]["success_submitted_transaction"]
                        bidPrice = json_transaction_data[id]["found_transactions"][stock]["tdameritrade"]['bidPrice']
                        askPrice = json_transaction_data[id]["found_transactions"][stock]["tdameritrade"]['askPrice']

                        if stock_trans_info["transaction_type"] == "Sell" and success_trans:
                            amt_stock_sold = json_transaction_data[id]["found_transactions"][stock]['amount_stock_sold']
                            transaction_info = f"Sold {amt_stock_sold} of {symbol} for ${bidPrice} per Share"
                            transaction_item = QListWidgetItem(transaction_info)
                            self.stock_report_list.addItem(transaction_item)
                        if stock_trans_info["transaction_type"] == "Buy" and success_trans:
                            amt_stock_bought = json_transaction_data[id]["found_transactions"][stock]['amount_stock_bought']
                            transaction_info = f"Bought {amt_stock_bought} of {symbol} for ${askPrice} per Share"
                            transaction_item = QListWidgetItem(transaction_info)
                            self.stock_report_list.addItem(transaction_item)
                    print("-"*40)
            with open("Data/transaction_data.json", 'w') as f:
                f.write(json.dumps(json_transaction_data, indent=4))
            print("Ping:", ping_count, " Time: ", datetime.now())
            time.sleep(time_interval_seconds)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    # app.setStyleSheet(dark_stylesheet)
    mr_hedgy_app = MrHedgyApp()
    mr_hedgy_app.show()
    sys.exit(app.exec_())



