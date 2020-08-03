from O365 import Account, MSGraphProtocol
import os
from dotenv import load_dotenv,find_dotenv
import json
from datetime import datetime
from bs4 import BeautifulSoup
import pytz

load_dotenv(find_dotenv())


class Outlook:

    def __init__(self, timezone=""):
        """
        A class for interfacing with the Outlook API
        :param timezone: the timezone displayed on received calls from the Outlook API
         list of timezone are here:
         https://docs.microsoft.com/en-us/graph/api/resources/datetimetimezone?view=graph-rest-1.0
         Defaults to current timezone
        """
        self.credentials = (os.getenv('AZURE_APP_CLIENT_ID'), os.getenv('AZURE_APP_CLIENT_SECRET'))
        protocol = MSGraphProtocol(timezone=timezone)
        self.account = self.account = Account(self.credentials, protocol=protocol)

    def authenticate_with_tenant_id(self):
        self.account = Account(self.credentials, auth_flow_type='credentials', tenant_id=os.getenv('AZURE_TENANT_ID'))
        if self.account.authenticate():
            print('Authenticated!')

    def authenticate_through_popup(self):
        if self.account.authenticate(scopes=['basic', 'message_all']):
            print('Authenticated!')

    def get_current_UTC_datetime(self):
        """
        gets the current UTC datetime.
        All requests to Outlook API are made in the UTC timezone
        :return: the utc datetime in year:month:day hour:minute:second
        """
        utc_datetime = datetime.utcnow()
        utc_converted = utc_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        return utc_converted

    def convert_datetime_to_UTC_datetime(self, year, month, day, hour, min, sec, timezone):
        """
        convert a given datetime to UTC datetime
        :param year:
        :param month:
        :param day:
        :param hour:
        :param min:
        :param sec:
        :param timezone: the timezone string 'US/Eastern'
        :return: the converted datetime string
        """
        utc = pytz.utc
        py_timezone = pytz.timezone(timezone)
        given_datetime = py_timezone.localize(datetime(year,month,day,hour,min,sec))
        utc_time = given_datetime.astimezone(utc)
        return utc_time

    def get_timezones(self):
        """
        Gets all available timezones for the pytz module
        :return: a list of all timezones
        """
        return pytz.all_timezones

    def get_email_body_messages(self, email_address, folder_name, query=""):
        """
        Gets all emails from the given email address and folder name
        more info on query parameters: https://docs.microsoft.com/en-us/graph/query-parameters
        :param email_address:
        :param folder_name:
        :param query:
        :return:
        """
        mailbox = self.account.mailbox(resource=email_address)
        if query:
            myquery = mailbox.new_query().search(query)
        else:
            myquery=""
        inbox = mailbox.get_folder(folder_name=folder_name)
        messages = {}
        for message in inbox.get_messages(query=myquery):
            id = message.object_id
            received = message.received
            subject = message.subject
            body_preview = message.body_preview
            body = message.body
            body_parser = ""
            soup = BeautifulSoup(body)
            paragraphs = soup.find_all('p')
            for paragraph in paragraphs:
                body_parser += paragraph.text

            messages[id] = {
               "date_received": str(received),
               "subject": subject,
               "body_preview": body_preview,
               "body": body_parser
            }
        return messages

if __name__ == '__main__':
    my_outlook = Outlook()
    current_datetime = datetime.now()
    print(current_datetime)
    utc_current_time = my_outlook.get_current_UTC_datetime()
    result = my_outlook.convert_datetime_to_UTC_datetime(2002, 10, 27, 6, 0, 0, 'Pacific/Auckland')
    messages = my_outlook.get_email_body_messages("eupston130@hotmail.com", "Kyle Dennis", f"subject:TWK AND received>=2020-06-23T11:49:02")
    print(json.dumps(messages, indent=4))

