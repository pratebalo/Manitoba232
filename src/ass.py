from utils.logger_config import logger
import requests
import src.utilitys as ut
from decouple import config
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ConversationHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from PIL import Image, ImageDraw
from random import randrange
from io import BytesIO

STAGE1, STAGE2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))


async def ass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    await update.message.delete()
    if effective_chat.id == ID_MANITOBA:
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /culos")
        return ConversationHandler.END

    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"User {context.user_data['user'].apodo} entro en el comando culos")

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CANCELAR", callback_data=f"CANCEL")]])
    context.user_data["oldMessage"] = await effective_chat.send_message(f"Enviame una imagen cuadrada de una cara sin bordes", reply_markup=reply_markup)

    return STAGE1


async def ass2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    size_list = [(160, 160), (90, 90), (140, 140)]
    point_list = [(345, 480), (427, 333), (462, 248)]
    photo_list = ['images/mono.jpg', 'images/perro.jpg', 'images/mono2.jpg']
    n = randrange(len(size_list))
    im1 = Image.open(photo_list[n])
    file = await update.message.photo[-1].get_file()
    url = file.file_path
    response = requests.get(url)
    im2 = Image.open(BytesIO(response.content))
    size = size_list[n]
    im2.thumbnail(size, Image.ANTIALIAS)
    x, y = im2.size
    e_x, e_y = size[0] * 3 / 5, size[0] * 13 / 15
    bbox = (x / 2 - e_x / 2, y / 2 - e_y / 2, x / 2 + e_x / 2, y / 2 + e_y / 2)

    mask_im = Image.new("L", im2.size, 0)
    draw = ImageDraw.Draw(mask_im)
    draw.ellipse(bbox, fill=255)
    back_im = im1.copy()
    back_im.paste(im2, (point_list[n][0] - int(x / 2), point_list[n][1] - int(y / 2)), mask_im)
    back_im.save('photo_final.jpg', quality=95)

    logger.warning(f"{context.user_data['user'].apodo} mando la foto")

    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    await context.bot.sendPhoto(ID_MANITOBA, photo=open("photo_final.jpg", "rb"))

    return ConversationHandler.END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando culos")
    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('culos', ass)],
        states={
            STAGE1: [MessageHandler(filters.PHOTO & ~filters.COMMAND, ass2),
                     CallbackQueryHandler(end, pattern='^CANCEL')]

        },
        fallbacks=[CommandHandler('culos', ass)],
    )
