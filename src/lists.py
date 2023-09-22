from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

import pandas as pd
import src.utilitys as ut
import re
from datetime import datetime
from utils import database as db
from decouple import config
from utils import logger_config

CHOOSE_LIST, CREATE_LIST, CREATE_LIST2, CREATE_LIST3, DELETE_LIST, FINAL_OPTION = range(6)
ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger


def lists_state(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)
    if update.message is not None:
        id_message = update.message.message_id
    else:
        id_message = update.callback_query.message.message_id
    if update.effective_chat.id == ID_MANITOBA:
        context.bot.sendMessage(chat_id=update.effective_user.id, text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /listas")
        return

    all_lists = db.select("lists")
    context.user_data["all_lists"] = all_lists
    chat_id = update.effective_chat.id

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} entró en el comando listas")

    keyboard = []
    text = f"{context.user_data['user'].apodo} ¿Qué quieres hacer?\n"

    for i, my_list in all_lists.iterrows():
        keyboard_line = []
        text += f" {i + 1}. {my_list.list_name}\n"
        keyboard_line.append(InlineKeyboardButton(i + 1, callback_data="NOTHING"))
        keyboard_line.append(InlineKeyboardButton("👀", callback_data="VIEW" + str(my_list.id)))
        keyboard_line.append(InlineKeyboardButton("🗑", callback_data="DELETE" + str(my_list.id)))
        keyboard.append(keyboard_line)
    keyboard.append([InlineKeyboardButton("Crear nueva lista", callback_data="CREATE")])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data="END")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    context.bot.deleteMessage(chat_id, id_message)
    return CHOOSE_LIST


