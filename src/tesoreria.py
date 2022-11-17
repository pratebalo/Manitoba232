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
import logging
from utils import database as db
import re
import os

# Stages
OPCION, BOTE, BOTE2, PAGAR, FINAL_OPTION = range(5)
ID_MANITOBA = int(os.environ.get("ID_MANITOBA"))
ID_TESORERIA = int(os.environ.get("ID_TESORERIA"))
ID_ADMIN = int(os.environ.get("ID_ADMIN"))
logger = logging.getLogger("tesoreria")


def tesoreria(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} entro en el comando tesoreria")

    update.message.delete()
    text = f"<b>Tesoreria</b>\n{update.effective_user.first_name}: ¿Qué quieres hacer?\n"
    keyboard = [[InlineKeyboardButton("Meter dinero en el bote", callback_data="+")],
                [InlineKeyboardButton("Sacar dinero del bote", callback_data="-")],
                [InlineKeyboardButton("Comunicar un gasto", callback_data="GASTO")]]
    if update.effective_user.id == ID_TESORERIA or update.effective_user.id == ID_ADMIN:
        keyboard.append([InlineKeyboardButton("A PAGAR A PAGAR 🤑🤑", callback_data="PAGO")])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data="TERMINAR")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.sendMessage(update.effective_chat.id, text, parse_mode="HTML", reply_markup=reply_markup)
    return OPCION


def bote(update: Update, context: CallbackContext):
    context.user_data["tipo"] = update.callback_query.data
    context.user_data["oldMessage"] = update.callback_query.edit_message_text(
        f"{update.effective_user.first_name}: ¿Cuánto dinero?")

    return BOTE


def bote2(update: Update, context: CallbackContext):
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha enviado la cantidad {update.message.text}")
    context.user_data["cantidad"] = re.sub('[^\d.]', '', update.message.text.replace(",", "."))
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id,
                                                              f"{update.effective_user.first_name}: ¿Cúal es el motivo?")

    return BOTE2


def bote3(update: Update, context: CallbackContext):
    data = db.select("data")
    bote = db.select("botes")
    persona = data[data.id == update.effective_user.id].squeeze()
    logger.warning(
        f"{update.effective_chat.type} -> {update.effective_user.first_name} ha enviado el motivo {update.message.text}")
    if context.user_data["tipo"] == "GASTO":
        cantidad = float(context.user_data["cantidad"])
        db.insert_gastos(persona.id,
                         update.message.text,
                         cantidad,
                         datetime.today().strftime('%d/%m/%Y'),
                         persona.apodo)
        mensaje_tesorera = f"{persona.apodo} ha gastado {cantidad}€ en {update.message.text}"
        mensaje_usuario = f"Has metido el gasto de {cantidad}€ con el concepto '{update.message.text}'"
    else:
        cantidad = float(context.user_data["tipo"] + context.user_data["cantidad"])
        bote_actual = bote.iloc[-1].total + cantidad
        db.insert_bote(update.effective_user.id,
                       cantidad,
                       bote_actual,
                       update.message.text)
        if context.user_data["tipo"] == "+":
            mensaje_tesorera = f"{persona.apodo} ha metido {context.user_data['cantidad']}€ " \
                               f"en el bote con el concepto '{update.message.text}'.\nHay {bote_actual}€ en el bote"
        else:
            mensaje_tesorera = f"{persona.apodo} ha sacado {context.user_data['cantidad']}€ " \
                               f"del bote con el concepto '{update.message.text}'.\nHay {bote_actual}€ en el bote"
        mensaje_usuario = f"Bote actualizado.\nHay {bote_actual}€ en el bote"

    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    context.bot.sendMessage(update.effective_chat.id, mensaje_usuario)
    context.bot.sendMessage(ID_TESORERIA, mensaje_tesorera)

    return ConversationHandler.END


def pagar(update: Update, context: CallbackContext):
    gastos = db.select("gastos").sort_values(by=["pagado", "id_persona"], ignore_index=True)

    keyboard = []
    texto = f"A soltar el dinero polssssss 💰💶💵💷💸\n"
    for i, gasto in gastos.iterrows():
        keyboardline = []
        texto += f" {i + 1}. {gasto.nombre_persona}({gasto.fecha.strftime('%d/%m')}) {gasto.cantidad}€ -> {gasto.motivo}\n"
        keyboardline.append(InlineKeyboardButton(i + 1, callback_data="NADA"))
        if gasto.pagado:
            keyboardline.append(InlineKeyboardButton("🧾", callback_data="NADA"))
        else:
            keyboardline.append(InlineKeyboardButton("💰", callback_data="PAGAR" + str(gasto.id)))
        keyboard.append(keyboardline)

    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(text=texto, parse_mode="HTML", reply_markup=reply_markup)
    return PAGAR


def terminar_pagar(update: Update, context: CallbackContext):
    gastos = db.select("gastos")
    id_gasto = int(update.callback_query.data.replace("PAGAR", ""))
    gasto = gastos[gastos.id == id_gasto].squeeze()
    db.update_gasto(id_gasto)
    texto = f"Se te ha pagado el gasto '{gasto.motivo}' por valor de {gasto.cantidad}€ en la fecha {gasto.fecha.strftime('%d/%m/%Y')}"
    context.bot.sendMessage(chat_id=int(gasto.id_persona), text=texto)
    update.callback_query.delete_message()
    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUAR")),
                 InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]

    context.bot.sendMessage(update.effective_chat.id, text="Quieres pagar a alguien mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))
    return FINAL_OPTION


def terminar(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha salido de tesoreria")
    return ConversationHandler.END


def get_conv_handler_tesoreria():
    conv_handler_tesoreria = ConversationHandler(
        entry_points=[CommandHandler('tesoreria', tesoreria)],
        states={
            OPCION: [CallbackQueryHandler(terminar, pattern='^TERMINAR$'),
                     CallbackQueryHandler(pagar, pattern='^PAGO$'),
                     CallbackQueryHandler(bote),
                     ],
            BOTE: [MessageHandler(Filters.text & ~Filters.command, bote2)],
            BOTE2: [MessageHandler(Filters.text & ~Filters.command, bote3)],
            PAGAR: [CallbackQueryHandler(terminar, pattern='^TERMINAR$'),
                    CallbackQueryHandler(terminar_pagar, pattern='^PAGAR')],
            FINAL_OPTION: [
                CallbackQueryHandler(pagar, pattern='^CONTINUAR$'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR')],
        },
        fallbacks=[CommandHandler('tesoreria', tesoreria)],
    )
    return conv_handler_tesoreria
