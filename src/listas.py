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
from datetime import datetime
import logging
from utils import database as db
import os, re

ELEGIR_LISTA, CREAR_LISTA1, CREAR_LISTA2, EDITAR_LISTA1, EDITAR_LISTA2, EDITAR_LISTA_A, EDITAR_LISTA_E, \
ELIMINAR_LISTA, FINAL_OPTION = range(9)
ID_MANITOBA = int(os.environ.get("ID_MANITOBA"))
logger = logging.getLogger("listas")


def listas(update: Update, context: CallbackContext):
    all_listas = db.select("listas")
    context.user_data["all_listas"] = all_listas
    if update.message:
        id_mensaje = update.message.message_id
        context.user_data["ediciones"] = []
    else:
        id_mensaje = update.callback_query.message.message_id

    chat_id = update.effective_chat.id
    user = update.effective_user

    logger.warning(f"{update.effective_chat.type} -> {user.first_name} entró en el comando listas")

    keyboard = []
    text = f"{user.first_name} ¿Qué quieres hacer?\n"

    for i, lista in all_listas.iterrows():
        keyboardline = []
        text += f" {i + 1}. {lista.nombre}\n"
        keyboardline.append(InlineKeyboardButton(i + 1, callback_data="NADA"))
        keyboardline.append(InlineKeyboardButton("👀", callback_data="VER" + str(lista.id)))
        # keyboardline.append(InlineKeyboardButton("🖋", callback_data="EDITAR" + str(lista.id)))
        keyboardline.append(InlineKeyboardButton("🗑", callback_data="ELIMINAR" + str(lista.id)))
        keyboard.append(keyboardline)
    keyboard.append([InlineKeyboardButton("Crear nueva lista", callback_data=str("CREAR"))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["query_listas"] = context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    context.bot.deleteMessage(chat_id, id_mensaje)
    return ELEGIR_LISTA


def ver_lista(update: Update, context: CallbackContext):
    all_listas = context.user_data["all_listas"]
    id_lista = int(update.callback_query.data.replace("VER", ""))

    lista = all_listas[all_listas.id == id_lista].iloc[0]

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} seleccionó ver la lista '{lista.nombre}'")
    text = f"{update.effective_user.first_name} ha solicitado ver la lista:\n{lista_to_text(lista)}"
    keyboard = [InlineKeyboardButton("Continuar", callback_data="CONTINUAR"),
                InlineKeyboardButton("Terminar", callback_data="TERMINAR")]
    update.callback_query.edit_message_text(parse_mode="HTML", text=text, reply_markup=InlineKeyboardMarkup([keyboard]))

    return FINAL_OPTION


def crear_lista(update: Update, context: CallbackContext):
    query = update.callback_query

    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} seleccionó crea lista")

    context.bot.deleteMessage(query.message.chat_id, query.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(query.message.chat_id, parse_mode="Markdown",
                                                              text=f"{update.effective_user.first_name}: Escribe el nombre de la lista")

    return CREAR_LISTA1


def crear_lista2(update: Update, context: CallbackContext):
    message = update.message
    context.user_data["nombre_lista"] = message.text

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} eligio el nombre {message.text}")

    context.bot.deleteMessage(message.chat_id, message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(message.chat_id, parse_mode="Markdown",
                                                              text=f"{update.effective_user.first_name}: Escribe la lista en el siguiente formato:\n**Elemento1**\n**Elemento2** ")
    return CREAR_LISTA2


def end_crear_lista(update: Update, context: CallbackContext):
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha escrito {update.message.text}")

    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)

    elementos = []
    for id, line in enumerate(update.message.text.splitlines()):
        elementos.append(line)

    tipo_elementos = [0] * len(elementos)
    new_lista = pd.Series(
        {"nombre": context.user_data["nombre_lista"], "elementos": elementos, "tipo_elementos": tipo_elementos,
         "creador": update.effective_user["id"],
         "fecha": datetime.today().strftime('%d/%m/%Y %H:%M'), "id_mensaje": 0})

    text = f"""{update.effective_user.first_name} ha creado la lista:\n{lista_to_text(new_lista)}\n"""
    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR_EDITAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha creado la lista {context.user_data['nombre_lista']}")
    mensaje_crear = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=text)
    new_lista.id_mensaje = mensaje_crear.message_id
    db.insert_lista(new_lista)
    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