def view_list(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    all_lists = context.user_data["all_lists"]
    id_list = int(update.callback_query.data.replace("VIEW", ""))

    my_list = all_lists[all_lists.id == id_list].iloc[0]

    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó ver la lista '{my_list.list_name}'")

    text = f"{context.user_data['user'].apodo} ha solicitado ver la lista:\n{list_to_text(my_list)}"
    new_message = context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML", text=text)
    if chat_id == ID_MANITOBA:
        try:
            context.bot.deleteMessage(ID_MANITOBA, int(my_list.message_id))
        except Exception as error:
            logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")
        my_list.message_id = new_message.message_id
        db.update_list(my_list)
    lists_state(update, context)


def create_list(update: Update, context: CallbackContext):
    query = update.callback_query

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó crear lista")

    context.bot.deleteMessage(query.message.chat_id, query.message.message_id)

    text = "Esto es una lista numerada:\n  1. Elemento1\n  2. Todo tiene un espaciado al principio y un numero\n  3. Y se actualizan los numeros " \
           "automaticamente\n----------------------------\nEsto es una lista con guiones:\n  - Elemento1\n  - Igual que la numerada pero sin numeros" \
           "\n----------------------------\nEsto es una lista sin formato:\nPuedes poner todo\n -como\n -quieras\n" \
           "       y lo mantiene sin editar\n+tal como está\n "
    context.user_data["oldMessage"] = context.bot.sendMessage(query.message.chat_id, text=text)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lista numerada", callback_data="NUMBERED"), InlineKeyboardButton("Lista con guiones", callback_data="NORMAL"),
          InlineKeyboardButton("Sin formato", callback_data="UNFORMAT")],
         [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.bot.sendMessage(query.message.chat_id, parse_mode="Markdown", reply_markup=keyboard,
                            text=f"{context.user_data['user'].apodo}: Qué tipo de lista quieres crear?")

    return CREATE_LIST


def create_list2(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data["type_list"] = update.callback_query.data
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó {update.callback_query.message.text}")

    context.bot.deleteMessage(query.message.chat_id, query.message.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
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

    new_list = pd.Series(
        {"list_name": context.user_data["list_name"], "elements": elements, "type_list": context.user_data["type_list"],
         "creator": update.effective_user["id"], "date": datetime.today().strftime('%d/%m/%Y %H:%M'), "message_id": 0})

    text = f"""{context.user_data['user'].apodo} ha creado la lista:\n{list_to_text(new_list)}\n"""

    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha creado la lista {context.user_data['list_name']}")
    create_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    new_list.message_id = create_message.message_id
    db.insert_list(new_list)
    lists_state(update, context)
    return CHOOSE_LIST


def delete_list(update: Update, _: CallbackContext):
    id_list = int(update.callback_query.data.replace("DELETE", ""))

    text = f"¿Seguro que quieres eliminar la lista?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data="DELETE" + str(id_list)),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_LIST


def delete_list2(update: Update, context: CallbackContext):
    list_id = int(update.callback_query.data.replace("DELETE", ""))
    my_list = db.delete("lists", list_id).iloc[0]
    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha eliminado la lista '{my_list.list_name}'")
    text = f"{context.user_data['user'].apodo} ha eliminado la lista:\n{list_to_text(my_list)}"
    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(my_list.message_id))
    except Exception as error:
        logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")

    context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)

    lists_state(update, context)

    return CHOOSE_LIST


def end(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha salido del comando asistencia")

    return ConversationHandler.END


def list_to_text(my_list):
    text = f"<b>{my_list.list_name}</b>:\n"
    for n, element in enumerate(my_list.elements):
        if my_list.type_list == "NUMBERED":
            text += f"  {n + 1}. {element}\n"
        elif my_list.type_list == "UNFORMAT":
            text += f"{element}\n"
        else:
            text += f"  - {element}\n"
    return text


def edit_list_manual(update: Update, context: CallbackContext):
    all_lists = db.select("lists")
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{context.user_data['user'].apodo} ha editado la lista con el mensaje\n{update.message.text} ")

    poll_name = (update.message.text.split(":\n"))[1]
    my_list = all_lists[all_lists.list_name == poll_name].squeeze()
    elements = (update.message.text.split(":\n", 2))[2].split("\n")
    if my_list.type_list == "NUMBERED":
        elements = [re.sub(r"^\s* *[0-9]*[.]* *", r"", element) for element in elements]
    elif my_list.type_list == "NORMAL":
        elements = [re.sub(r"^\s* *-* *", "", element) for element in elements]
    my_list.elements = elements
    my_list.tipo_elementos = [0] * len(elements)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    try:
        context.bot.deleteMessage(ID_MANITOBA, int(my_list.message_id))
    except Exception as error:
        logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")
    text = f"{context.user_data['user'].apodo} ha editado la lista:\n{list_to_text(my_list)}"
    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    my_list.message_id = new_message.message_id
    db.update_list(my_list)


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('listas', lists_state)],
        states={
            CHOOSE_LIST: [
                CallbackQueryHandler(view_list, pattern='^VIEW'),
                CallbackQueryHandler(create_list, pattern='^CREATE'),
                CallbackQueryHandler(delete_list, pattern='^DELETE'),
                CallbackQueryHandler(end, pattern='^END')
            ],
            CREATE_LIST: [CallbackQueryHandler(lists_state, pattern='^CANCEL$'),
                          CallbackQueryHandler(create_list2)],
            CREATE_LIST2: [MessageHandler(Filters.text & ~Filters.command, create_list3),
                           CallbackQueryHandler(lists_state, pattern='^CANCEL$')],
            CREATE_LIST3: [MessageHandler(Filters.text & ~Filters.command, end_crete_list),
                           CallbackQueryHandler(lists_state, pattern='^CANCEL$')],
            DELETE_LIST: [
                CallbackQueryHandler(delete_list2, pattern='^DELETE'),
                CallbackQueryHandler(lists_state, pattern='^BACK')],
            FINAL_OPTION: [
                CallbackQueryHandler(lists_state, pattern='^CONTINUE'),
                CallbackQueryHandler(end, pattern='^END')],

        },
        fallbacks=[CommandHandler('listas', lists_state)],
    )
