from telegram.ext import ContextTypes

from decouple import config
from utils import database as db
import re

ID_ADMIN = config("ID_ADMIN")
ID_LOGS = config("ID_LOGS")
ID_SHEET_CASTORES = config("ID_SHEET_CASTORES")
ID_SHEET_MANADA = config("ID_SHEET_MANADA")
ID_SHEET_TROPA = config("ID_SHEET_TROPA")
ID_SHEET_ESCULTAS = config("ID_SHEET_ESCULTAS")
ID_SHEET_ROVER = config("ID_SHEET_ROVER")
ID_SHEET_KRAAL = config("ID_SHEET_KRAAL")


def get_person(person_id: int):
    data = db.select('data')
    person = data[data.id == person_id].squeeze()

    return person


def set_actual_user(person_id: int, context):
    person = get_person(person_id)
    context.user_data["user"] = person


async def check_log_errors(context: ContextTypes.DEFAULT_TYPE):
    with open(file="errors.log") as f:
        logs = f.read()

    regex = r'\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs)
    result = [element for element in result if element]
    if "last_error_log" in context.bot_data.keys():
        if context.bot_data["last_error_log"] in result:
            diff = result[result.index(context.bot_data["last_error_log"]) + 1:]
            for text in diff:
                await context.bot.sendMessage(ID_LOGS, text=f"MANITOBA - {text}")

    context.bot_data["last_error_log"] = result[-1]


async def check_last_logs(context: ContextTypes.DEFAULT_TYPE):
    with open(file="info_warning.log") as f:
        logs = f.read()

    regex = r'\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs)
    result = [element for element in result if element]
    if "last_log" in context.bot_data.keys():
        if context.bot_data["last_log"] in result:
            diff = result[result.index(context.bot_data["last_log"]) + 1:]
            for text in diff:
                await context.bot.sendMessage(ID_LOGS, text=f"MANITOBA - {text}")

    context.bot_data["last_log"] = result[-1]

# folders = [ID_SHEET_CASTORES, ID_SHEET_MANADA, ID_SHEET_TROPA, ID_SHEET_ESCULTAS, ID_SHEET_ROVER]
# for i in range(1, 6):
#     data = utils.gillweb.download_data_gillweb(section=i)
#     sheet = folders[i - 1]
#     data["full_name"] = data.nombre_dni + " " + data.surname
#     for person in data.itertuples():
#         print(person.full_name)
#
#     print()