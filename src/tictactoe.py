from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler, ContextTypes

import pandas as pd
import src.utilitys as ut
import re
from datetime import datetime
from utils import database as db
from decouple import config
from utils.logger_config import logger

SELECT_TYPE, SELECT_ENEMY, CREATE_LIST2, CREATE_LIST3, DELETE_LIST, FINAL_OPTION = range(6)
ID_MANITOBA = int(config("ID_MANITOBA"))


def check_win(board: list):
    for row in board:
        if len(set(row)) == 1 and row[0] != 0:
            return row[0]

    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] and board[0][col] != 0:
            return board[0][col]

    if board[0][0] == board[1][1] == board[2][2] and board[0][0] != 0:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] != 0:
        return board[0][2]

    return 0


async def tictoactoe_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.effective_chat.id == ID_MANITOBA:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando tictactoe desde Manitoba")
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /3enraya")
        return ConversationHandler.END
    if update.message:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando tictactoe")
    else:
        await update.callback_query.delete_message()
        logger.warning(f"{context.user_data['user'].apodo} ha vuelto al inicio de tictactoe")

    text = f"¿A que quieres jugar?\n"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("3 en raya", callback_data="3")],
                                         [InlineKeyboardButton("4 en raya", callback_data="4")]])

    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    return SELECT_TYPE


async def challengue_tictoactoe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    query = update.callback_query
    await query.answer()
    context.user_data["type_game"] = query.data

    keyboard = []
    part_keyboard = []
    data = db.select("data")
    data = data[~(data.id == update.effective_user.id)].reset_index(drop=True)
    for i, persona in data.sort_values(by="apodo", ignore_index=True).iterrows():
        part_keyboard.append(InlineKeyboardButton(persona.apodo, callback_data=str(persona.id)))
        if i % 3 == 2 or i == len(data) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="CANCEL")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(parse_mode="HTML", reply_markup=reply_markup, text="<b>¿A quién quieres retar?</b>")
    logger.warning(f"{context.user_data['user'].apodo} ha asignado a {query.data} a la tarea")
    return SELECT_ENEMY


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    query = update.callback_query
    await query.answer()
    context.user_data["type_game"] = query.data


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('3enraya', tictoactoe_state)],
        states={
            SELECT_TYPE: [CallbackQueryHandler(challengue_tictoactoe)]

        },
        fallbacks=[CommandHandler('3enraya', tictoactoe_state)],
    )