def editar_lista(update: Update, context: CallbackContext):
    query = update.callback_query
    all_listas = db.select("listas")
    if query.data == "CONTINUAR_EDITAR":
        lista = all_listas[all_listas.id == context.user_data["id_lista"]].iloc[0]
    else:
        id_lista = int(query.data.replace("EDITAR", ""))
        lista = all_listas[all_listas.id == id_lista].iloc[0]
        context.user_data["lista"] = lista
        context.user_data["id_lista"] = id_lista

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha elegido editar la lista '{lista.nombre}'")

    keyboard = []
    for i, (elem, tipo) in enumerate(zip(lista.elementos, lista.tipo_elementos)):
        line_keyboard = [InlineKeyboardButton(str(i + 1), callback_data="NADA"),
                         InlineKeyboardButton("📝", callback_data="EDITAR" + str(i))]
        # if tipo == 0:
        #     line_keyboard.append(InlineKeyboardButton("⬜", callback_data="MARCAR" + str(i)))
        # else:
        #     line_keyboard.append(InlineKeyboardButton("👌🏽", callback_data="NADA"))
        line_keyboard.append(InlineKeyboardButton("🗑", callback_data="ELIMINAR" + str(i)))
        keyboard.append(line_keyboard)
    keyboard.append([InlineKeyboardButton("Añadir nuevo elemento", callback_data=str("AÑADIR"))])
    keyboard.append([InlineKeyboardButton("Atras", callback_data=str("ATRAS")),
                     InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.delete_message()
    texto = f"{update.effective_user.first_name}: ¿Que quieres hacer?:\n{lista_to_text(lista)}"
    context.user_data["query_elementos"] = context.bot.sendMessage(update.effective_chat.id,
                                                                   parse_mode="HTML", text=texto,
                                                                   reply_markup=reply_markup)
    return EDITAR_LISTA2


def editar_lista_anadir(update: Update, context: CallbackContext):
    # Añadir elementos
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha elegido añadir elementos a la lista")
    message = update.callback_query.message
    context.bot.deleteMessage(message.chat_id, message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(message.chat_id, parse_mode="HTML",
                                                              text=f"{update.effective_user.first_name}: Escribe los elementos a añadir en el siguiento formato:\n<b>Elemento1</b>\n<b>Elemento2</b> ")
    return EDITAR_LISTA_A


def end_editar_lista_anadir(update: Update, context: CallbackContext):
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha añadido {update.message.text}")
    lista = context.user_data["lista"]
    for line in update.message.text.splitlines():
        lista.elementos.append(line)
        lista.tipo_elementos.append(0)

    texto = f"{update.effective_user.first_name} ha añadido elementos a la lista:\n{lista_to_text(lista)}"

    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha editado la lista '{lista.nombre}'")

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR_EDITAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")
    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)
    lista.id_mensaje = new_message.message_id
    db.update_lista(lista)
    context.user_data["lista"] = lista
    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


def end_editar_lista_eliminar(update: Update, context: CallbackContext):
    lista = context.user_data["lista"]
    pos_elemento = int(update.callback_query.data.replace("ELIMINAR", ""))
    logger.warning(
        f"""{update.effective_chat.type} -> {update.effective_user.first_name} ha eliminado '{lista.elementos[pos_elemento]}' de la lista '{lista.nombre}'""")
    elemento_eliminado = lista.elementos[pos_elemento]
    lista.elementos.pop(pos_elemento)
    lista.tipo_elementos.pop(pos_elemento)
    texto = f"{update.effective_user.first_name} ha eliminado '{elemento_eliminado}' de la lista:\n{lista_to_text(lista)}"
    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR_EDITAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")
    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)
    lista.id_mensaje = new_message.message_id
    db.update_lista(lista)
    context.user_data["lista"] = lista
    update.callback_query.delete_message()
    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))

    return FINAL_OPTION


def end_editar_lista_marcar(update: Update, context: CallbackContext):
    lista = context.user_data["lista"]
    pos_elemento = int(update.callback_query.data.replace("MARCAR", ""))
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha marcado {lista.elementos[pos_elemento]}")
    lista.tipo_elementos[pos_elemento] = 1 - lista.tipo_elementos[pos_elemento]
    context.bot.deleteMessage(update.callback_query.message.chat_id, update.callback_query.message.message_id)
    texto = f"{update.effective_user.first_name} ha editado la lista:\n{lista_to_text(lista)}"

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR_EDITAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")

    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)
    lista.id_mensaje = new_message.message_id
    db.update_lista(lista)
    context.user_data["lista"] = lista
    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))

    return FINAL_OPTION


def editar_lista_editar(update: Update, context: CallbackContext):
    lista = context.user_data["lista"]
    message = update.callback_query.message
    context.bot.deleteMessage(message.chat_id, message.message_id)
    pos_elemento = int(update.callback_query.data.replace("EDITAR", ""))
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha seleccionado editar {lista.elementos[pos_elemento]}")
    context.user_data["pos_elemento"] = pos_elemento
    context.user_data["oldMessage"] = context.bot.sendMessage(message.chat_id, parse_mode="HTML",
                                                              text=f"Escribe el nuevo elemento para '{lista.elementos[pos_elemento]}'")
    return EDITAR_LISTA_E


