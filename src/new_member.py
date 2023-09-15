from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

import logging
import src.utilitys as ut
from utils import database as db
from decouple import config

from datetime import date, datetime
from telegram_bot_calendar import DetailedTelegramCalendar, DAY, YEAR

# Stages
ELEGIR_NOMBRE, ELEGIR_APELLIDO, ELEGIR_MOTE, ELEGIR_GENERO, ELEGIR_FECHA, ELEGIR_FECHA2, FINAL_OPTION = range(7)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logging.getLogger("new_member")

your_translation_months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                           "Octubre", "Noviembre", "Diciembre"]
your_translation_days_of_week = list('LMXJVSD')
PRUEBA = {'y': 'año', 'm': 'mes', 'd': 'dia'}


class MyTranslationCalendar(DetailedTelegramCalendar):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_of_week['es'] = your_translation_days_of_week
        self.months['es'] = your_translation_months
        self.first_step = YEAR
        self.max_date = date.today()
        self.locale = "es"
        self.current_date = datetime.strptime("01/01/2000", '%d/%m/%Y').date()

    empty_nav_button = "❌"
    middle_button_day = "{month}"
    prev_button = "⏪"
    next_button = "⏩"


def start(update: Update, context: CallbackContext):

    ut.set_actual_user(update.effective_user.id, context)
    data = db.select("data")
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    user_id = int(update.effective_user.id)
    chat_id = int(update.effective_chat.id)

    ut.set_actual_user(update.effective_user.id, context)
    nombre = update.effective_user.first_name
    fila = data.loc[data.id == user_id]
    if len(fila) == 1:
        fila = fila.iloc[0]
        logger.info(f"{update.effective_chat.type} -> {fila.apodo} ha iniciado el bot")
    else:
        logger.info(
            f"{update.effective_chat.type} -> {nombre} con id: {user_id} ha iniciado el bot sin estar en el grupo")
        context.bot.sendMessage(chat_id, "Lo siento, pero no perteneces al grupo de Manitoba")
        return
    context.user_data["oldMessage2"] = context.bot.sendMessage(update.effective_chat.id,
                                                               'Antes de empezar, necesito que me respondas un par de preguntas')
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, '¿Cuál es tu nombre?')
    return ELEGIR_NOMBRE


def elegir_apellidos(update: Update, context: CallbackContext):
    context.user_data["nombre"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id,
                                                              '¿Cuáles son tus apellidos? (ej. García Pérez)')
    return ELEGIR_APELLIDO


def elegir_mote(update: Update, context: CallbackContext):
    context.user_data["apellidos"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id,
                                                              '¿Cuáles es tu mote? Si no tienes, dime tu nombre')
    return ELEGIR_MOTE


def elegir_genero(update: Update, context: CallbackContext):
    context.user_data["mote"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    texto = f"¿Con que género te identifícas?"
    keyboard = [[InlineKeyboardButton("Femenino", callback_data="F"),
                 InlineKeyboardButton("Masculino", callback_data="M"),
                 InlineKeyboardButton("Otros", callback_data="X")]]

    context.bot.sendMessage(chat_id=update.effective_chat.id, text=texto,
                            reply_markup=InlineKeyboardMarkup(keyboard))
    return ELEGIR_GENERO


def elegir_fecha(update: Update, context: CallbackContext):
    context.user_data["genero"] = update.callback_query.data
    context.bot.deleteMessage(update.callback_query.message.chat_id, update.callback_query.message.message_id)
    calendar, step = MyTranslationCalendar().build()
    context.bot.sendMessage(update.effective_chat.id, parse_mode=f"HTML", reply_markup=calendar,
                            text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}")
    return ELEGIR_FECHA


def elegir_fecha2(update: Update, context: CallbackContext):
    result, key, step = MyTranslationCalendar().process(update.callback_query.data)
    if not result and key:
        context.bot.edit_message_text(parse_mode="HTML", text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}",
                                      chat_id=update.callback_query.message.chat_id,
                                      message_id=update.callback_query.message.message_id,
                                      reply_markup=key)
    elif result:
        context.bot.deleteMessage(update.effective_chat.id,
                                  update.callback_query.message.message_id)

        context.user_data["fecha"] = result.strftime("%d/%m")
        context.user_data["año"] = result.strftime("%Y")

        logger.warning(
            f"{update.effective_chat.type} -> {update.effective_user.first_name} ha elegido la fecha {result}")
        terminar(update, context)


def terminar(update: Update, context: CallbackContext):
    context.bot.deleteMessage(context.user_data["oldMessage2"].chat_id, context.user_data["oldMessage2"].message_id)
    db.update_data_start(update.effective_user.id, context.user_data["nombre"], context.user_data["apellidos"],
                         context.user_data["mote"], context.user_data["genero"], context.user_data["fecha"],
                         context.user_data["año"])

    context.bot.sendMessage(update.effective_chat.id, "Muchas gracias. Ya he actualizado tus datos")
    context.bot.sendMessage(update.effective_chat.id,
                            f"Bienvenido {context.user_data['mote']}\n"
                            f"Puedes probar a usar los comandos poniendo / seguido del nombre del comando")

    context.bot.sendMessage(update.effective_chat.id, "Los comandos son:\n"
                                                      "  ·listas - Crea, edita o borra una lista\n"
                                                      "  ·tareas - Crea, edita o borra una tarea\n"
                                                      "  ·loquendo - Envíame un texto y te reenvío un audio\n"
                                                      "  ·tesoreria - Comunicar gastos a la tesorera\n"
                                                      "  ·pietrobot -  Envíame un mensaje por privado y lo envío por el grupo anónimamente\n"
                                                      "  ·culos - Inserta la cara de alguien en un culo")
    return ConversationHandler.END


def new_member(update: Update, context: CallbackContext):
    member = update.message.new_chat_members[0]
    context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML",
                            text=f'Bienvenido al grupo {member.first_name}. '
                                 f'Necesito que pulses <a href="https://t.me/manitoba232bot">aquí</a> y le des a Iniciar')
    db.insert_data(member.id, member.first_name)


def left_member(update: Update, context: CallbackContext):
    member = update.message.left_chat_member
    db.delete("data", member.id)


def get_conv_handler_start():
    conv_handler_start = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ELEGIR_NOMBRE: [MessageHandler(Filters.text & ~Filters.command, elegir_apellidos)],
            ELEGIR_APELLIDO: [MessageHandler(Filters.text & ~Filters.command, elegir_mote)],
            ELEGIR_MOTE: [MessageHandler(Filters.text & ~Filters.command, elegir_genero)],
            ELEGIR_GENERO: [CallbackQueryHandler(elegir_fecha)],
            ELEGIR_FECHA: [CallbackQueryHandler(elegir_fecha2)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    return conv_handler_start
