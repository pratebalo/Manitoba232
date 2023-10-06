from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters
from utils import database as db
from decouple import config
from datetime import date
from telegram_bot_calendar import DetailedTelegramCalendar, DAY

import pandas as pd
from utils import logger_config
import random
import src.utilitys as ut

# Stages
ELEGIR_TAREA, CREAR_TAREA1, CREAR_TAREA2, CREAR_TAREA3, CREAR_TAREA4, CREAR_TAREA5, FINAL_OPTION = range(7)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger

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


async def recordar_tareas(context: ContextTypes.DEFAULT_TYPE):
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
                await context.bot.sendMessage(chat_id=persona, parse_mode="HTML", text=text)


async def tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.message:
        context.user_data["ediciones"] = []
        await update.message.delete()
    else:
        await update.callback_query.delete_message()
    user = update.effective_user
    context.user_data["creador_tarea"] = user["id"]
    logger.warning(f"{user.first_name} entro en el comando tareas")
    all_tareas = db.select("tareas")
    data = db.select("data")
    context.user_data["data"] = data
    context.user_data["all_tareas"] = all_tareas
    text = f"¿Qué quieres hacer?\n"
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
    keyboard.append([InlineKeyboardButton("Terminar", callback_data="END")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    context.user_data["personas_asignadas"] = []
    return ELEGIR_TAREA


async def ver_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_tareas = context.user_data["all_tareas"]
    data = context.user_data["data"]
    pos_tarea = int(update.callback_query.data.replace("VER", ""))
    tarea = all_tareas.iloc[pos_tarea]
    logger.warning(
        f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó ver la tarea '{tarea.descripcion}'")
    texto = f"Has solicitado ver la tarea:\n" + tarea_to_text(tarea, data)

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("END"))]]

    await update.callback_query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


async def crear_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["oldMessage"] = await update.callback_query.edit_message_text(parse_mode="HTML", text="<b>Creando tarea</b>\nIntroduce la descripción")
    logger.warning(f"{context.user_data['user'].apodo} ha seleccionado crear tarea")
    return CREAR_TAREA1


async def elegir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} ha introducido la descripcion: {update.message.text}")
    context.user_data["descripcion"] = update.message.text
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    calendar, step = MyTranslationCalendar().build()
    await update.effective_chat.send_message(parse_mode=f"HTML", reply_markup=calendar,
                                             text=f"<b>Creando tarea</b>\nElige {PRUEBA[step]}")
    return CREAR_TAREA2


async def elegir_fecha2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result, key, step = MyTranslationCalendar().process(update.callback_query.data)
    if not result and key:
        await context.bot.edit_message_text(parse_mode="HTML", text=f"<b>Creando tarea</b>\nElige {PRUEBA[step]}",
                                            chat_id=update.callback_query.message.chat_id,
                                            message_id=update.callback_query.message.message_id,
                                            reply_markup=key)
    elif result:
        await update.callback_query.delete_message()
        result = result.strftime("%d/%m/%Y")
        context.user_data["fecha"] = result

        logger.warning(f"{context.user_data['user'].apodo} ha elegido la fecha {result}")
        keyboard = []
        part_keyboard = []
        data = context.user_data["data"]
        for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
            part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
            if i % 3 == 2 or i == len(data) - 1:
                keyboard.append(part_keyboard)
                part_keyboard = []

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_chat.send_message(parse_mode="HTML", reply_markup=reply_markup,
                                                 text="<b>Creando tarea</b>\n¿A qúe persona quieres asignarla?")

        return CREAR_TAREA3


