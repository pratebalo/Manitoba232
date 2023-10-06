from utils import logger_config
import src.utilitys as ut

from decouple import config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters
from gtts import gTTS

LOQUENDO_1, LOQUENDO_2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger


def loquendo(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_chat.type} -> User {context.user_data['user'].apodo} entro en el comando loquendo")

    context.bot.deleteMessage(chat_id, update.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(chat_id, f"¿Qué texto quieres convertir?")
    return LOQUENDO_1


def loquendo2(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    idi = ['af', 'ar', 'bn', 'bs', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'eo', 'es', 'et', 'fi', 'fr', 'gu',
           'hi', 'hr', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jw', 'km', 'kn', 'ko', 'la', 'lv', 'mk', 'ml', 'mr',
           'my', 'ne', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'si', 'sk', 'sq', 'sr', 'su', 'sv', 'sw', 'ta', 'te',
           'th', 'tl', 'tr', 'uk', 'ur', 'vi']
    languages = ['Afrikaans', 'Arabic', 'Bengali', 'Bosnian', 'Catalan', 'Czech', 'Welsh', 'Danish', 'German', 'Greek',
                 'English', 'Esperanto', 'Spanish', 'Estonian', 'Finnish', 'French', 'Gujarati', 'Hindi', 'Croatian',
                 'Hungarian', 'Armenian', 'Indonesian', 'Icelandic', 'Italian', 'Japanese', 'Javanese', 'Khmer',
                 'Kannada', 'Korean', 'Latin', 'Latvian', 'Macedonian', 'Malayalam', 'Marathi', 'Myanmar', 'Nepali',
                 'Dutch', 'Norwegian', 'Polish', 'Portuguese', 'Romanian', 'Russian', 'Sinhala', 'Slovak', 'Albanian',
                 'Serbian', 'Sundanese', 'Swedish', 'Swahili', 'Tamil', 'Telugu', 'Thai', 'Filipino', 'Turkish',
                 'Ukrainian', 'Urdu', 'Vietnamese']
    part_keyboard = []
    keyboard = []
    for i, (lang, lg) in enumerate(zip(languages, idi)):
        part_keyboard.append(InlineKeyboardButton(lang, callback_data=lg))
        if i % 3 == 2 or i == len(languages):
            keyboard.append(part_keyboard)
            part_keyboard = []

    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.warning(f"{update.effective_chat.type} -> User {context.user_data['user'].apodo} mando el texto:\n {update.message.text}")

    context.bot.deleteMessage(context.user_data["oldMessage"].chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(chat_id, text=f"¿Qué idioma quieres poner?", reply_markup=reply_markup)
    context.user_data["texto"] = update.message.text

    return LOQUENDO_2


def end_loquendo(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id
    logger.warning(f"{update.effective_chat.type} -> User {context.user_data['user'].apodo} mando el idioma:\n {update.callback_query.data}")

    context.bot.deleteMessage(chat_id, context.user_data["oldMessage"].message_id)
    tts = gTTS(context.user_data["texto"], lang=update.callback_query.data)
    file_name = "Mensajito de Baden Powell.mp3"
    tts.save(file_name)
    context.bot.sendAudio(chat_id, timeout=60, audio=open(file_name, "rb"))

    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('loquendo', loquendo)],
        states={
            LOQUENDO_1: [MessageHandler(Filters.text & ~Filters.command, loquendo2)],
            LOQUENDO_2: [CallbackQueryHandler(end_loquendo)]

        },
        fallbacks=[CommandHandler('loquendo', loquendo)],
    )
