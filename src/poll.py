from utils import logger_config
from decouple import config

from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import src.utilitys as ut
from utils import database as db

ID_MANITOBA = int(config("ID_MANITOBA"))

logger = logger_config.logger

SELECT_POLL = 0


def polls_state(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)
    chat_id = update.effective_chat.id
    if update.message:
        context.bot.deleteMessage(chat_id, update.message.message_id)
    if update.effective_chat.id == ID_MANITOBA:
        context.bot.sendMessage(chat_id=update.effective_user.id, text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /encuestas")
        return
    polls = db.select("encuestas")
    polls = polls[~polls.end].reset_index()

    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} entró en el comando encuestas")

    keyboard = []
    text = f"{context.user_data['user'].apodo} ¿Qué quieres hacer?\n"
    if polls.empty:
        keyboard.append([InlineKeyboardButton("No hay encuestas activas 😢", callback_data="NOTHING")])
    else:
        for i, poll in polls.iterrows():
            keyboard_line = []
            text += f" {i + 1}. {poll.question}\n"
            keyboard_line.append(InlineKeyboardButton(i + 1, callback_data="A"))
            keyboard_line.append(InlineKeyboardButton("👀", callback_data="VIEW" + str(poll.id)))
            keyboard_line.append(InlineKeyboardButton("🗑", callback_data="DELETE" + str(poll.id)))
            keyboard_line.append(InlineKeyboardButton("📯", callback_data="CLOSE" + str(poll.id)))
            keyboard.append(keyboard_line)
        keyboard.append([InlineKeyboardButton("Democracia 🗳️", callback_data=str("DEMOCRACY"))])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data=str("END"))])
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    return SELECT_POLL


def receive_poll_answer(update: Update, context: CallbackContext) -> None:
    """Summarize a users poll vote"""
    ut.set_actual_user(update.effective_user.id, context)
    data = db.select("data")
    user_id = str(update.poll_answer.user.id)
    polls = db.select("encuestas")
    poll_id = int(update.poll_answer.poll_id)
    poll = polls[polls.id == poll_id].squeeze()
    all_votes = poll.votes
    poll_answer = update.poll_answer
    if not poll_answer.option_ids:
        logger.warning(f"{context.user_data['user'].apodo} quito su voto de la encuesta {poll.question}")
        all_votes.remove(int(user_id))
    else:
        all_votes.append(int(user_id))
        votes = [poll.options[i] for i in poll_answer.option_ids]
        without_vote = data[~data.id.isin(all_votes)].apodo.tolist()
        if user_id in poll.last_vote.keys():
            added = list(set(votes) - set(poll.last_vote[user_id]))
            removed = list(set(poll.last_vote[user_id]) - set(votes))
            logger.warning(f"{context.user_data['user'].apodo} ha quitado {removed} y ha añadido {added} "
                           f"dejando {votes} en la encuesta {poll.question}. Restantes -> {without_vote}")
        else:
            logger.warning(f"{context.user_data['user'].apodo} ha votado {votes} en la encuesta {poll.question}. Restantes -> {without_vote}")

        poll.last_vote[user_id] = votes

    db.update_poll(poll_id, all_votes, poll.message_id, poll.last_vote)


def receive_poll(update: Update, context: CallbackContext) -> None:
    """On receiving polls, reply to it by a closed poll copying the received poll"""
    ut.set_actual_user(update.effective_user.id, context)
    actual_poll = update.effective_message.poll
    logger.warning(f"{context.user_data['user'].apodo} ha creado la encuesta {actual_poll.question}")
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

        db.insert_poll(new_poll.poll.id, new_poll.poll.question, options, [], url, update.message.chat_id, new_poll.message_id)


def democracy(update: Update, context: CallbackContext) -> None:
    update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando democracia")
    data = db.select("data")
    polls = db.select("encuestas")
    polls = polls[~polls.end]
    text1 = "Estos son los miserables que odian la democracia:\n"
    for _, persona in data.iterrows():
        questions = ""
        total = 0
        for _, poll in polls.iterrows():
            if persona.id not in poll.votes:
                questions += f"- <a href='{poll.url}'>{poll.question}</a>\n"
                total += 1

        if questions:
            text1 += f"- <a href='tg://user?id={persona.id}'>{persona.apodo}</a>"
            if total == 1:
                text1 += "\n"
            else:
                text1 += f"x{total}\n"
            text2 = f"{persona.apodo}, al vivir en una democracia tienes derecho a votar en las encuestas\n" + questions
            try:
                context.bot.sendMessage(chat_id=persona.id, parse_mode="HTML", text=text2)
            except Exception as error:
                logger.warning(f"{persona.apodo} con id {persona.id} NO tiene activado el bot -> {error}")

    context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=text1)


