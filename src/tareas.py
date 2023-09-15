from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters
from utils import database as db
from decouple import config
from datetime import date
from telegram_bot_calendar import DetailedTelegramCalendar, DAY

import pandas as pd
import logging
import random
import src.utilitys as ut

# Stages
ELEGIR_TAREA, CREAR_TAREA1, CREAR_TAREA2, CREAR_TAREA3, CREAR_TAREA4, CREAR_TAREA5, FINAL_OPTION = range(7)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logging.getLogger("tareas")

your_translation_months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                           "Octubre", "Noviembre", "Diciembre"]
your_translation_days_of_week = list('LMXJVSD')
PRUEBA = {'y': 'año', 'm': 'mes', 'd': 'dia'}


class MyTranslationCalendar(DetailedTelegramCalendar):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_of_week['es'] = your_translation_days_of_week
        self.months['es'] = your_translation_months
        self.first_step = DAY
        self.min_date = date.today()
        self.locale = "es"

    empty_nav_button = "❌"
    middle_button_day = "{month}"
    prev_button = "⏪"
    next_button = "⏩"


def recordar_tareas(context: CallbackContext):
    all_tareas = db.select("tareas")
    data = db.select("data")
    for _, tarea in all_tareas[~all_tareas.completada].iterrows():
        days = (tarea.fecha - date.today()).days
        text = ""
        if days % 7 == 0:
            text = f"Recuerda que tienes esta tarea pendiente\n{tarea_to_text(tarea, data)}"
        elif days == 3:
            text = f"Te quedan 3 diassssss\n{tarea_to_text(tarea, data)}"
        elif days == 1:
            text = f"Que era para mañanaaaaaaaa\n{tarea_to_text(tarea, data)}"
        if text:
            for persona in tarea.personas:
                context.bot.sendMessage(chat_id=persona, parse_mode="HTML", text=text)


def tareas(update: Update, context: CallbackContext):

    ut.set_actual_user(update.effective_user.id, context)
    recordar_tareas(context)
    if update.message:
        context.user_data["ediciones"] = []
        context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    else:
        context.bot.deleteMessage(update.effective_chat.id, update.callback_query.message.message_id)
    user = update.effective_user
    context.user_data["creador_tarea"] = user["id"]
    logger.warning(f"{update.effective_chat.type} -> {user.first_name} entro en el comando tareas")
    all_tareas = db.select("tareas")
    data = db.select("data")
    context.user_data["data"] = data
    context.user_data["all_tareas"] = all_tareas
    text = f"{update.effective_user.first_name}: ¿Qué quieres hacer?\n"
    keyboard = []
    for i, tarea in all_tareas.iterrows():
        part_keyboard = []
        text += f"{i + 1}. {tarea.descripcion}\n"
        part_keyboard.append(InlineKeyboardButton(str(i + 1), callback_data="NADA"))
        part_keyboard.append(InlineKeyboardButton("👀", callback_data="VER" + str(i)))
        if tarea.completada:
            part_keyboard.append(InlineKeyboardButton("🏁", callback_data="NADA"))
        else:
            if user.id in tarea.personas or user.id == tarea.creador:
                part_keyboard.append(InlineKeyboardButton("‼", callback_data="COMPLETAR" + str(i)))
            else:
                part_keyboard.append(InlineKeyboardButton(" ", callback_data="NADA"))
        # part_keyboard.append(InlineKeyboardButton("🖋", callback_data="EDITAR" + str(i)))
        part_keyboard.append(InlineKeyboardButton("🗑", callback_data="ELIMINAR" + str(i)))
        keyboard.append(part_keyboard)
    keyboard.append([InlineKeyboardButton("Crear nueva tarea", callback_data="CREAR")])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data="TERMINAR")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    context.bot.sendMessage(update.effective_chat.id, text, reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    context.user_data["personas_asignadas"] = []
    return ELEGIR_TAREA


def ver_tarea(update: Update, context: CallbackContext):
    all_tareas = context.user_data["all_tareas"]
    data = context.user_data["data"]
    pos_tarea = int(update.callback_query.data.replace("VER", ""))
    tarea = all_tareas.iloc[pos_tarea]
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} seleccionó ver la tarea '{tarea.descripcion}'")
    texto = f"{update.effective_user.first_name} ha solicitado ver la tarea:\n" + tarea_to_text(tarea, data)

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    update.callback_query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


def crear_tarea(update: Update, context: CallbackContext):
    context.user_data["oldMessage"] = update.callback_query.edit_message_text(parse_mode="HTML",
                                                                              text="<b>Creando tarea</b>\nIntroduce la descripción")
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha seleccionado crear tarea")
    return CREAR_TAREA1


