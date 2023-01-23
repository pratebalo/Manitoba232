from __future__ import print_function
import pandas as pd
import os.path
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from utils import gillweb
from telegram.ext import CallbackContext

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/contacts',
          'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'keys.json'

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
creds = None
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("contacts_drive")
if os.path.exists(ROOT_DIR + '/token.json'):
    creds = Credentials.from_authorized_user_file(ROOT_DIR + '/token.json',
                                                  SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(ROOT_DIR + '/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(ROOT_DIR + '/token.json', 'w') as token:
        token.write(creds.to_json())

service = build('people', 'v1', credentials=creds, cache_discovery=False)


def update_contacts(context: CallbackContext):
    resultset = service.people().connections().list(
        resourceName='people/me',
        pageSize=2000,
        personFields='names,emailAddresses,phoneNumbers,biographies,memberships,metadata').execute()

    data_gmail = pd.DataFrame()
    for contact in resultset['connections']:
        data = [contact['names'][0].get('givenName', ''), contact['names'][0].get('familyName', '')]
        data.extend([contact[col][0]['value'] if col in contact else '' for col in
                     ['biographies', 'emailAddresses', 'phoneNumbers']])
        data += [contact[col] for col in ['resourceName', 'etag', 'metadata']]
        data.append(tuple(sorted([a['contactGroupMembership']['contactGroupId'] for a in contact['memberships']])))
        data_gmail = data_gmail.append(pd.Series(data), ignore_index=True)
    data_gmail.columns = ['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers', 'resourceName',
                          'etag', 'metadata', 'memberships']
    data_gmail = data_gmail.sort_values(['givenName', 'familyName']).reset_index(drop=True)
    data_gillweb = gillweb.get_data_gillweb()
    data_gmail2 = data_gmail.merge(data_gillweb.drop_duplicates(),
                                   on=['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers',
                                       'memberships'],
                                   how='left',
                                   indicator=True)
    data_gmail2 = data_gmail2[data_gmail2['_merge'] == 'left_only']
    data_gillweb2 = data_gmail.merge(data_gillweb.drop_duplicates(),
                                     on=['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers',
                                         'memberships'],
                                     how='right',
                                     indicator=True)
    data_gillweb2 = data_gillweb2[data_gillweb2['_merge'] == 'right_only']
    for _, row in data_gillweb2.iterrows():
        body = {
            'names': [
                {
                    'givenName': row['givenName'],
                    'familyName': row['familyName']
                }
            ],
            'phoneNumbers': [
                {
                    'value': row['phoneNumbers']
                }
            ],
            'emailAddresses': [
                {
                    'value': row['emailAddresses']
                }
            ],
            'biographies': [
                {
                    'value': row['biographies']
                }
            ]}
        memberships = []
        for j in row['memberships']:
            memberships.append({'contactGroupMembership': {'contactGroupResourceName': 'contactGroups/' + j}})
        body['memberships'] = memberships
        logger.warning(f"Se crea el contacto -> {row}")
        service.people().createContact(body=body).execute()

    for _, row in data_gmail2.iterrows():
        logger.warning(f"Se elimina el contacto -> {row}")

        service.people().deleteContact(resourceName=row['resourceName']).execute()
