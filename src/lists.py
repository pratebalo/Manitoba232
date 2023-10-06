from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler, ContextTypes

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


async def lists_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.effective_chat.id == ID_MANITOBA:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando listas desde Manitoba")
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /listas")
        return ConversationHandler.END
    if update.message:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando listas")
    else:
        await update.callback_query.delete_message()
        logger.warning(f"{context.user_data['user'].apodo} ha vuelto al inicio de listas")
    all_lists = db.select("lists")
    context.user_data["all_lists"] = all_lists

    keyboard = []
    text = f"¿Qué quieres hacer?\n"

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

    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    return CHOOSE_LIST


async def view_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    all_lists = context.user_data["all_lists"]
    id_list = int(update.callback_query.data.replace("VIEW", ""))

    my_list = all_lists[all_lists.id == id_list].iloc[0]

    logger.warning(f"{context.user_data['user'].apodo} seleccionó ver la lista '{my_list.list_name}'")

    text = f"{context.user_data['user'].apodo} ha solicitado ver la lista:\n{list_to_text(my_list)}"
    new_message = await context.bot.send_message(update.effective_chat.id, parse_mode="HTML", text=text)
    if chat_id == ID_MANITOBA:
        try:
            await context.bot.delete_message(ID_MANITOBA, int(my_list.message_id))
        except Exception as error:
            logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")
        my_list.message_id = new_message.message_id
        db.update_list(my_list)
    await lists_state(update, context)


async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    logger.warning(f"{context.user_data['user'].apodo} seleccionó crear lista")

    await context.bot.delete_message(query.message.chat_id, query.message.message_id)

    text = "Esto es una lista <b>numerada</b>:\n  1. Elemento1\n  2. Todo tiene un espaciado al principio y un numero\n  3. Y se actualizan los numeros " \
           "automaticamente\n----------------------------\nEsto es una lista con <b>guiones</b>:\n  - Elemento1\n  - Igual que la numerada pero sin numeros" \
           "\n----------------------------\nEsto es una lista <b>sin formato</b>:\nPuedes poner todo\n -como\n -quieras\n" \
           "       y lo mantiene sin editar\n+tal como está\n----------------------------\n <b>Qué tipo de lista quieres crear?</b>"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Numerada", callback_data="NUMBERED"),
          InlineKeyboardButton("Con guiones", callback_data="NORMAL"),
          InlineKeyboardButton("Sin formato", callback_data="UNFORMAT")],
         [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    await context.bot.send_message(query.message.chat_id, parse_mode="HTML", reply_markup=keyboard, text=text)

    return CREATE_LIST


async def create_list2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["type_list"] = update.callback_query.data
    logger.warning(f"{context.user_data['user'].apodo} eligió el tipo {update.callback_query.data}")

    await context.bot.delete_message(query.message.chat_id, query.message.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await context.bot.send_message(query.message.chat_id, parse_mode="Markdown", reply_markup=keyboard,
                                                                     text=f"Escribe el nombre de la lista")
    return CREATE_LIST2


async def create_list3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    context.user_data["list_name"] = message.text

    logger.warning(f"{context.user_data['user'].apodo} eligió el nombre {message.text}")

    await context.bot.delete_message(message.chat_id, message.message_id)
    await context.bot.delete_message(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await context.bot.send_message(
        message.chat_id,
        parse_mode="Markdown",
        reply_markup=keyboard,
        text=f"Escribe la lista en el siguiente formato:\n**Elemento1**\n**Elemento2** ")

    return CREATE_LIST3


async def end_crete_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} ha escrito\n{update.message.text}")

    await context.bot.delete_message(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)

    elements = []
    for idx, line in enumerate(update.message.text.splitlines()):
        elements.append(line)

    new_list = pd.Series(
        {"list_name": context.user_data["list_name"], "elements": elements, "type_list": context.user_data["type_list"],
         "creator": update.effective_user["id"], "date": datetime.today().strftime('%d/%m/%Y %H:%M'), "message_id": 0})

    text = f"""{context.user_data['user'].apodo} ha creado la lista:\n{list_to_text(new_list)}\n"""

    logger.warning(f"{context.user_data['user'].apodo} ha creado la lista {context.user_data['list_name']}")
    create_message = await context.bot.send_message(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    new_list.message_id = create_message.message_id
    db.insert_list(new_list)
    await lists_state(update, context)
    return CHOOSE_LIST


async def delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_list = int(update.callback_query.data.replace("DELETE", ""))
    all_lists = context.user_data["all_lists"]
    my_list = all_lists[all_lists.id == id_list].squeeze()
    logger.warning(f"{context.user_data['user'].apodo} ha elegido eliminar la lista '{my_list.list_name}'")

    text = f"¿Seguro que quieres eliminar la lista?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data="DELETE" + str(id_list)),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_LIST


async def delete_list2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    list_id = int(update.callback_query.data.replace("DELETE", ""))
    my_list = db.delete("lists", list_id).iloc[0]
    logger.warning(f"{context.user_data['user'].apodo} ha confirmado eliminar la lista '{my_list.list_name}'")
    text = f"{context.user_data['user'].apodo} ha eliminado la lista:\n{list_to_text(my_list)}"
    try:
        await context.bot.delete_message(chat_id=ID_MANITOBA, message_id=int(my_list.message_id))
    except Exception as error:
        logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")

    await context.bot.send_message(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)

    await lists_state(update, context)

    return CHOOSE_LIST


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando listas")

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


async def edit_list_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
    try:
        await context.bot.delete_message(ID_MANITOBA, int(my_list.message_id))
    except Exception as error:
        logger.error(f"Fallo al eliminar el mensaje  {my_list.message_id} -> {error}")
    text = f"{context.user_data['user'].apodo} ha editado la lista:\n{list_to_text(my_list)}"
    new_message = await context.bot.send_message(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
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
            CREATE_LIST2: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_list3),
                           CallbackQueryHandler(lists_state, pattern='^CANCEL$')],
            CREATE_LIST3: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_crete_list),
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
