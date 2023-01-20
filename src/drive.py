from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    Filters
)
import pandas as pd
import logging
from utils import database as db
import random
from decouple import config
from utils import client_drive
from datetime import date
from telegram_bot_calendar import DetailedTelegramCalendar, DAY

# Stages
DRIVE1, DRIVE2, DRIVE3 = range(3)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logging.getLogger("drive")


def drive(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} entró en el comando drive")

    chat_id = update.effective_chat.id
    files = client_drive.get_all_files_description("0AHBcqK_64EhOUk9PVA")
    files.mimeType = files.mimeType.str.replace('application/', "").str.replace('vnd.google-apps.', "").str.replace('vnd.openxmlformats-officedocument.', "")
    keyboard = []
    for i, file in files.iterrows():
        keyboardline = []

        if file.mimeType == "folder":
            keyboardline.append(InlineKeyboardButton("📁" + file["name"], callback_data="ABRIR" + file.id))
        elif file.mimeType == "pdf":
            keyboardline.append(InlineKeyboardButton("📕" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "vnd.ms-excel" or file.mimeType == "spreadsheetml.sheet" or file.mimeType == "spreadsheet":
            keyboardline.append(InlineKeyboardButton("📕" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "image/jpeg" or file.mimeType == "image/jpeg":
            keyboardline.append(InlineKeyboardButton("🖼" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "text/plain":
            keyboardline.append(InlineKeyboardButton("🗒" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "video/3gpp" or file.mimeType == "video/mp4" or file.mimeType == "video/quicktime":
            keyboardline.append(InlineKeyboardButton("📹" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "msword" or file.mimeType == "document" or file.mimeType == "wordprocessingml.document":
            keyboardline.append(InlineKeyboardButton("📘" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "zip" or file.mimeType == "rar":
            keyboardline.append(InlineKeyboardButton("🗃" + file["name"], callback_data="DESCARGAR" + file.id))

        keyboard.append(keyboardline)
    keyboard.append([InlineKeyboardButton("Subir archivo", callback_data=str("CREAR"))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, "Files", reply_markup=reply_markup)

    return DRIVE1


def drive2(update: Update, context: CallbackContext):
    context.bot.deleteMessage(update.effective_chat.id, update.callback_query.message.message_id)
    chat_id = update.effective_chat.id
    file_id = update.callback_query.data.replace("ABRIR", "")
    files = client_drive.get_all_files_description(file_id)
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} selecciona la carpeta {file_id}")
    files.mimeType = files.mimeType.str.replace('application/', "").str.replace('vnd.google-apps.', "").str.replace('vnd.openxmlformats-officedocument.', "")
    keyboard = []
    for i, file in files.iterrows():
        keyboardline = []

        if file.mimeType == "folder":
            keyboardline.append(InlineKeyboardButton("📁" + file["name"], callback_data="ABRIR" + file.id))
        elif file.mimeType == "pdf":
            keyboardline.append(InlineKeyboardButton("📕" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "vnd.ms-excel" or file.mimeType == "spreadsheetml.sheet" or file.mimeType == "spreadsheet":
            keyboardline.append(InlineKeyboardButton("📗" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "image/jpeg" or file.mimeType == "image/jpeg":
            keyboardline.append(InlineKeyboardButton("🖼" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "text/plain":
            keyboardline.append(InlineKeyboardButton("🗒" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "video/3gpp" or file.mimeType == "video/mp4" or file.mimeType == "video/quicktime":
            keyboardline.append(InlineKeyboardButton("📹" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "msword" or file.mimeType == "document" or file.mimeType == "wordprocessingml.document":
            keyboardline.append(InlineKeyboardButton("📘" + file["name"], callback_data="DESCARGAR" + file.id))
        elif file.mimeType == "zip" or file.mimeType == "rar":
            keyboardline.append(InlineKeyboardButton("🗃" + file["name"], callback_data="DESCARGAR" + file.id))

        keyboard.append(keyboardline)
    keyboard.append([InlineKeyboardButton("Subir archivo", callback_data=str("CREAR"))])
    parent_folder = client_drive.get_parent_id(file_id)
    if parent_folder:
        keyboard.append([InlineKeyboardButton("Carpeta anterior", callback_data="ABRIR" + str(parent_folder))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, "Files", reply_markup=reply_markup)

    return DRIVE2


def drive_descargar(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    file_id = update.callback_query.data.replace("DESCARGAR", "")
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} descargo el archivo {file_id}")
    file = client_drive.get_file_description(file_id)
    doc = client_drive.get_file(file)
    context.bot.sendDocument(chat_id=chat_id, document=doc, timeout=2000)


conv_handler_drive = ConversationHandler(
    entry_points=[CommandHandler('drive', drive)],
    states={
        DRIVE1: [
            CallbackQueryHandler(drive2, pattern='^ABRIR'),
            CallbackQueryHandler(drive_descargar, pattern='^DESCARGAR')
        ],
        DRIVE2: [
            CallbackQueryHandler(drive2, pattern='^ABRIR'),
            CallbackQueryHandler(drive_descargar, pattern='^DESCARGAR')
        ],
        DRIVE3: [
            CallbackQueryHandler(drive2, pattern='^DESCARGAR')
        ],
    },
    fallbacks=[CommandHandler('drive', drive)],
)
