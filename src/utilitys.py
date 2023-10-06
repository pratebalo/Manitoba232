from telegram.ext import ContextTypes

from decouple import config
from utils import database as db
import re

ID_ADMIN = config("ID_ADMIN")


def get_person(person_id: int):
    data = db.select('data')
    person = data[data.id == person_id].squeeze()

    return person


def set_actual_user(person_id: int, context):
    person = get_person(person_id)
    context.user_data["user"] = person


async def check_logs(context: ContextTypes.DEFAULT_TYPE):
    with open(file="errors.log") as f:
        logs = f.read()

    regex = r'\d{4}-\d{2}-\d{2} '
    result = re.split(regex, logs)
    result = [element for element in result if element]
    if "last_log" in context.bot_data.keys():
        diff = result[result.index(context.bot_data["last_log"]) + 1:]
        for text in diff:
            await context.bot.sendMessage(ID_ADMIN, text=text)
        context.bot_data["last_log"] = result[-1]
    else:
        context.bot_data["last_log"] = result[-1]