def elegir_fecha(update: Update, context: CallbackContext):
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha introducido la descripcion: {update.message.text}")
    context.user_data["descripcion"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    calendar, step = MyTranslationCalendar().build()
    context.bot.sendMessage(update.effective_chat.id, parse_mode=f"HTML", reply_markup=calendar,
                            text=f"<b>Creando tarea</b>\nElige {PRUEBA[step]}")
    return CREAR_TAREA2


def elegir_fecha2(update: Update, context: CallbackContext):
    result, key, step = MyTranslationCalendar().process(update.callback_query.data)
    if not result and key:
        context.bot.edit_message_text(parse_mode="HTML", text=f"<b>Creando tarea</b>\nElige {PRUEBA[step]}",
                                      chat_id=update.callback_query.message.chat_id,
                                      message_id=update.callback_query.message.message_id,
                                      reply_markup=key)
    elif result:
        context.bot.deleteMessage(update.effective_chat.id, update.callback_query.message.message_id)
        result = result.strftime("%d/%m/%Y")
        context.user_data["fecha"] = result

        logger.warning(
            f"{update.effective_chat.type} -> {update.effective_user.first_name} ha elegido la fecha {result}")
        keyboard = []
        part_keyboard = []
        data = context.user_data["data"]
        for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
            part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
            if i % 3 == 2 or i == len(data) - 1:
                keyboard.append(part_keyboard)
                part_keyboard = []

        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML", reply_markup=reply_markup,
                                text="<b>Creando tarea</b>\n¿A qúe persona quieres asignarla?")

        return CREAR_TAREA3


