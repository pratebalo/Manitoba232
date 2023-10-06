from utils import logger_config
import src.utilitys as ut

from decouple import config
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters
from gtts import gTTS

LOQUENDO_1, LOQUENDO_2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logger_config.logger


async def loquendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    if update.effective_chat.id == ID_MANITOBA:
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /loquendo")
        return ConversationHandler.END
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"User {context.user_data['user'].apodo} entro en el comando loquendo")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CANCELAR", callback_data=f"CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message(f"¿Qué texto quieres convertir?", reply_markup=reply_markup)
    return LOQUENDO_1


async def loquendo2(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    keyboard.append([InlineKeyboardButton("CANCELAR", callback_data=f"CANCEL")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.warning(f"User {context.user_data['user'].apodo} mando el texto:\n {update.message.text}")

    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    context.user_data["oldMessage"] = await update.effective_chat.send_message(text=f"¿Qué idioma quieres poner?", reply_markup=reply_markup)
    context.user_data["texto"] = update.message.text

    return LOQUENDO_2


async def end_loquendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"User {context.user_data['user'].apodo} mando el idioma: {update.callback_query.data}")

    await context.user_data["oldMessage"].delete()
    tts = gTTS(context.user_data["texto"], lang=update.callback_query.data)
    file_name = "Mensajito de Baden Powell.mp3"
    tts.save(file_name)
    await update.effective_chat.send_audio(audio=open(file_name, "rb"))

    return ConversationHandler.END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando loquendo")
    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('loquendo', loquendo)],
        states={
            LOQUENDO_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, loquendo2),
                         CallbackQueryHandler(end, pattern='^CANCEL')],
            LOQUENDO_2: [CallbackQueryHandler(end, pattern='^CANCEL$'),
                         CallbackQueryHandler(end_loquendo)]

        },
        fallbacks=[CommandHandler('loquendo', loquendo)],
    )
