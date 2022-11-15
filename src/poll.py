import logging
import os

from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, KeyboardButtonPollType, \
    ReplyKeyboardMarkup

from utils import database as db

ID_MANITOBA = int(os.environ.get("ID_MANITOBA"))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger("poll")

ELEGIR_ENCUESTA, FINAL_OPTION = range(2)


def encuestas(update: Update, context: CallbackContext) -> None:
    polls = db.select("encuestas")
    polls = polls[~polls.end].reset_index()
    chat_id = update.effective_chat.id
    user = update.effective_user

    logger.warning(f"{update.effective_chat.type} -> {user.first_name} entró en el comando encuestas")

    keyboard = []
    text = f"{user.first_name} ¿Qué quieres hacer?\n"
    if polls.empty:
        keyboard.append([InlineKeyboardButton("No hay encuestas activas 😢", callback_data="NADA")])
    else:
        for i, poll in polls.iterrows():
            keyboardline = []
            text += f" {i + 1}. {poll.question}\n"
            keyboardline.append(InlineKeyboardButton(i + 1, callback_data="A"))
            keyboardline.append(InlineKeyboardButton("👀", callback_data="VER" + str(poll.id)))
            keyboardline.append(InlineKeyboardButton("🗑", callback_data="ELIMINAR" + str(poll.id)))
            keyboardline.append(InlineKeyboardButton("📯", callback_data="FINALIZAR" + str(poll.id)))
            keyboard.append(keyboardline)
        keyboard.append([InlineKeyboardButton("Democracia 🗳️", callback_data=str("DEMOCRACIA"))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["query_listas"] = context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    if update.message:
        context.bot.deleteMessage(chat_id, update.message.message_id)
    return ELEGIR_ENCUESTA


def receive_poll_answer(update: Update, context: CallbackContext) -> None:
    """Summarize a users poll vote"""
    data = db.select("data")
    user_id = int(update.poll_answer.user.id)
    polls = db.select("encuestas")
    poll_id = int(update.poll_answer.poll_id)
    poll = polls[polls.id == poll_id].squeeze()
    votes = poll.votes
    respuesta = update.poll_answer
    if not respuesta.option_ids:
        logger.warning(f"{update.effective_user.first_name} quito su voto de la encuesta {poll.question}")
        votes.remove(int(update.poll_answer.user.id))
        db.update_poll(poll_id, votes, poll.message_id)
    else:
        votes.append(user_id)
        votos = [poll.options[i] for i in respuesta.option_ids]
        restantes = data[~data.id.isin(votes)].apodo.tolist()
        logger.warning(
            f"{update.effective_user.first_name} ha votado {votos} en la encuesta {poll.question}. Restantes -> {restantes}")
        db.update_poll(poll_id, votes, poll.message_id)


def receive_poll(update: Update, context: CallbackContext) -> None:
    """On receiving polls, reply to it by a closed poll copying the received poll"""
    actual_poll = update.effective_message.poll
    logger.warning(f"{update.effective_user.first_name} ha creado la encuesta {actual_poll.question}")
    if not actual_poll.is_anonymous and not update.message.forward_from:

        update.effective_message.delete()
        options = [o.text.replace("'", "") for o in actual_poll.options]
        if len(options) < 10:
            options += ["NS/NC - No puedo"]
        if update.message.reply_to_message:
            if update.message.reply_to_message.forward_from_chat:
                new_poll = context.bot.send_poll(
                    update.effective_chat.id,
                    question=actual_poll.question.replace("'", ""),
                    options=options,
                    is_anonymous=False,
                    allows_multiple_answers=actual_poll.allows_multiple_answers,
                    reply_to_message_id=update.message.reply_to_message.message_id
                )

                url = f"https://t.me/c/{str(new_poll.chat.id)[4:]}/{new_poll.message_id}?thread={update.message.reply_to_message.message_id}"
            else:
                new_poll = context.bot.send_poll(
                    update.effective_chat.id,
                    question=actual_poll.question.replace("'", ""),
                    options=options,
                    is_anonymous=False,
                    allows_multiple_answers=actual_poll.allows_multiple_answers
                )
                url = f"https://t.me/c/{str(new_poll.chat.id)[4:]}/{new_poll.message_id}"
        else:
            new_poll = context.bot.send_poll(
                update.effective_chat.id,
                question=actual_poll.question.replace("'", ""),
                options=options,
                is_anonymous=False,
                allows_multiple_answers=actual_poll.allows_multiple_answers
            )
            url = f"https://t.me/c/{str(new_poll.chat.id)[4:]}/{new_poll.message_id}"

        db.insert_poll(new_poll.poll.id, new_poll.poll.question, options, [], url, update.message.chat_id,
                       new_poll.message_id)


def democracia(update: Update, context: CallbackContext) -> None:
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_user.first_name} ha ejecutado el comando democracia")
    data = db.select("data")
    encuestas = db.select("encuestas")
    encuestas = encuestas[~encuestas.end]
    texto = "Estos son los miserables que odian la democracia:\n"
    for _, persona in data.iterrows():
        questions = ""
        total = 0
        for _, encuesta in encuestas.iterrows():
            if persona.id not in encuesta.votes:
                questions += f"- <a href='{encuesta.url}'>{encuesta.question}</a>\n"
                total += 1

        if questions:
            texto += f"- <a href='tg://user?id={persona.id}'>{persona.apodo}</a>"
            if total == 1:
                texto += "\n"
            else:
                texto += f"x{total}\n"
            text = f"{persona.apodo}, al vivir en una democracia tienes derecho a votar en las encuestas\n" + questions
            try:
                context.bot.sendMessage(chat_id=persona.id, parse_mode="HTML", text=text)
            except:
                print(f"{persona.apodo} con id {persona.id} NO tiene activado el bot")

    context.bot.sendMessage(update.effective_chat.id, parse_mode="HTML", text=texto)


def bot_activado(update: Update, context: CallbackContext) -> None:
    logger.warning(f"{update.effective_user.first_name} ha ejecutado el comando bot_activado")
    data = db.select("data")
    for _, persona in data.iterrows():
        try:
            mensaje = context.bot.sendMessage(chat_id=persona.id, parse_mode="HTML", text="prueba")
            context.bot.deleteMessage(mensaje.chat_id, mensaje.message_id)
            # print(f"{persona.apodo} con id {persona.id} tiene activado el bot")
        except:
            print(f"{persona.apodo} con id {persona.id} NO tiene activado el bot")


def terminar(update: Update, context: CallbackContext):
    update.callback_query.delete_message()

    return ConversationHandler.END


def ver_encuesta(update: Update, context: CallbackContext):
    id_encuesta = int(update.callback_query.data.replace("VER", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == id_encuesta].squeeze()

    chat = int(poll.chat_id)
    id_mensaje = int(poll.message_id)
    try:
        update.callback_query.delete_message()
    except:
        print(f"No se puede eliminar el mensaje")

    message = context.bot.forwardMessage(chat, int(poll.chat_id), id_mensaje, )
    db.update_poll(poll.id, poll.votes, message.message_id)
    try:
        context.bot.deleteMessage(chat, id_mensaje)
    except:
        print(f"No se puede eliminar el mensaje")
    encuestas(update, context)


def eliminar_encuesta(update: Update, context: CallbackContext):
    id_encuesta = int(update.callback_query.data.replace("ELIMINAR", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == id_encuesta].squeeze()

    chat = int(poll.chat_id)
    id_mensaje = int(poll.message_id)
    db.delete("encuestas", poll.id)
    update.callback_query.delete_message()
    try:
        context.bot.deleteMessage(chat, id_mensaje)
        # print(f"{persona.apodo} con id {persona.id} tiene activado el bot")
    except:
        print(f"No se puede eliminar el mensaje")
    encuestas(update, context)


def finalizar_encuesta(update: Update, context: CallbackContext):
    id_encuesta = int(update.callback_query.data.replace("FINALIZAR", ""))
    data = db.select("data")
    polls = db.select("encuestas")
    poll = polls[polls.id == id_encuesta].squeeze()
    update.callback_query.delete_message()

    logger.warning(f"{update.effective_user.first_name} ha ejecutado el comando democracia")
    texto = f"La encuesta {poll.question} ha finalizado.\n"
    texto2 = f"Estos son los miserables que odian la democracia:\n"
    all_voted = True
    for _, persona in data.iterrows():
        if persona.id not in poll.votes:
            all_voted = False
            texto2 += f"<a href='tg://user?id={persona.id}'>{persona.apodo}</a>\n"
    if not all_voted:
        texto += texto2
    db.end_poll(poll.id)
    context.bot.stopPoll(int(poll.chat_id), int(poll.message_id))
    context.bot.forwardMessage(int(poll.chat_id), int(poll.chat_id), int(poll.message_id), )
    context.bot.sendMessage(ID_MANITOBA, texto, parse_mode="HTML")

    encuestas(update, context)


conv_handler_encuestas = ConversationHandler(
    entry_points=[CommandHandler('encuestas', encuestas)],
    states={
        ELEGIR_ENCUESTA: [
            CallbackQueryHandler(ver_encuesta, pattern='^VER'),
            CallbackQueryHandler(eliminar_encuesta, pattern='^ELIMINAR'),
            CallbackQueryHandler(finalizar_encuesta, pattern='^FINALIZAR'),
            CallbackQueryHandler(democracia, pattern='^DEMOCRACIA'),
            CallbackQueryHandler(terminar, pattern='^TERMINAR$')
        ],
        FINAL_OPTION: [
            CallbackQueryHandler(encuestas, pattern='^CONTINUAR$'),

            CallbackQueryHandler(terminar, pattern='^TERMINAR')]},
    fallbacks=[CommandHandler('encuestas', encuestas)],
)