def asignar_persona2(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data["personas_asignadas"].append(int(query.data))
    keyboard = []
    part_keyboard = []
    data = context.user_data["data"]
    for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
        if not persona.id in context.user_data["personas_asignadas"]:
            part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
        if i % 3 == 2 or i == len(data) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []
    keyboard.append([InlineKeyboardButton("NO", callback_data="NO")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(parse_mode="HTML", reply_markup=reply_markup,
                            text="<b>Creando tarea</b>\nPersona asignada. ¿Quieres asignarla a alguien más?")
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha asignado a {query.data} a la tarea")
    return CREAR_TAREA4


def end_creacion(update: Update, context: CallbackContext):
    context.bot.deleteMessage(update.effective_chat.id, update.callback_query.message.message_id)
    data = context.user_data["data"]
    tarea = pd.Series(
        {"descripcion": context.user_data["descripcion"], "personas": context.user_data["personas_asignadas"],
         "fecha": context.user_data["fecha"], "creador": context.user_data["creador_tarea"]})

    texto = f"""{update.effective_user.first_name} ha creado la tarea:\n""" + tarea_to_text(tarea, data)

    db.insert_tarea(tarea)
    sticker = ["CAACAgIAAx0CTey1gAACAiJgDvqYZC9VcMAvbJu8c_LKDD4R-gACigAD9wLID_jyogIDMJ9NHgQ",
               "CAACAgIAAx0CTey1gAACAiNgDvqb4ZQnkhOJqxBxcfNeC6PKiAACDAEAAvcCyA8bE6ozG0L6sx4E",
               "CAACAgIAAx0CTey1gAACAiRgDvqdnzEjoQWAhx8ixlNBsr89HgAC8wADVp29Cmob68TH-pb-HgQ",
               "CAACAgIAAx0CTey1gAACAiVgDvqp-x4WxBTpA_8BLeNZHmgTLQACDgADwDZPEyNXFESHbtZlHgQ",
               "CAACAgIAAx0CTey1gAACAiZgDvq1usw0Bk8BhySorPlmW4MIUwACNAADWbv8JWBOiTxAs-8HHgQ",
               "CAACAgIAAx0CTey1gAACAidgDvq9Hg4rMGs1decm0hjCn21HOgACCAEAAvcCyA_dAQAB7MrQa-UeBA"]

    personas = data[data.id.isin(tarea.personas)]
    for _, persona in personas.iterrows():
        try:
            context.bot.sendMessage(persona.id, parse_mode="HTML",
                                    text="Se te ha asignado la siguiente tarea:\n" + texto)
        except:
            context.bot.sendMessage(ID_MANITOBA, text=f"{persona.apodo} no me tiene activado")
            context.bot.sendSticker(ID_MANITOBA, sticker=sticker[random.randint(0, len(sticker) - 1)])
    logger.warning(f"{update.effective_chat.type} -> Se ha creado la tarea {tarea.descripcion}")

    keyboard = [[InlineKeyboardButton("Continuar", callback_data="CONTINUAR"),
                 InlineKeyboardButton("Terminar", callback_data="TERMINAR")]]

    context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML", text=texto,
                            reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


def editar_tarea(update: Update, context: CallbackContext):
    """Show new choice of buttons"""
    query = update.callback_query

    data = context.user_data["data"]
    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("EDITAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    texto = f"{update.effective_user.first_name} ha editado la tarea \n<b>{tarea_to_text(tarea, data)}</b>"
    keyboard = [[InlineKeyboardButton("Continuar", callback_data="CONTINUAR"),
                 InlineKeyboardButton("Terminar", callback_data="TERMINAR")]]

    update.callback_query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


def eliminar_tarea(update: Update, context: CallbackContext):
    query = update.callback_query

    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("ELIMINAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    db.delete("tareas", tarea.id)
    data = context.user_data["data"]
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name}  ha eliminado la tarea \n{tarea_to_text(tarea, data)}")
    texto = f"{update.effective_user.first_name} ha eliminado la tarea \n<b>{tarea_to_text(tarea, data)}</b>"

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


def completar_tarea(update: Update, context: CallbackContext):
    query = update.callback_query
    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("COMPLETAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    tarea.completada = True
    db.update_tarea(tarea)
    data = context.user_data["data"]
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name}  ha completado la tarea \n{tarea_to_text(tarea, data)}")
    texto = f"<a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a> ha completado la tarea!!!!!! \n<b>{tarea_to_text(tarea, data)}</b>"

    query.delete_message()
    if context.user_data["ediciones"]:
        context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML",
                                text="\n".join(context.user_data["ediciones"]))
    context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=texto)
    stickers = ["CAACAgIAAxkBAAICXmAasBQ2GrCJTRmfjzDArpTLXfVtAAJJAQACVp29CnVtIjfXzilUHgQ",
                "CAACAgIAAxkBAAICX2AasB6gnf_gqA3c8s00wW3AFj5QAAJNAANZu_wlKIGgbd0bgvceBA",
                "CAACAgIAAxkBAAICYGAasCfRVfZcMOVWzZiuX2pFuZC7AAJXAAPBnGAMxgL9s1SbpjQeBA",
                "CAACAgIAAxkBAAICYWAasDPbxJKIINhcFeiQsiYvVEGpAAJjAANOXNIpRcBzCXnlr_AeBA"]
    context.bot.sendSticker(ID_MANITOBA, sticker=random.choice(stickers))
    return ConversationHandler.END


def tarea_to_text(tarea, data):
    text = f"-<b>{tarea.descripcion}</b>:\n" \
           f"-<b>{tarea.fecha}</b>\n"
    personas = data[data.id.isin(tarea.personas)]
    for _, persona in personas.iterrows():
        text += f"  +{persona.apodo}\n"
    return text


def terminar(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha salido de tareas")
    if context.user_data["ediciones"]:
        context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML",
                                text="\n".join(context.user_data["ediciones"]))
    return ConversationHandler.END


def get_conv_handler_tareas():
    conv_handler_tareas = ConversationHandler(
        entry_points=[CommandHandler('tareas', tareas)],
        states={
            ELEGIR_TAREA: [
                CallbackQueryHandler(ver_tarea, pattern='^VER'),
                CallbackQueryHandler(crear_tarea, pattern='^CREAR'),
                CallbackQueryHandler(editar_tarea, pattern='^EDITAR'),
                CallbackQueryHandler(eliminar_tarea, pattern='^ELIMINAR'),
                CallbackQueryHandler(completar_tarea, pattern='^COMPLETAR'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR')
            ],
            CREAR_TAREA1: [MessageHandler(Filters.text & ~Filters.command, elegir_fecha)],
            CREAR_TAREA2: [CallbackQueryHandler(elegir_fecha2)],
            CREAR_TAREA3: [CallbackQueryHandler(asignar_persona2)],
            CREAR_TAREA4: [CallbackQueryHandler(end_creacion, pattern='^NO$'),
                           CallbackQueryHandler(asignar_persona2)],
            FINAL_OPTION: [
                CallbackQueryHandler(tareas, pattern='^CONTINUAR$'),
                CallbackQueryHandler(editar_tarea, pattern='^CONTINUAR_EDITAR$'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
        },
        fallbacks=[CommandHandler('tareas', tareas)],
    )
    return conv_handler_tareas