def bot_activated(update: Update, context: CallbackContext) -> None:
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando bot_activado")
    data = db.select("data")
    db.update_bot_activated_all()
    for _, person in data.iterrows():
        try:
            message = context.bot.sendMessage(chat_id=person.id, parse_mode="HTML", text="Test de bot activado")
            context.bot.deleteMessage(message.chat_id, message.message_id)
            # print(f"{persona.apodo} con id {persona.id} tiene activado el bot")
        except Exception as error:
            db.update_bot_not_activated(person.id)
            context.bot.sendMessage(chat_id=update.effective_chat.id, parse_mode="HTML",
                                    text=f"{person.apodo} con id {person.id} NO tiene activado el bot")
            logger.warning(f"{person.apodo} con id {person.id} NO tiene activado el bot -> {error}")


def end(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha salido del comando encuestas")

    return ConversationHandler.END


def view_poll(update: Update, context: CallbackContext):
    poll_id = int(update.callback_query.data.replace("VIEW", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()

    chat = int(poll.chat_id)
    message_id = int(poll.message_id)
    try:
        update.callback_query.delete_message()
    except Exception as error:
        logger.error(f"Fallo al eliminar el mensaje -> {error}")
    message = context.bot.forwardMessage(update.effective_chat.id, chat, message_id, )
    if update.effective_chat.id == chat:
        db.update_poll(poll.id, poll.votes, message.message_id, poll.last_vote)
        try:
            context.bot.deleteMessage(chat, message_id)
        except Exception as error:
            logger.error(f"No se puede eliminar el mensaje -> {error}")

    polls_state(update, context)


def delete_poll(update: Update, context: CallbackContext):
    poll_id = int(update.callback_query.data.replace("DELETE", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()

    chat = int(poll.chat_id)
    message_id = int(poll.message_id)
    db.delete("encuestas", poll.id)
    update.callback_query.delete_message()
    try:
        context.bot.deleteMessage(chat, message_id)
    except Exception as error:
        logger.error(f"No se puede eliminar el mensaje de la encuesta-> {error}")
    polls_state(update, context)


def end_poll(update: Update, context: CallbackContext):
    poll_id = int(update.callback_query.data.replace("CLOSE", ""))
    data = db.select("data")
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()
    update.callback_query.delete_message()

    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando democracia")
    text = f"La encuesta {poll.question} ha finalizado.\n"
    text2 = f"Estos son los miserables que odian la democracia:\n"
    all_voted = True
    for _, persona in data.iterrows():
        if persona.id not in poll.votes:
            all_voted = False
            text2 += f"<a href='tg://user?id={persona.id}'>{persona.apodo}</a>\n"
    if not all_voted:
        text += text2
    db.end_poll(poll.id)
    context.bot.stopPoll(int(poll.chat_id), int(poll.message_id))
    context.bot.forwardMessage(int(poll.chat_id), int(poll.chat_id), int(poll.message_id), )
    context.bot.sendMessage(ID_MANITOBA, text, parse_mode="HTML")

    polls_state(update, context)


def get_conv_handler_polls():
    conv_handler_polls = ConversationHandler(
        entry_points=[CommandHandler('encuestas', polls_state)],
        states={
            SELECT_POLL: [
                CallbackQueryHandler(view_poll, pattern='^VIEW'),
                CallbackQueryHandler(delete_poll, pattern='^DELETE'),
                CallbackQueryHandler(end_poll, pattern='^CLOSE'),
                CallbackQueryHandler(democracy, pattern='^DEMOCRACY'),
                CallbackQueryHandler(end, pattern='^END$')
            ]
        },
        fallbacks=[CommandHandler('encuestas', polls_state)]
    )
    return conv_handler_polls