def end_editar_lista_editar(update: Update, context: CallbackContext):
    lista = context.user_data["lista"]
    pos_elemento = context.user_data["pos_elemento"]
    elemento_editado = lista.elementos[pos_elemento]
    lista.elementos[pos_elemento] = update.message.text
    lista.tipo_elementos[pos_elemento] = 0
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha escrito el nuevo elemento {elemento_editado}")
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    texto = f"{update.effective_user.first_name} ha editado el elemento {pos_elemento + 1}. '{elemento_editado}' de la lista:\n{lista_to_text(lista)}"

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")

    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)
    lista.id_mensaje = new_message.message_id
    db.update_lista(lista)
    context.user_data["lista"] = lista
    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


def eliminar_lista(update: Update, context: CallbackContext):
    id_lista = int(update.callback_query.data.replace("ELIMINAR", ""))

    texto = f"¿Seguro que quieres eliminar la lista?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data="ELIMINAR" + str(id_lista)),
                 InlineKeyboardButton("Volver atrás", callback_data="VOLVER")]]

    update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

    return ELIMINAR_LISTA


def eliminar_lista2(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    id_lista = int(update.callback_query.data.replace("ELIMINAR", ""))
    lista = db.delete("listas", id_lista).iloc[0]
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha eliminado la lista '{lista.nombre}'")
    texto = f"{update.effective_user.first_name} ha eliminado la lista:\n{lista_to_text(lista)}"
    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    try:
        context.bot.deleteMessage(chat_id=ID_MANITOBA, message_id=int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")

    context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)

    context.bot.sendMessage(update.effective_chat.id, text="Quieres hacer algo mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))

    return FINAL_OPTION


def terminar(update: Update, context: CallbackContext):
    update.callback_query.delete_message()

    return ConversationHandler.END


def lista_to_text(lista):
    text = f"<b>{lista.nombre}</b>:\n"
    for n, elemento in enumerate(lista.elementos):
        if lista.tipo_elementos[n] == 0:
            text += f"  {n + 1}. {elemento}\n"
        else:
            text += f"  {n + 1}. <s>{elemento}</s>\n"
    return text


def editar_lista_manual(update: Update, context: CallbackContext):
    all_listas = db.select("listas")

    logger.warning(f"{update.effective_user.name} ha editado la lista con el mensaje\n{update.message.text} ")

    poll_name = (update.message.text.split(":\n"))[1]
    lista = all_listas[all_listas.nombre == poll_name].squeeze()
    elementos = (update.message.text.split(":\n", 2))[2].split("\n")
    elementos2 = [re.sub(r"^[\s]*[ ]*[0-9]*[.]*[ ]*", r"", element) for element in elementos]
    lista.elementos = elementos2
    lista.tipo_elementos = [0] * len(elementos2)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    try:
        context.bot.deleteMessage(ID_MANITOBA, int(lista.id_mensaje))
    except:
        logger.error(f"Fallo al eliminar el mensaje  {lista.id_mensaje}")
    texto = f"{update.effective_user.first_name} ha editado la lista:\n{lista_to_text(lista)}"
    new_message = context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=texto)
    lista.id_mensaje = new_message.message_id
    db.update_lista(lista)


def get_conv_handler_listas():
    conv_handler_listas = ConversationHandler(
        entry_points=[CommandHandler('listas', listas)],
        states={
            ELEGIR_LISTA: [
                CallbackQueryHandler(ver_lista, pattern='^VER'),
                CallbackQueryHandler(crear_lista, pattern='^CREAR'),
                CallbackQueryHandler(editar_lista, pattern='^EDITAR'),
                CallbackQueryHandler(eliminar_lista, pattern='^ELIMINAR'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')
            ],
            CREAR_LISTA1: [MessageHandler(Filters.text & ~Filters.command, crear_lista2)],
            CREAR_LISTA2: [MessageHandler(Filters.text & ~Filters.command, end_crear_lista)],
            EDITAR_LISTA2: [
                CallbackQueryHandler(editar_lista_anadir, pattern='^AÑADIR$'),
                CallbackQueryHandler(end_editar_lista_marcar, pattern='^MARCAR'),
                CallbackQueryHandler(editar_lista_editar, pattern='^EDITAR'),
                CallbackQueryHandler(end_editar_lista_eliminar, pattern='^ELIMINAR'),
                CallbackQueryHandler(listas, pattern='^ATRAS'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
            EDITAR_LISTA_A: [MessageHandler(Filters.text & ~Filters.command, end_editar_lista_anadir)],
            EDITAR_LISTA_E: [MessageHandler(Filters.text & ~Filters.command, end_editar_lista_editar)],
            ELIMINAR_LISTA: [
                CallbackQueryHandler(eliminar_lista2, pattern='^ELIMINAR'),
                CallbackQueryHandler(listas, pattern='^VOLVER')],
            FINAL_OPTION: [
                CallbackQueryHandler(listas, pattern='^CONTINUAR$'),
                CallbackQueryHandler(editar_lista, pattern='^CONTINUAR_EDITAR$'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR')],

        },
        fallbacks=[CommandHandler('listas', listas)],
    )
    return conv_handler_listas
