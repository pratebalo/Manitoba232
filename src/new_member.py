from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters

import src.utilitys as ut
from utils import database as db
from decouple import config
from utils import logger_config
from datetime import date, datetime
from telegram_bot_calendar import DetailedTelegramCalendar, YEAR

# Stages
SELECT_NAME, SELECT_SURNAME, SELECT_NICK, SELECT_GENDER, SELECT_DATE, SELECT_DATE2, FINAL_OPTION = range(7)

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
        self.first_step = YEAR
        self.max_date = date.today()
        self.locale = "es"
        self.current_date = datetime.strptime("01/01/2000", '%d/%m/%Y').date()

    empty_nav_button = "❌"
    middle_button_day = "{month}"
    prev_button = "⏪"
    next_button = "⏩"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    data = db.select("data")
    await update.message.delete()
    user_id = int(update.effective_user.id)

    ut.set_actual_user(update.effective_user.id, context)
    name = update.effective_user.first_name
    row = data.loc[data.id == user_id]
    if len(row) == 1:
        row = row.iloc[0]
        logger.info(f"{row.apodo} ha iniciado el bot")
    else:
        logger.info(f"{name if name else 'Alguien'} con id: {user_id} ha iniciado el bot sin estar en el grupo")
        await update.effective_chat.send_message("Lo siento, pero no perteneces al grupo de Manitoba")
        return
    context.user_data["oldMessage2"] = await update.effective_chat.send_message('Antes de empezar, necesito que me respondas un par de preguntas')
    context.user_data["oldMessage"] = await update.effective_chat.send_message('¿Cuál es tu nombre?')
    return SELECT_NAME


async def select_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    context.user_data["oldMessage"] = await update.effective_chat.send_message('¿Cuáles son tus apellidos? (ej. García Pérez)')
    return SELECT_SURNAME


async def select_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["surname"] = update.message.text
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    context.user_data["oldMessage"] = await update.effective_chat.send_message('¿Cuáles es tu mote? Si no tienes, dime tu nombre')
    return SELECT_NICK


async def select_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    texto = f"¿Con que género te identifícas?"
    keyboard = [[InlineKeyboardButton("Femenino", callback_data="F"),
                 InlineKeyboardButton("Masculino", callback_data="M"),
                 InlineKeyboardButton("Otros", callback_data="X")]]

    await update.effective_chat.send_message(text=texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_GENDER


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gender"] = update.callback_query.data
    await update.callback_query.delete_message()
    calendar, step = MyTranslationCalendar().build()
    await update.effective_chat.send_message(parse_mode=f"HTML", reply_markup=calendar, text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}")
    return SELECT_DATE


async def select_date2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result, key, step = MyTranslationCalendar().process(update.callback_query.data)
    if not result and key:
        await context.bot.edit_message_text(parse_mode="HTML", text=f"<b>Introduce tu cumpleaños</b>\nElige {PRUEBA[step]}",
                                            chat_id=update.callback_query.message.chat_id,
                                            message_id=update.callback_query.message.message_id,
                                            reply_markup=key)
    elif result:
        await update.callback_query.delete_message()

        context.user_data["date"] = result.strftime("%d/%m")
        context.user_data["year"] = result.strftime("%Y")

        logger.warning(f"{update.effective_user.first_name} ha elegido la fecha {result}")
        await terminar(update, context)


async def terminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.user_data["oldMessage2"].delete()
    db.update_fields_table(table="data", idx=update.effective_user.id, nombre=context.user_data["name"], apellidos=context.user_data["surname"],
                           apodo=context.user_data["nick"], genero=context.user_data["gender"], cumple=context.user_data["date"],
                           cumple_ano=context.user_data["year"])

    await update.effective_chat.send_message("Muchas gracias. Ya he actualizado tus datos")
    await update.effective_chat.send_message(
        f"Bienvenido {context.user_data['nick']}\nPuedes probar a usar los comandos poniendo / seguido del nombre del comando")

    await update.effective_chat.send_message(f"Los comandos son:\n{commands_to_list(context.bot.commands)}")
    return ConversationHandler.END


async def new_member(update: Update, _: ContextTypes.DEFAULT_TYPE):
    member = update.message.new_chat_members[0]
    await update.effective_chat.send_message(parse_mode="HTML",
                                             text=f'Bienvenido al grupo {member.first_name if member.first_name else ""}.'
                                                  f'Necesito que pulses <a href="https://t.me/manitoba232bot">aquí</a> y le des a Iniciar')
    db.insert_data(member.id, member.first_name)


async def left_member(update: Update, _: ContextTypes.DEFAULT_TYPE):
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
            SELECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_surname)],
            SELECT_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_nick)],
            SELECT_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_gender)],
            SELECT_GENDER: [CallbackQueryHandler(select_date)],
            SELECT_DATE: [CallbackQueryHandler(select_date2)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    return conv_handler_start
