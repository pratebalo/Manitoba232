from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters

from datetime import datetime
from gtts import gTTS
import pandas as pd
import src.utilitys as ut
from utils import database as db
import random
from decouple import config

CUMPLE1, CUMPLE2, CUMPLE3, CUMPLE4 = range(4)
ID_MANITOBA = int(config("ID_MANITOBA"))
STICKERS = ["CAACAgIAAxkBAAEDfgNhugP6zcKUVHjHDThT6UFcw7Ex7AACPQEAAiI3jgRzp-LtkvRpKCME",
            "CAACAgIAAxkBAAEDfgVhugQphnj0lZMlP6wgXvp7tVp4ogACCwEAAvcCyA_F9DuYlapx2yME",
            "CAACAgIAAxkBAAEDfgdhugQt8geB2KWFbDQ0TA2IXbx7ZQACNQADO2AkFOi0JbQQZiMhIwQ",
            "CAACAgIAAxkBAAEDfghhugQuCg9Bnus-lr1f-cdt2bYsBAACWQADrWW8FPS7RxeJ4S0JIwQ",
            "CAACAgIAAxkBAAEDfgthugQyW3f6sBqc9cq-rBhArU-16gACAQwAArbpmEtKWijuVpAoPiME",
            "CAACAgIAAxkBAAEDfg1hugQ1DdHic0OmMnwBfIhq7Ab8ZgACiQADFkJrCkbL2losgrCOIwQ",
            "CAACAgIAAxkBAAEDfg9hugQ4Tv9ioGb0Wo6tUyjZZbEB3AAC8AIAArVx2ga4Ryudl_pd6CME"]


async def birthday(context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")
    date = datetime.today().strftime('%d/%m')
    data_birth = data[data.cumple == date]

    for _, person in data_birth.iterrows():
        # tts = gTTS(cumpleanero.cumple_song, lang=cumpleanero.cumple_lang)
        # tts.save(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3")

        await context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=f"Felicidades <b>{person.apodo}</b>!!!!!")
        await context.bot.sendSticker(chat_id=ID_MANITOBA, sticker=STICKERS[random.randint(0, len(STICKERS) - 1)])
        # context.bot.sendAudio(chat_id=ID_MANITOBA, audio=open(f"Felicitacion de su majestad para {cumpleanero.apodo}.mp3", "rb"))
        if person.genero == "F":
            await context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=f"Por seeeeerrrr tan bueeeennaa muchaaaaachaaaaa 🎉🎊🎈")
        elif person.genero == "M":
            await context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=f"Por seeeeerrrr tan bueeeenn muchaaaaachaooooo 🎉🎊🎈")
        else:
            await context.bot.sendMessage(chat_id=ID_MANITOBA, parse_mode="HTML", text=f"Por seeeeerrrr tan bueeeenn muchaaaaacheeee 🎉🎊🎈")


async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

    ut.set_actual_user(update.effective_user.id, context)
    data = db.select("data")
    year = datetime.now().year
    data.cumple = pd.to_datetime(data.cumple, format='%d/%m').apply(lambda dt: dt.replace(year=year))

    a = data[data.cumple > datetime.today()].sort_values("cumple")[0:4]
    text = ""
    for _, person in a.iterrows():
        text += f"{person.nombre} {person.apellidos}  | {person.cumple.strftime('%d/%m')}/{str(person.cumple_ano)}\n"

    await update.effective_chat.send_message(text)


async def get_all_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    await update.message.delete()
    data = db.select("data")
    year = datetime.now().year
    data.cumple = pd.to_datetime(data.cumple, format='%d/%m').apply(lambda dt: dt.replace(year=year))

    a = data.sort_values("cumple")
    text = ""
    for _, persona in a.iterrows():
        if pd.isna(persona.cumple):
            text += f"{persona.nombre} {persona.apellidos}  | N/A\n"
        else:
            text += f"{persona.nombre} {persona.apellidos}  | {persona.cumple.strftime('%d/%m')}/{str(int(persona.cumple_ano))}\n"

    await update.effective_chat.send_message(text)


async def set_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")

    ut.set_actual_user(update.effective_user.id, context)
    await update.message.delete()
    keyboard = []
    part_keyboard = []
    for i, person in data.sort_values(by="apodo", ignore_index=True).iterrows():
        part_keyboard.append(InlineKeyboardButton(person.apodo, callback_data=str(person.id)))
        if i % 3 == 2 or i == len(data) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message("Elige", reply_markup=reply_markup)
    return CUMPLE1


async def set_birthday2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["personaId"] = update.callback_query.data
    context.user_data["oldMessage"] = await update.callback_query.edit_message_text(f"Cancion de cumpleaños")

    return CUMPLE2


async def set_birthday3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cancion"] = update.message.text
    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    context.user_data["oldMessage"] = await update.effective_chat.send_message("Idioma")

    return CUMPLE3


async def set_birthday4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["idioma"] = update.message.text
    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    context.user_data["oldMessage"] = await update.effective_chat.send_message("sticker")

    return CUMPLE4


async def set_birthday5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat

    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    tts = gTTS(context.user_data["cancion"], lang=context.user_data["idioma"])
    tts.save(f"Felicitacion de su majestad para {context.user_data['personaId']}.mp3")

    await effective_chat.send_message(parse_mode="HTML", text=f"Felicidades <b>{context.user_data['personaId']}</b>!!!!!")
    await effective_chat.send_sticker(sticker=update.message.sticker.file_id)
    await effective_chat.send_audio(audio=open(f"Felicitacion de su majestad para {context.user_data['personaId']}.mp3", "rb"))
    db.update_birth(context.user_data["personaId"], context.user_data["cancion"], context.user_data["idioma"], update.message.sticker.file_id)
    return ConversationHandler.END


def get_conv_handler():
    conv_handler_birthday = ConversationHandler(
        entry_points=[CommandHandler('setcumple', set_birthday)],
        states={
            CUMPLE1: [CallbackQueryHandler(set_birthday2)],
            CUMPLE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_birthday3)],
            CUMPLE3: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_birthday4)],
            CUMPLE4: [MessageHandler(filters.Sticker.ALL & ~filters.COMMAND, set_birthday5)],

        },
        fallbacks=[CommandHandler('setcumple', set_birthday)],
    )
    return conv_handler_birthday
