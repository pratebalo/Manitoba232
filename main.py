import warnings
from utils import logger_config
import pytz
import pandas as pd
import src.utilitys as ut
from decouple import config
from telegram import Update, Bot
from telegram.ext import CommandHandler, PollAnswerHandler, ConversationHandler, CallbackContext, MessageHandler, Filters, Updater

from datetime import datetime, time, timedelta
from utils.sheets_drive import generate_sheet_sections

from dotenv import load_dotenv
from utils import database as db
from utils import contacts_drive as contacts, menu
from src import poll, tareas, birthday, lists, treasury, new_member, drive, assistance, ass, pietro, loquendo

warnings.filterwarnings("ignore")

logger = logger_config.logger

ID_MANITOBA = int(config("ID_MANITOBA"))
ID_SHEET_LISTADOS = config('ID_SHEET_LISTADOS')

TOKEN = config("TOKEN")


def muted(context: CallbackContext):
    data = db.select("data")
    hoy = datetime.today()
    data.ultimo_mensaje = pd.to_datetime(data.ultimo_mensaje)
    for _, persona in data[data.ultimo_mensaje < (hoy - timedelta(23))].iterrows():
        context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=f"""Te echamos de menos <a href="tg://user?id={persona.id}">{persona.apodo}</a>""")


def echo(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)
    user = context.user_data['user']
    user.total_mensajes += 1
    user.ronda_mensajes += 1
    user.ultimo_mensaje = datetime.today().strftime('%d/%m/%Y %H:%M:S')
    message = update.message
    chat = update.effective_chat.type
    if message:
        if message.text:
            if "la lista:\n" in message.text:
                lists.edit_list_manual(update, context)

        elif message.sticker:
            user.sticker += 1
            logger.info(f"{chat} -> {user.apodo} ha enviado un sticker. Con un total de {user.total_mensajes} mensajes y {user.ronda_mensajes} esta ronda")
        elif message.photo:
            logger.info(f"{chat} -> {user.apodo} ha enviado una foto. Con un total de {user.total_mensajes} mensajes y {user.ronda_mensajes} esta ronda")
        elif message.animation:
            user.gif += 1
            logger.info(f"{chat} -> {user.apodo} ha enviado un gif. Con un total de {user.total_mensajes} mensajes y {user.ronda_mensajes} esta ronda")
        elif message.document:
            _ = message.document
        #     if "acta" in doc.file_name.lower() and doc.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        #         file = context.bot.get_file(doc.file_id)
        #         file.download(doc.file_name)
        #         path = os.path.dirname(os.path.realpath(__file__))
        #         docx2pdf.convert(doc.file_name)
        #         file_name = doc.file_name.replace(".docx", ".pdf")
        #
        #         client_drive.upload_file(file_name, parent_id='1V34ehU4iaHgadWCRSl9hlvZUIn62qWSM')
        #         client_drive.upload_file(doc.file_name, parent_id='1V34ehU4iaHgadWCRSl9hlvZUIn62qWSM')
        #     logger.info(
        #         f"{chat} -> {fila.apodo} ha enviado el documento {message.document.file_name} tipo "
        #         f"{message.document.mime_type}. Con un total de {fila.total_mensajes} mensajes")
        elif message.new_chat_members:
            new_member.new_member(update, context)
            logger.info(f"{chat} -> {message.new_chat_members[0]} ha entrado al grupo ")
        elif message.left_chat_member:
            new_member.left_member(update, context)
            logger.info(f"{chat} -> {message.left_chat_member} ha salido del grupo ")
        elif message.pinned_message:
            logger.info(f"{chat} -> {user.apodo} ha anclado un mensaje")
        elif message.voice_chat_participants_invited:
            logger.info(f"{chat} -> {user.apodo} ha metido a la llamada a {message.voice_chat_participants_invited.users.username}")
        elif message.pinned_message:
            logger.info(f"{chat} -> {user.apodo} ha anclado un mensaje")
        else:
            logger.info(f"{chat} -> message desconocido:  {message}")
        db.update_data_messages(user)
    elif update.edited_message:
        user.total_mensajes -= 1
        user.ronda_mensajes -= 1
        logger.warning(f"{chat} -> {user.apodo} ha editado un mensaje. Con un total de {user.total_mensajes} mensajes y {user.ronda_mensajes} esta ronda")
    else:
        logger.info(f"{chat} -> update desconocido: {update}")


def listings(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha entrado en el comando listados")
    generate_sheet_sections()
    context.bot.sendMessage(update.effective_chat.id, text=f'https://docs.google.com/spreadsheets/d/{ID_SHEET_LISTADOS}/')
    return ConversationHandler.END


if __name__ == "__main__":
    load_dotenv()
    try:
        my_bot = Bot(token=TOKEN)
        updater = Updater(my_bot.token, use_context=True)
        dp = updater.dispatcher

        job = updater.job_queue

        pd.options.display.width = 0

        dp.add_handler(lists.get_conv_handler())
        dp.add_handler(treasury.get_conv_handler())
        dp.add_handler(loquendo.get_conv_handler())
        dp.add_handler(pietro.get_conv_handler())
        dp.add_handler(birthday.get_conv_handler())
        dp.add_handler(ass.get_conv_handler())
        dp.add_handler(tareas.get_conv_handler())
        dp.add_handler(menu.get_conv_handler_menu())
        dp.add_handler(assistance.get_conv_handler())
        dp.add_handler(CommandHandler('cumples', birthday.get_birthday))
        dp.add_handler(CommandHandler('allcumples', birthday.get_all_birthday))
        dp.add_handler(CommandHandler('listados', listings))

        dp.add_handler(PollAnswerHandler(poll.receive_poll_answer))
        dp.add_handler(MessageHandler(Filters.poll, poll.receive_poll))
        dp.add_handler(CommandHandler('bot', poll.bot_activated))
        dp.add_handler(poll.get_conv_handler_polls())
        dp.add_handler(drive.conv_handler_drive)
        dp.add_handler(new_member.get_conv_handler_start())
        dp.add_handler(MessageHandler(Filters.all, echo))
        #
        job.run_daily(birthday.birthday, time(7, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
        job.run_daily(contacts.update_contacts, time(4, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
        # job.run_daily(muted, time(17, 54, 00, 000000))
        job.run_daily(tareas.recordar_tareas, time(9, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
        logger.info(f"Iniciando el bot")
        logger.error(f"Fallo al eliminar el mensaje")
        logger.warning(f"Fallo al eliminar el mensaje")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Error {e}")
