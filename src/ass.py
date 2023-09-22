from utils import logger_config
import requests
import src.utilitys as ut
from decouple import config
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

from PIL import Image, ImageDraw
from random import randrange
from io import BytesIO

STAGE1, STAGE2 = range(2)

ID_MANITOBA = int(config("ID_MANITOBA"))

logger = logger_config.logger


def ass(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.deleteMessage(chat_id, update.message.message_id)
    if chat_id == ID_MANITOBA:
        context.bot.sendMessage(chat_id=update.effective_user.id, text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /pietrobot")
        return

    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_chat.type} -> User {context.user_data['user'].apodo} entro en el comando culos")

    context.user_data["oldMessage"] = context.bot.sendMessage(chat_id, f"Enviame una imagen cuadrada de una cara sin bordes")

    return STAGE1


def ass2(update: Update, context: CallbackContext):
    size_list = [(160, 160), (90, 90), (140, 140)]
    point_list = [(345, 480), (427, 333), (462, 248)]
    photo_list = ['images/mono.jpg', 'images/perro.jpg', 'images/mono2.jpg']
    n = randrange(len(size_list))
    im1 = Image.open(photo_list[n])
    url = context.bot.get_file(file_id=update.message.photo[-1].file_id).file_path
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

    chat_id = update.message.chat_id
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} mando la foto")

    context.bot.deleteMessage(chat_id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(chat_id, update.message.message_id)
    context.bot.sendPhoto(chat_id, photo=open("photo_final.jpg", "rb"))

    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('culos', ass)],
        states={
            STAGE1: [MessageHandler(Filters.photo & ~Filters.command, ass2)]

        },
        fallbacks=[CommandHandler('culos', ass)],
    )
