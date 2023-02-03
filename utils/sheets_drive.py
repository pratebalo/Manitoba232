from __future__ import print_function
import os.path
import random
import utils.gillweb as gillweb
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from datetime import datetime

DICT = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.form': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.google-apps.jam': ''}
FOLDER_BASE = '0AHBcqK_64EhOUk9PVA'

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/contacts',
          'https://www.googleapis.com/auth/spreadsheets']

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
creds = None
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

sheets_service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
spreadsheets = sheets_service.spreadsheets()
drive = build('drive', 'v3', credentials=creds, cache_discovery=False)


def create_sheet(sheet_name, folder_id):
    try:
        file_metadata = {
            'name': sheet_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        response = drive.files().create(body=file_metadata).execute()

        sheet = get_sheet(response['id'])

        return sheet

    except Exception as e:
        print(e)


def append_data(sheet, worksheet_name, cell_range_insert, values):
    try:
        value_range_body = {
            'majorDimension': 'ROWS',
            'values': values
        }

        response = spreadsheets.values().append(
            spreadsheetId=sheet['spreadsheetId'],
            valueInputOption='USER_ENTERED',
            range=f'{worksheet_name}!{cell_range_insert}',
            body=value_range_body
        ).execute()

        return response

    except Exception as e:
        print(e)


def add_sheets(gsheet_id, sheet_name):
    try:
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 5000,
                            'columnCount': 100
                        },
                        "tabColor": {
                            "red": random.uniform(0, 1),
                            "green": random.uniform(0, 1),
                            "blue": random.uniform(0, 1)
                        }
                    }
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        return response

    except Exception as e:
        print(e)


def delete_sheet(gsheet_id, sheet_id):
    try:
        request_body = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        return response

    except Exception as e:
        print(e)


def clear_sheet(gsheet_id, sheet_name):
    try:
        response = spreadsheets.values().clear(
            spreadsheetId=gsheet_id,
            body={},
            range=f'{sheet_name}!A1:Z'
        ).execute()

        return response

    except Exception as e:
        print(e)


def get_sheet(gsheet_id):
    sheet = sheets_service.spreadsheets().get(spreadsheetId=gsheet_id).execute()

    return sheet


def rename_file(file_id, new_name):
    try:
        body = {'name': new_name}
        return drive.files().update(fileId=file_id, body=body).execute()

    except Exception as e:
        print(e)


def generate_sheet_sections():
    list_sections = gillweb.get_listed_sections()
    sheet_id = '1uPKEj1s7Y4TPcyTImGrkmjl4POGM6Mryk3Ebn8L8lxM'
    sheet = get_sheet(sheet_id)
    new_name = f'Listados-{datetime.now().strftime("%d/%m/%y %H:%M")}'
    rename_file(sheet_id, new_name)
    for section, df in list_sections:
        clear_sheet(sheet_id, section)
        data = [df.columns.values.tolist()]
        data.extend(df.values.tolist())
        append_data(sheet, section, 'B2', data)
        x = df.groupby(['Sección']).size().reset_index(name='Total')
        x.loc[len(x.index)] = ['Suma', sum(x.Total)]
        data = [x.columns.values.tolist()]
        data.extend(x.values.tolist())
        append_data(sheet, section, 'H3', data)
