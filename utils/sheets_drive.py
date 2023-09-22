import os.path
import random
import utils.gillweb as gillweb
from decouple import config
from utils import logger_config 
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from datetime import datetime
import utils.database as db

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

logger = logger_config.logger
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

ID_SHEET_CASTORES = config('ID_SHEET_CASTORES')
ID_SHEET_MANADA = config('ID_SHEET_MANADA')
ID_SHEET_TROPA = config('ID_SHEET_TROPA')
ID_SHEET_ESCULTAS = config('ID_SHEET_ESCULTAS')
ID_SHEET_ROVER = config('ID_SHEET_ROVER')

sheet_sections = {1: ID_SHEET_CASTORES, 2: ID_SHEET_MANADA, 3: ID_SHEET_TROPA, 4: ID_SHEET_ESCULTAS, 5: ID_SHEET_ROVER}

ID_SHEET_LISTADOS = config('ID_SHEET_LISTADOS')


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
        logger.error(e)


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
        logger.error(e)


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
        logger.error(e)


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
        logger.error(e)


def clear_sheet(gsheet_id, sheet_name, ranged='A1:Z'):
    try:
        response = spreadsheets.values().clear(
            spreadsheetId=gsheet_id,
            body={},
            range=f'{sheet_name}!{ranged}'
        ).execute()

        return response

    except Exception as e:
        logger.error(e)


def get_sheet(gsheet_id):
    sheet = sheets_service.spreadsheets().get(spreadsheetId=gsheet_id).execute()

    return sheet


def rename_file(file_id, new_name):
    try:
        body = {'name': new_name}
        return drive.files().update(fileId=file_id, body=body).execute()

    except Exception as e:
        logger.error(e)


def generate_sheet_sections():
    list_sections = gillweb.get_listed_sections()
    sheet_id = ID_SHEET_LISTADOS
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


def generate_sheet_assistance(section):
    sheet_id = sheet_sections[section]
    assistance = db.select_where("assistance", ["section"], [section]).sort_values('date')
    sheet = get_sheet(sheet_id)
    data_gillweb = gillweb.download_data_gillweb(section)[['id', 'name', 'surname']]
    result_df = data_gillweb.copy()
    trim = ['2024-01-10', '2024-04-07', '2024-09-16']
    pos = 0
    total = 0

    for index, row in assistance.iterrows():
        if row["date"] > datetime.strptime(trim[pos], "%Y-%m-%d").date():
            if total != 0:
                result_df[f"Trimestre {pos + 1}"] = result_df[result_df.columns[-total:]].sum(axis=1)
            pos += 1
            total = 0
        attendees = row['people_id']
        result_df[row['meeting_name']] = result_df['id'].apply(lambda x: 1 if x in attendees else 0)
        total += 1

    if "Trimestre" not in result_df.columns[-1] and len(result_df.columns) > 3:
        result_df[f"Trimestre {pos + 1}"] = result_df[result_df.columns[-total:]].sum(axis=1)
        pos += 1

    quarters_col = [index for index, column_name in enumerate(result_df.columns) if 'Trimestre' in column_name]

    result_df[f"Total"] = result_df.iloc[:, quarters_col].sum(axis=1)
    result_df[assistance.meeting_name] = result_df[assistance.meeting_name].replace({1: 'SI', 0: 'NO'})
    result_df.sort_values('Total', inplace=True, ascending=False)
    result_df.drop("id", inplace=True, axis=1)
    result_df = result_df.rename(columns={"name": "Nombre", "surname": "Apellidos"})
    clear_sheet(sheet_id, 'Asistencia')
    data = [result_df.columns.tolist()]
    data.extend(result_df.values.tolist())
    append_data(sheet, 'Asistencia', 'B2', data)
