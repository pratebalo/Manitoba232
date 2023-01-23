from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from mimetypes import MimeTypes
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from io import BytesIO
from datetime import datetime
import pandas as pd

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

drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)


def get_file_by_id(file_id, mimeType):
    if mimeType == "application/vnd.google-apps.spreadsheet":
        request = drive_service.files().export_media(fileId=file_id,
                                                     mimeType='application/x-vnd.oasis.opendocument.spreadsheet')
    elif mimeType == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        request = drive_service.files().get_media(fileId=file_id)
    else:
        return None
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    fh.seek(0)
    file = pd.read_excel(fh)
    file.dropna(axis=0, how='all', inplace=True)
    return file


def get_file(file):
    try:
        request = drive_service.files().get_media(fileId=file.id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fd=fh, request=request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

    except:
        request = drive_service.files().export_media(fileId=file.id,
                                                     mimeType=file.mimeType)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fd=fh, request=request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
    fh.seek(0, os.SEEK_END)
    print(fh.tell())
    fh.seek(0)

    fh.name = file['name']
    # with open(os.path.join(f"./../Carpeta/{fh.name}"), "wb") as f:
    #     f.write(fh.read())
    # f.close()
    return fh


def get_parent_id(file_id):
    file = drive_service.files().get(fileId=file_id,
                                     fields='id, name, parents').execute()
    if file.get('parents'):
        return file.get('parents')[0]
    else:
        return None


def create_folder(name, parent_folder):
    file_metadata = {
        'name': name,
        'parents': [parent_folder],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = drive_service.files().create(body=file_metadata,
                                        supportsAllDrives=True,
                                        fields='id').execute()
    return file.get('id')


def get_all_files_description(parent_folder):
    query = f"'{parent_folder}' in parents and trashed= False "
    response = drive_service.files().list(pageSize=1000,
                                          supportsAllDrives=False,
                                          includeItemsFromAllDrives=False,
                                          q=query,
                                          fields="nextPageToken, files(id, name,kind,mimeType)").execute()
    files = response.get('files')

    data = pd.DataFrame(files).sort_values("mimeType", ascending=False)

    data = data.replace({'mimeType': DICT})

    return data


def get_file_description(file_id):
    data = drive_service.files().get(fileId=file_id,
                                     supportsAllDrives=True).execute()
    file = pd.DataFrame([pd.Series(data)])
    file.loc[
        file.mimeType == "application/vnd.google-apps.document", "name"] += ".docx"
    file.loc[
        file.mimeType == "application/vnd.google-apps.spreadsheet", "name"] += ".xlsx"
    file = file.replace({'mimeType': DICT})
    return file.squeeze()


def upload_file(path, parent_id=None):
    mime = MimeTypes()

    file_metadata = {
        'name': os.path.basename(path),
        # 'mimeType' : 'application/vnd.google-apps.spreadsheet'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    media = MediaFileUpload(path, mimetype=mime.guess_type(os.path.basename(path))[0],
                            resumable=True)
    try:
        file = drive_service.files().create(body=file_metadata,
                                            media_body=media,
                                            fields='id').execute()
        print(file.get('id'))
    except HttpError:
        print('corrupted file')
        pass
