import warnings
import pytz
import pandas as pd
import src.utilitys as ut

from decouple import config
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, PollAnswerHandler, ContextTypes, Application

from datetime import datetime, time, timedelta

from dotenv import load_dotenv
from utils import contacts_drive as contacts, menu, database as db
from utils.sheets_drive import generate_sheet_sections
from utils.logger_config import logger
from src import poll, tareas, birthday, lists, treasury, new_member, drive, assistance, ass, pietro, loquendo

warnings.filterwarnings("ignore")

ID_MANITOBA = int(config("ID_MANITOBA"))
ID_SHEET_LISTADOS = config('ID_SHEET_LISTADOS')

TOKEN = config("TOKEN")


async def muted(context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")
    hoy = datetime.today()
    data.ultimo_mensaje = pd.to_datetime(data.ultimo_mensaje)
    for _, persona in data[data.ultimo_mensaje < (hoy - timedelta(23))].iterrows():
        await context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=f"""Te echamos de menos <a href="tg://user?id={persona.id}">{persona.apodo}</a>""")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                await lists.edit_list_manual(update, context)

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
        #         file = await context.bot.get_file(doc.file_id)
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
            await new_member.new_member(update, context)
            logger.info(f"{chat} -> {message.new_chat_members[0]} ha entrado al grupo ")
        elif message.left_chat_member:
            await new_member.left_member(update, context)
            logger.info(f"{chat} -> {message.left_chat_member} ha salido del grupo ")
        elif message.pinned_message:
            logger.info(f"{chat} -> {user.apodo} ha anclado un mensaje")
        elif message.pinned_message:
            logger.info(f"{chat} -> {user.apodo} ha anclado un mensaje")
        else:
            logger.info(f"{chat} -> message desconocido:  {message}")
        db.update_fields_table(table="data", idx=user.id,
                               ultimo_mensaje=user.ultimo_mensaje, total_mensajes=user.total_mensajes,
                               ronda_mensajes=user.ronda_mensajes, sticker=user.sticker, gif=user.gif)

    elif update.edited_message:
        user.total_mensajes -= 1
        user.ronda_mensajes -= 1
        logger.warning(f"{chat} -> {user.apodo} ha editado un mensaje. Con un total de {user.total_mensajes} mensajes y {user.ronda_mensajes} esta ronda")
    else:
        logger.info(f"{chat} -> update desconocido: {update}")


async def listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    chat = update.effective_chat
    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando listados")
    await update.message.delete()
    message = await chat.send_message(text=f'Generando los listados')
    message2 = await chat.send_sticker(sticker='CAACAgIAAxkBAAIJf2Perl8wSGXGavHr4598UvY10lLVAAIjAAMoD2oUJ1El54wgpAYuBA')
    generate_sheet_sections()
    await message.delete()
    await message2.delete()
    await update.effective_chat.send_message(text=f'https://docs.google.com/spreadsheets/d/{ID_SHEET_LISTADOS}/')
    return ConversationHandler.END


if __name__ == "__main__":
    load_dotenv()
    app = Application.builder().token(TOKEN).build()

    job = app.job_queue

    pd.options.display.width = 0

    app.add_handler(lists.get_conv_handler())
    app.add_handler(treasury.get_conv_handler())
    app.add_handler(loquendo.get_conv_handler())
    app.add_handler(pietro.get_conv_handler())
    app.add_handler(birthday.get_conv_handler())
    app.add_handler(ass.get_conv_handler())
    app.add_handler(tareas.get_conv_handler())
    app.add_handler(menu.get_conv_handler_menu())
    app.add_handler(assistance.get_conv_handler())
    app.add_handler(CommandHandler('cumples', birthday.get_birthday))
    app.add_handler(CommandHandler('allcumples', birthday.get_all_birthday))
    app.add_handler(CommandHandler('listados', listings))

    app.add_handler(PollAnswerHandler(poll.receive_poll_answer))
    app.add_handler(MessageHandler(filters.POLL, poll.receive_poll))
    app.add_handler(CommandHandler('bot', poll.bot_activated))
    app.add_handler(poll.get_conv_handler_polls())
    app.add_handler(drive.conv_handler_drive)
    app.add_handler(new_member.get_conv_handler_start())
    app.add_handler(MessageHandler(filters.ALL, echo))

    job.run_daily(birthday.birthday, time(7, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
    job.run_daily(contacts.update_contacts, time(4, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
    # job.run_daily(muted, time(17, 54, 00, 000000))
    job.run_daily(tareas.recordar_tareas, time(9, 00, 00, tzinfo=pytz.timezone('Europe/Madrid')))
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print("Otro error:", e)