async def asignar_persona2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["personas_asignadas"].append(int(query.data))
    keyboard = []
    part_keyboard = []
    data = context.user_data["data"]
    for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
        if persona.id not in context.user_data["personas_asignadas"]:
            part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
        if i % 3 == 2 or i == len(data) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []
    keyboard.append([InlineKeyboardButton("NO", callback_data="NO")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(parse_mode="HTML", reply_markup=reply_markup,
                                  text="<b>Creando tarea</b>\nPersona asignada. ¿Quieres asignarla a alguien más?")
    logger.warning(f"{context.user_data['user'].apodo} ha asignado a {query.data} a la tarea")
    return CREAR_TAREA4


async def end_creacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    data = context.user_data["data"]
    tarea = pd.Series(
        {"descripcion": context.user_data["descripcion"], "personas": context.user_data["personas_asignadas"],
         "fecha": context.user_data["fecha"], "creador": context.user_data["creador_tarea"]})

    texto = f"""{context.user_data['user'].apodo} ha creado la tarea:\n""" + tarea_to_text(tarea, data)

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
            await context.bot.sendMessage(persona.id, parse_mode="HTML",
                                          text="Se te ha asignado la siguiente tarea:\n" + texto)
        except:
            await context.bot.sendMessage(ID_MANITOBA, text=f"{persona.apodo} no me tiene activado")
            await context.bot.sendSticker(ID_MANITOBA, sticker=sticker[random.randint(0, len(sticker) - 1)])
    logger.warning(f"Se ha creado la tarea {tarea.descripcion}")

    keyboard = [[InlineKeyboardButton("Continuar", callback_data="CONTINUAR"),
                 InlineKeyboardButton("Terminar", callback_data="END")]]

    await update.effective_chat.send_message(parse_mode="HTML", text=texto,
                                             reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


async def editar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show new choice of buttons"""
    query = update.callback_query

    data = context.user_data["data"]
    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("EDITAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    texto = f"{context.user_data['user'].apodo} ha editado la tarea \n<b>{tarea_to_text(tarea, data)}</b>"
    keyboard = [[InlineKeyboardButton("Continuar", callback_data="CONTINUAR"),
                 InlineKeyboardButton("Terminar", callback_data="END")]]

    await update.callback_query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


async def eliminar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("ELIMINAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    db.delete("tareas", tarea.id)
    data = context.user_data["data"]
    logger.warning(f"{context.user_data['user'].apodo}  ha eliminado la tarea \n{tarea_to_text(tarea, data)}")
    texto = f"{context.user_data['user'].apodo} ha eliminado la tarea \n<b>{tarea_to_text(tarea, data)}</b>"

    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("END"))]]

    await query.edit_message_text(parse_mode="HTML", text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["ediciones"].append("\n" + texto)
    return FINAL_OPTION


async def completar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    all_tareas = context.user_data["all_tareas"]
    pos_tarea = int(query.data.replace("COMPLETAR", ""))
    tarea = all_tareas.iloc[pos_tarea]
    tarea.completada = True
    db.update_tarea(tarea)
    data = context.user_data["data"]
    logger.warning(f"{context.user_data['user'].apodo}  ha completado la tarea \n{tarea_to_text(tarea, data)}")
    texto = f"<a href='tg://user?id={update.effective_user.id}'>{context.user_data['user'].apodo}</a> " \
            f"ha completado la tarea!!!!!! \n<b>{tarea_to_text(tarea, data)}</b>"

    await query.delete_message()
    if context.user_data["ediciones"]:
        await context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML",
                                      text="\n".join(context.user_data["ediciones"]))
    await context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=texto)
    stickers = ["CAACAgIAAxkBAAICXmAasBQ2GrCJTRmfjzDArpTLXfVtAAJJAQACVp29CnVtIjfXzilUHgQ",
                "CAACAgIAAxkBAAICX2AasB6gnf_gqA3c8s00wW3AFj5QAAJNAANZu_wlKIGgbd0bgvceBA",
                "CAACAgIAAxkBAAICYGAasCfRVfZcMOVWzZiuX2pFuZC7AAJXAAPBnGAMxgL9s1SbpjQeBA",
                "CAACAgIAAxkBAAICYWAasDPbxJKIINhcFeiQsiYvVEGpAAJjAANOXNIpRcBzCXnlr_AeBA"]
    await context.bot.sendSticker(ID_MANITOBA, sticker=random.choice(stickers))
    return ConversationHandler.END


def tarea_to_text(tarea, data):
    text = f"-<b>{tarea.descripcion}</b>:\n" \
           f"-<b>{tarea.fecha}</b>\n"
    personas = data[data.id.isin(tarea.personas)]
    for _, persona in personas.iterrows():
        text += f"  +{persona.apodo}\n"
    return text


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido de tareas")
    if context.user_data["ediciones"]:
        await context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML",
                                      text="\n".join(context.user_data["ediciones"]))
    return ConversationHandler.END


def get_conv_handler():
    conv_handler_tareas = ConversationHandler(
        entry_points=[CommandHandler('tareas', tareas)],
        states={
            ELEGIR_TAREA: [
                CallbackQueryHandler(ver_tarea, pattern='^VER'),
                CallbackQueryHandler(crear_tarea, pattern='^CREAR'),
                CallbackQueryHandler(editar_tarea, pattern='^EDITAR'),
                CallbackQueryHandler(eliminar_tarea, pattern='^ELIMINAR'),
                CallbackQueryHandler(completar_tarea, pattern='^COMPLETAR'),
                CallbackQueryHandler(end, pattern='^END')
            ],
            CREAR_TAREA1: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_fecha)],
            CREAR_TAREA2: [CallbackQueryHandler(elegir_fecha2)],
            CREAR_TAREA3: [CallbackQueryHandler(asignar_persona2)],
            CREAR_TAREA4: [CallbackQueryHandler(end_creacion, pattern='^NO$'),
                           CallbackQueryHandler(asignar_persona2)],
            FINAL_OPTION: [
                CallbackQueryHandler(tareas, pattern='^CONTINUAR$'),
                CallbackQueryHandler(editar_tarea, pattern='^CONTINUAR_EDITAR$'),
                CallbackQueryHandler(end, pattern='^TERMINAR$')],
        },
        fallbacks=[CommandHandler('tareas', tareas)],
    )
    return conv_handler_tareas
