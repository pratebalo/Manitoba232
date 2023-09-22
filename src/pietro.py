from utils import logger_config
import src.utilitys as ut

from decouple import config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

STAGE1, STAGE2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger


def pietro_bot(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    context.bot.deleteMessage(chat_id, update.message.message_id)
    if update.effective_chat.id == ID_MANITOBA:
        context.bot.sendMessage(chat_id=update.effective_user.id, text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /pietrobot")
        return
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha entrado en pietrobot")
    if not chat_id == ID_MANITOBA:
        keyboard = [[InlineKeyboardButton("Me ha parecido oir que", callback_data="Me ha parecido oir que")],
                    [InlineKeyboardButton("Me ha dicho un pajarito que", callback_data="Me ha dicho un pajarito que")],
                    [InlineKeyboardButton("Se dice se comenta que", callback_data="Se dice se comenta que")]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.sendMessage(chat_id, text="¿Con qué texto quieres que empiece el mensaje?", reply_markup=reply_markup)
        return STAGE1
    else:
        return ConversationHandler.END


def pietro_bot2(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.user_data["start"] = update.callback_query.data
    context.bot.deleteMessage(chat_id, update.callback_query.message.message_id)

    context.bot.sendMessage(chat_id, text=f"¿Qué texto quieres enviar?\n{context.user_data['start']}...")
    return STAGE2


def end_pietro_bot(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha escrito {update.message.text}")
    context.bot.sendMessage(ID_MANITOBA, text=context.user_data["start"] + " " + update.message.text)
    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('pietrobot', pietro_bot)],
        states={
            STAGE1: [CallbackQueryHandler(pietro_bot2)],
            STAGE2: [MessageHandler(Filters.text & ~Filters.command, end_pietro_bot)],
        },
        fallbacks=[CommandHandler('pietrobot', pietro_bot)],

    )
