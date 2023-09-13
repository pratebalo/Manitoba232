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
import src.utilitys as ut
import logging
import re
from datetime import datetime
from utils import database as db
from decouple import config

CHOOSE_LIST, CREATE_LIST, CREATE_LIST2, CREATE_LIST3, DELETE_LIST, FINAL_OPTION = range(6)
ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logging.getLogger("lists")


def lists(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)
    all_listas = db.select("listas")
    context.user_data["all_lists"] = all_listas
    if update.message:
        id_message = update.message.message_id
    else:
        id_message = update.callback_query.message.message_id

    chat_id = update.effective_chat.id

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} entró en el comando listas")

    keyboard = []
    text = f"{context.user_data['user'].apodo} ¿Qué quieres hacer?\n"

    for i, lista in all_listas.iterrows():
        keyboard_line = []
        text += f" {i + 1}. {lista.nombre}\n"
        keyboard_line.append(InlineKeyboardButton(i + 1, callback_data="NOTHING"))
        keyboard_line.append(InlineKeyboardButton("👀", callback_data="VIEW" + str(lista.id)))
        keyboard_line.append(InlineKeyboardButton("🗑", callback_data="DELETE" + str(lista.id)))
        keyboard.append(keyboard_line)
    keyboard.append([InlineKeyboardButton("Crear nueva lista", callback_data=str("CREATE"))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("END"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["query_listas"] = context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    context.bot.deleteMessage(chat_id, id_message)
    return CHOOSE_LIST


def view_list(update: Update, context: CallbackContext):
    all_listas = context.user_data["all_lists"]
    id_lista = int(update.callback_query.data.replace("VIEW", ""))

    lista = all_listas[all_listas.id == id_lista].iloc[0]

    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó ver la lista '{lista.nombre}'")
    text = f"{context.user_data['user'].apodo} ha solicitado ver la lista:\n{list_to_text(lista)}"
    keyboard = [InlineKeyboardButton("Continuar", callback_data="CONTINUE"),
                InlineKeyboardButton("Terminar", callback_data="END")]
    update.callback_query.edit_message_text(parse_mode="HTML", text=text, reply_markup=InlineKeyboardMarkup([keyboard]))

    return FINAL_OPTION


def create_list(update: Update, context: CallbackContext):
    query = update.callback_query

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó crear lista")

    context.bot.deleteMessage(query.message.chat_id, query.message.message_id)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lista numerada", callback_data="NUMBERED"), InlineKeyboardButton("Lista normal", callback_data="NORMAL")],
         [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = context.bot.sendMessage(query.message.chat_id, parse_mode="Markdown", reply_markup=keyboard,
                                                              text=f"{context.user_data['user'].apodo}: Qué tipo de lista quieres crear?")

    return CREATE_LIST


def create_list2(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data["type_list"] = update.callback_query.message.text
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó {update.callback_query.message.text}")

    context.bot.deleteMessage(query.message.chat_id, query.message.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = context.bot.sendMessage(query.message.chat_id, parse_mode="Markdown", reply_markup=keyboard,
                                                              text=f"{context.user_data['user'].apodo}: Escribe el nombre de la lista")

    return CREATE_LIST2


def create_list3(update: Update, context: CallbackContext):
    message = update.message
    context.user_data["list_name"] = message.text

    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} eligio el nombre {message.text}")

    context.bot.deleteMessage(message.chat_id, message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = context.bot.sendMessage(
        message.chat_id,
        parse_mode="Markdown",
        reply_markup=keyboard,
        text=f"{context.user_data['user'].apodo}: Escribe la lista en el siguiente formato:\n**Elemento1**\n**Elemento2** ")

    return CREATE_LIST3


def end_crete_list(update: Update, context: CallbackContext):
    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha escrito {update.message.text}")

    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)

    elements = []
    for idx, line in enumerate(update.message.text.splitlines()):
        elements.append(line)

    type_elements = [0] * len(elements)
    new_lista = pd.Series(
        {"nombre": context.user_data["list_name"], "elementos": elements, "tipo_elementos": type_elements,
         "creador": update.effective_user["id"],
         "fecha": datetime.today().strftime('%d/%m/%Y %H:%M'), "id_mensaje": 0})

    text = f"""{context.user_data['user'].apodo} ha creado la lista:\n{list_to_text(new_lista)}\n"""

    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha creado la lista {context.user_data['list_name']}")
    create_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    new_lista.id_mensaje = create_message.message_id
    db.insert_list(new_lista)
    lists(update, context)
    return CHOOSE_LIST


def delete_list(update: Update, context: CallbackContext):
    id_list = int(update.callback_query.data.replace("DELETE", ""))

    text = f"¿Seguro que quieres eliminar la lista?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data="DELETE" + str(id_list)),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_LIST


def delete_list2(update: Update, context: CallbackContext):
    id_lista = int(update.callback_query.data.replace("DELETE", ""))
    lista = db.delete("listas", id_lista).iloc[0]
    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha eliminado la lista '{lista.nombre}'")
    text = f"{context.user_data['user'].apodo} ha eliminado la lista:\n{list_to_text(lista)}"
    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")

    context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)

    lists(update, context)

    return CHOOSE_LIST


def end(update: Update, context: CallbackContext):
    update.callback_query.delete_message()

    return ConversationHandler.END


def list_to_text(lista):
    text = f"<b>{lista.nombre}</b>:\n"
    for n, element in enumerate(lista.elementos):
        if lista.tipo_elementos[n] == 0:
            text += f"  {n + 1}. {element}\n"
        else:
            text += f"  {n + 1}. <s>{element}</s>\n"
    return text


def edit_list_manual(update: Update, context: CallbackContext):
    all_lists = db.select("listas")

    logger.warning(f"{context.user_data['user'].apodo} ha editado la lista con el mensaje\n{update.message.text} ")

    poll_name = (update.message.text.split(":\n"))[1]
    lista = all_lists[all_lists.nombre == poll_name].squeeze()
    elements = (update.message.text.split(":\n", 2))[2].split("\n")
    elements2 = [re.sub(r"^[\s]*[ ]*[0-9]*[.]*[ ]*", r"", element) for element in elements]
    lista.elementos = elements2
    lista.tipo_elementos = [0] * len(elements2)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    try:
        context.bot.deleteMessage(ID_MANITOBA, int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")
    text = f"{context.user_data['user'].apodo} ha editado la lista:\n{list_to_text(lista)}"
    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    lista.id_mensaje = new_message.message_id
    db.update_list(lista)


def get_conv_handler_listas():
    conv_handler_listas = ConversationHandler(
        entry_points=[CommandHandler('listas', lists)],
        states={
            CHOOSE_LIST: [
                CallbackQueryHandler(view_list, pattern='^VIEW'),
                CallbackQueryHandler(create_list, pattern='^CREATE'),
                CallbackQueryHandler(delete_list, pattern='^DELETE'),
                CallbackQueryHandler(end, pattern='^END')
            ],
            CREATE_LIST: [CallbackQueryHandler(lists, pattern='^CANCEL$'),
                          CallbackQueryHandler(create_list2)],
            CREATE_LIST2: [MessageHandler(Filters.text & ~Filters.command, create_list3),
                           CallbackQueryHandler(lists, pattern='^CANCEL$')],
            CREATE_LIST3: [MessageHandler(Filters.text & ~Filters.command, end_crete_list),
                           CallbackQueryHandler(lists, pattern='^CANCEL$')],
            DELETE_LIST: [
                CallbackQueryHandler(delete_list2, pattern='^DELETE'),
                CallbackQueryHandler(lists, pattern='^BACK')],
            FINAL_OPTION: [
                CallbackQueryHandler(lists, pattern='^CONTINUE'),
                CallbackQueryHandler(end, pattern='^END')],

        },
        fallbacks=[CommandHandler('listas', lists)],
    )
    return conv_handler_listas
