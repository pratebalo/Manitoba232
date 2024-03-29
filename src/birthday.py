from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    Filters
)
from datetime import datetime
from gtts import gTTS
import pandas as pd
from utils import database as db
import os

CUMPLE1, CUMPLE2, CUMPLE3, CUMPLE4 = range(4)
ID_MANITOBA = int(os.environ.get("ID_MANITOBA"))


def birthday(context: CallbackContext):
    data = db.select("data")
    fecha = datetime.today().strftime('%d/%m')
    cumpleaneros = data[data.cumple == fecha]
    for _, cumpleanero in cumpleaneros.iterrows():
        tts = gTTS(cumpleanero.cumple_song, lang=cumpleanero.cumple_lang)
        tts.save(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3")

        context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                text=f"Felicidades <b>{cumpleanero.apodo}</b>!!!!!")
        context.bot.sendSticker(chat_id=ID_MANITOBA,
                                sticker=cumpleanero.cumple_sticker)
        context.bot.sendAudio(chat_id=ID_MANITOBA,
                              audio=open(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3", "rb"))
        if cumpleanero.genero == "M":
            context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                    text=f"Por seeeeerrrr tan bueeeennaa muchaaaaachaaaaa 🎉🎊🎈")
        else:
            context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                    text=f"Por seeeeerrrr tan bueeeenn muchaaaaachaooooo 🎉🎊🎈")


def birthday2(update: Update, context: CallbackContext):
    data = db.select("data")
    fecha = datetime.today().strftime('%d/%m')
    cumpleaneros = data[data.cumple == fecha]
    for _, cumpleanero in cumpleaneros.iterrows():
        tts = gTTS(cumpleanero.cumple_song, lang=cumpleanero.cumple_lang)
        tts.save(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3")

        context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                text=f"Felicidades <b>{cumpleanero.apodo}</b>!!!!!")
        context.bot.sendSticker(chat_id=ID_MANITOBA,
                                sticker=cumpleanero.cumple_sticker)
        context.bot.sendAudio(chat_id=ID_MANITOBA,
                              audio=open(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3", "rb"))
        if cumpleanero.genero == "M":
            context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                    text=f"Por seeeeerrrr tan bueeeennaa muchaaaaachaaaaa 🎉🎊🎈")
        else:
            context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML",
                                    text=f"Por seeeeerrrr tan bueeeenn muchaaaaachaooooo 🎉🎊🎈")


def get_birthday(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.deleteMessage(chat_id, update.message.message_id)
    data = db.select("data")
    data.cumple = pd.to_datetime(data.cumple, format='%d/%m').apply(lambda dt: dt.replace(year=2021))

    a = data[data.cumple > datetime.today()].sort_values("cumple")[0:4]
    texto = ""
    for _, persona in a.iterrows():
        texto += persona.nombre_completo + " | " + persona.cumple.strftime('%d/%m') + "/" + str(persona.cumple_ano) + "\n"

    context.bot.sendMessage(chat_id, texto)


def set_birthday(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    data = db.select("data")
    context.bot.deleteMessage(chat_id, update.message.message_id)
    keyboard = []
    part_keyboard = []
    for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
        part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
        if i % 3 == 2 or i == len(data) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, "Elige", reply_markup=reply_markup)
    return CUMPLE1


def set_birthday2(update: Update, context: CallbackContext):
    context.user_data["personaId"] = update.callback_query.data
    context.user_data["oldMessage"] = update.callback_query.edit_message_text(f"Cancion de cumpleaños")

    return CUMPLE2


def set_birthday3(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.user_data["cancion"] = update.message.text
    context.bot.deleteMessage(chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(chat_id, update.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(chat_id, "idioma")

    return CUMPLE3


def set_birthday4(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.user_data["idioma"] = update.message.text
    context.bot.deleteMessage(chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(chat_id, update.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(chat_id, "sticker")

    return CUMPLE4


def set_birthday5(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.deleteMessage(chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(chat_id, update.message.message_id)
    tts = gTTS(context.user_data["cancion"], lang=context.user_data["idioma"])
    tts.save(f"Felicitacion de su majestad para {context.user_data['personaId']}.mp3")

    context.bot.sendMessage(chat_id=chat_id, parse_mode="HTML",
                            text=f"Felicidades <b>{context.user_data['personaId']}</b>!!!!!")
    context.bot.sendSticker(chat_id=chat_id,
                            sticker=update.message.sticker.file_id)
    context.bot.sendAudio(chat_id=chat_id,
                          audio=open(f"Felicitacion de su majestad para {context.user_data['personaId']}.mp3", "rb"))
    db.update_cumple(context.user_data["personaId"], context.user_data["cancion"], context.user_data["idioma"], update.message.sticker.file_id)
    return ConversationHandler.END


conv_handler_birthday = ConversationHandler(
    entry_points=[CommandHandler('setcumple', set_birthday)],
    states={
        CUMPLE1: [CallbackQueryHandler(set_birthday2)],
        CUMPLE2: [MessageHandler(Filters.text & ~Filters.command, set_birthday3)],
        CUMPLE3: [MessageHandler(Filters.text & ~Filters.command, set_birthday4)],
        CUMPLE4: [MessageHandler(Filters.sticker & ~Filters.command, set_birthday5)],

    },
    fallbacks=[CommandHandler('setcumple', set_birthday)],
)
