from utils import logger_config
import src.utilitys as ut

from decouple import config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters

STAGE1, STAGE2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger


async def pietro_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat

    await update.message.delete()
    if effective_chat.id == ID_MANITOBA:
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /pietrobot")
        return ConversationHandler.END
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_user.first_name} ha entrado en pietrobot")
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Me ha parecido oir que", callback_data="Me ha parecido oir que")],
         [InlineKeyboardButton("Me ha dicho un pajarito que", callback_data="Me ha dicho un pajarito que")],
         [InlineKeyboardButton("Se dice se comenta que", callback_data="Se dice se comenta que")],
         [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])

    await effective_chat.send_message(text="¿Con qué texto quieres que empiece el mensaje?", reply_markup=reply_markup)
    return STAGE1


async def pietro_bot2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["start"] = update.callback_query.data
    await update.callback_query.delete_message()

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CANCELAR", callback_data=f"CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message(text=f"¿Qué texto quieres enviar?\n{context.user_data['start']}...",
                                                                               reply_markup=reply_markup)
    return STAGE2


async def end_pietro_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{update.effective_user.first_name} ha escrito {update.message.text}")
    await context.user_data["oldMessage"].delete_message()
    await update.message.delete()
    await context.bot.sendMessage(ID_MANITOBA, text=context.user_data["start"] + " " + update.message.text)
    return ConversationHandler.END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando culos")
    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('pietrobot', pietro_bot)],
        states={
            STAGE1: [CallbackQueryHandler(end, pattern='CANCEL'),
                     CallbackQueryHandler(pietro_bot2)],
            STAGE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_pietro_bot),
                     CallbackQueryHandler(end, pattern='CANCEL')],
        },
        fallbacks=[CommandHandler('pietrobot', pietro_bot)],

    )
