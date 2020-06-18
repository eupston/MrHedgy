from O365 import Account
import os
from dotenv import load_dotenv,find_dotenv
import json
from datetime import datetime

load_dotenv(find_dotenv())


class Outlook:

    def __init__(self):
        self.credentials = (os.getenv('AZURE_APP_CLIENT_ID'),os.getenv('AZURE_APP_CLIENT_SECRET'))
        self.account = self.account = Account(self.credentials)

    def authenticate_with_tenant_id(self):
        self.account = Account(self.credentials, auth_flow_type='credentials', tenant_id=os.getenv('AZURE_TENANT_ID'))
        if self.account.authenticate():
            print('Authenticated!')

    def authenticate_through_popup(self):
        if self.account.authenticate(scopes=['basic', 'message_all']):
            print('Authenticated!')

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
            messages[id] = {
               "date_received": str(received),
               "subject": subject,
               "body_preview": body_preview
            }
        return messages



if __name__ == '__main__':
    my_outlook = Outlook()
    messages = my_outlook.get_email_body_messages("eupston130@hotmail.com", "Kyle Dennis", f"subject:TWK AND received>=2020-06-16")
    print(json.dumps(messages, indent=4))
    print(datetime.now())