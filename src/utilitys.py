from telegram.ext import ContextTypes

from decouple import config
from utils import database as db, gillweb
import re

import utils.client_drive as drive

ID_ADMIN = config("ID_ADMIN")
ID_LOGS = config("ID_LOGS")
ID_FOLDER_CASTORES = config("ID_FOLDER_CASTORES")
ID_FOLDER_MANADA = config("ID_FOLDER_MANADA")
ID_FOLDER_TROPA = config("ID_FOLDER_TROPA")
ID_FOLDER_ESCULTAS = config("ID_FOLDER_ESCULTAS")
ID_FOLDER_ROVER = config("ID_FOLDER_ROVER")
ID_FOLDER_KRAAL = config("ID_FOLDER_KRAAL")


def get_person(person_id: int):
    data = db.select('data')
    person = data[data.id == person_id].squeeze()

    return person


def set_actual_user(person_id: int, context):
    person = get_person(person_id)
    context.user_data["user"] = person


async def check_log_errors(context: ContextTypes.DEFAULT_TYPE):
    logs = get_last_lines("errors.log")

    regex = r'\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs)
    result = [element.strip() for element in result if element]
    if "last_error_log" in context.bot_data.keys():
        if context.bot_data["last_error_log"] in result:
            diff = result[result.index(context.bot_data["last_error_log"]) + 1:]
            for text in diff:
                max_length = 4096
                for i in range(0, len(text), max_length):
                    fragment = text[i:i + max_length]
                    await context.bot.sendMessage(ID_LOGS, text=f"MANITOBA - {fragment}")

    context.bot_data["last_error_log"] = result[-1]


async def check_last_logs(context: ContextTypes.DEFAULT_TYPE):
    logs = get_last_lines("info_warning.log")

    regex = r'\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs)
    result = [element.strip() for element in result if element]
    if "last_log" in context.bot_data.keys():
        if context.bot_data["last_log"] in result:
            diff = result[result.index(context.bot_data["last_log"]) + 1:]
            for text in diff:
                max_length = 4096
                for i in range(0, len(text), max_length):
                    fragment = text[i:i + max_length]
                    await context.bot.sendMessage(ID_LOGS, text=f"MANITOBA - {fragment}")

    context.bot_data["last_log"] = result[-1]


def get_last_lines(file, num_lines=200):
    buffer_size = 4096  # Puedes ajustar el tamaño del búfer según tus necesidades

    with open(file, 'rb') as f:
        f.seek(0, 2)
        pos = f.tell()
        total_lines = 0
        lines = []

        while pos > 0 and 10 < num_lines:
            to_read = min(pos, buffer_size)
            pos -= to_read
            f.seek(pos)
            chunk = f.read(to_read)

            # Decodificar el bloque de bytes y dividir por líneas
            lines_in_chunk = chunk.decode('utf-8', errors='replace').splitlines()

            # Contar las líneas en el bloque y actualizar el contador total
            total_lines += len(lines_in_chunk) - 1

            # Insertar las líneas en la lista (excepto la última, que puede estar incompleta)
            lines[:0] = lines_in_chunk

        # Devolver las líneas concatenadas
        return '\n'.join(lines[-num_lines:])

# folders = [ID_FOLDER_CASTORES, ID_FOLDER_MANADA, ID_FOLDER_TROPA, ID_FOLDER_ESCULTAS, ID_FOLDER_ROVER, ID_FOLDER_KRAAL]
# for i in range(1, 6):
#     data = gillweb.download_data_gillweb(section=i)
#     parent_folder = folders[i - 1]
#     data["folder_name"] = data.id.astype(str) + "-" + data.name + " " + data.surname
#     print(i)
#     for person in data.itertuples():
#         folder = drive.create_folder(person.folder_name, parent_folder)
