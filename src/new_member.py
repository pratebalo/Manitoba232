from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

import logging
import src.utilitys as ut
from utils import database as db
from decouple import config

from datetime import date, datetime
from telegram_bot_calendar import DetailedTelegramCalendar, YEAR

# Stages
SELECT_NAME, SELECT_SURNAME, SELECT_NICK, SELECT_GENDER, SELECT_DATE, SELECT_DATE2, FINAL_OPTION = range(7)

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
    name = update.effective_user.first_name
    row = data.loc[data.id == user_id]
    if len(row) == 1:
        row = row.iloc[0]
        logger.info(f"{update.effective_chat.type} -> {row.apodo} ha iniciado el bot")
    else:
        logger.info(f"{update.effective_chat.type} -> {name if name else 'Alguien'} con id: {user_id} ha iniciado el bot sin estar en el grupo")
        context.bot.sendMessage(chat_id, "Lo siento, pero no perteneces al grupo de Manitoba")
        return
    context.user_data["oldMessage2"] = context.bot.sendMessage(update.effective_chat.id, 'Antes de empezar, necesito que me respondas un par de preguntas')
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, '¿Cuál es tu nombre?')
    return SELECT_NAME


def select_surname(update: Update, context: CallbackContext):
    context.user_data["name"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, '¿Cuáles son tus apellidos? (ej. García Pérez)')
    return SELECT_SURNAME


def select_nick(update: Update, context: CallbackContext):
    context.user_data["surname"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, '¿Cuáles es tu mote? Si no tienes, dime tu nombre')
    return SELECT_NICK


def select_gender(update: Update, context: CallbackContext):
    context.user_data["nick"] = update.message.text
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    texto = f"¿Con que género te identifícas?"
    keyboard = [[InlineKeyboardButton("Femenino", callback_data="F"),
                 InlineKeyboardButton("Masculino", callback_data="M"),
                 InlineKeyboardButton("Otros", callback_data="X")]]

    context.bot.sendMessage(chat_id=update.effective_chat.id, text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_GENDER


def select_date(update: Update, context: CallbackContext):
    context.user_data["gender"] = update.callback_query.data
    context.bot.deleteMessage(update.callback_query.message.chat_id, update.callback_query.message.message_id)
    calendar, step = MyTranslationCalendar().build()
    context.bot.sendMessage(update.effective_chat.id, parse_mode=f"HTML", reply_markup=calendar, text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}")
    return SELECT_DATE


def select_date2(update: Update, context: CallbackContext):
    result, key, step = MyTranslationCalendar().process(update.callback_query.data)
    if not result and key:
        context.bot.edit_message_text(parse_mode="HTML", text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}",
                                      chat_id=update.callback_query.message.chat_id,
                                      message_id=update.callback_query.message.message_id,
                                      reply_markup=key)
    elif result:
        context.bot.deleteMessage(update.effective_chat.id,
                                  update.callback_query.message.message_id)

        context.user_data["date"] = result.strftime("%d/%m")
        context.user_data["year"] = result.strftime("%Y")

        logger.warning(
            f"{update.effective_chat.type} -> {update.effective_user.first_name} ha elegido la fecha {result}")
        terminar(update, context)


def terminar(update: Update, context: CallbackContext):
    context.bot.deleteMessage(context.user_data["oldMessage2"].chat_id, context.user_data["oldMessage2"].message_id)
    # db.update_data_start(update.effective_user.id, context.user_data["name"], context.user_data["surname"], context.user_data["nick"],
    #                      context.user_data["gender"], context.user_data["date"], context.user_data["year"])

    context.bot.sendMessage(update.effective_chat.id, "Muchas gracias. Ya he actualizado tus datos")
    context.bot.sendMessage(update.effective_chat.id,
                            f"Bienvenido {context.user_data['nick']}\nPuedes probar a usar los comandos poniendo / seguido del nombre del comando")

    context.bot.sendMessage(update.effective_chat.id, f"Los comandos son:\n{commands_to_list(context.bot.commands)}")
    return ConversationHandler.END


def new_member(update: Update, context: CallbackContext):
    member = update.message.new_chat_members[0]
    context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML",
                            text=f'Bienvenido al grupo {member.first_name if member.first_name else ""}.'
                                 f'Necesito que pulses <a href="https://t.me/manitoba232bot">aquí</a> y le des a Iniciar')
    db.insert_data(member.id, member.first_name)


def left_member(update: Update, context: CallbackContext):
    member = update.message.left_chat_member
    db.delete("data", member.id)


def commands_to_list(commands):
    text = ""
    for command in commands:
        text += f" ·/{command.command} - {command.description}\n"
    return text


def get_conv_handler_start():
    conv_handler_start = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_NAME: [MessageHandler(Filters.text & ~Filters.command, select_surname)],
            SELECT_SURNAME: [MessageHandler(Filters.text & ~Filters.command, select_nick)],
            SELECT_NICK: [MessageHandler(Filters.text & ~Filters.command, select_gender)],
            SELECT_GENDER: [CallbackQueryHandler(select_date)],
            SELECT_DATE: [CallbackQueryHandler(select_date2)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    return conv_handler_start
