from utils.logger_config import logger
from decouple import config

from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import src.utilitys as ut
from utils import database as db

ID_MANITOBA = int(config("ID_MANITOBA"))

SELECT_POLL = 0


async def polls_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.message:
        await update.message.delete()
    if update.effective_chat.id == ID_MANITOBA:
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /encuestas")
        return ConversationHandler.END
    polls = db.select("encuestas")
    polls = polls[~polls.finished].reset_index()

    logger.warning(f"{context.user_data['user'].apodo} entró en el comando encuestas")

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

    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    return SELECT_POLL


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ut.set_actual_user(update.effective_user.id, context)
    polls = db.select("encuestas")
    actual_poll = update.effective_message.poll

    poll = polls[polls.id == int(actual_poll.id)].squeeze()
    # await context.bot.forwardMessage(chat_id=ID_MANITOBA, from_chat_id=ID_MANITOBA, message_id=2993)

    if actual_poll.is_anonymous:
        return

    await update.effective_message.delete()
    if not poll.empty:
        logger.warning(f"{context.user_data['user'].apodo} ha reenviado la encuesta {poll.question}")
        await context.bot.forwardMessage(chat_id=ID_MANITOBA, from_chat_id=ID_MANITOBA, message_id=int(poll.message_id))
    else:

        options = [o.text.replace("'", "") for o in actual_poll.options]
        logger.warning(f"{context.user_data['user'].apodo} ha creado la encuesta {actual_poll.question} - {options}")
        if len(options) < 10:
            options += ["NS/NC - No puedo"]

        new_poll = await context.bot.send_poll(ID_MANITOBA,
                                               question=actual_poll.question.replace("'", ""),
                                               options=options,
                                               is_anonymous=False,
                                               allows_multiple_answers=actual_poll.allows_multiple_answers)

        url = f"https://t.me/c/{str(new_poll.chat.id)[4:]}/{new_poll.message_id}"

        db.insert_poll(new_poll.poll.id, new_poll.poll.question, options, [], url, new_poll.message_id)


async def democracy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando democracia")
    data = db.select("data")
    polls = db.select("encuestas")
    polls = polls[~polls.finished]
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
                await context.bot.sendMessage(chat_id=persona.id, parse_mode="HTML", text=text2)
            except Exception as error:
                logger.warning(f"{persona.apodo} con id {persona.id} NO tiene activado el bot -> {error}")

    await context.bot.sendMessage(ID_MANITOBA, parse_mode="HTML", text=text1)


async def bot_activated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{context.user_data['user'].apodo} ha ejecutado el comando bot_activado")
    data = db.select("data")
    db.update_bot_activated_all()
    for _, person in data.iterrows():
        try:
            message = await context.bot.sendMessage(chat_id=person.id, parse_mode="HTML", text="Test de bot activado")
            await message.delete()
        except Exception as error:
            db.update_fields_table(table="data", idx=person.id, activado=False)

            await update.effective_chat.send_message(parse_mode="HTML", text=f"{person.apodo} con id {person.id} NO tiene activado el bot")
            logger.warning(f"{person.apodo} con id {person.id} NO tiene activado el bot -> {error}")


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando encuestas")

    return ConversationHandler.END


async def view_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_id = int(update.callback_query.data.replace("VIEW", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()

    message_id = int(poll.message_id)
    await update.callback_query.delete_message()
    message = await context.bot.forwardMessage(chat_id=update.effective_chat.id, from_chat_id=ID_MANITOBA, message_id=message_id)
    if update.effective_chat.id == ID_MANITOBA:
        db.update_poll(poll.id, poll.votes, message.message_id, poll.last_vote)
        try:
            await context.bot.deleteMessage(ID_MANITOBA, message_id)
        except Exception as error:
            logger.error(f"No se puede eliminar el mensaje -> {error}")

    await polls_state(update, context)


async def delete_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_id = int(update.callback_query.data.replace("DELETE", ""))
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()

    message_id = int(poll.message_id)
    db.delete("encuestas", poll.id)
    await update.callback_query.delete_message()
    try:
        await context.bot.deleteMessage(ID_MANITOBA, message_id)
    except Exception as error:
        logger.error(f"No se puede eliminar el mensaje de la encuesta-> {error}")
    await polls_state(update, context)


async def end_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_id = int(update.callback_query.data.replace("CLOSE", ""))
    data = db.select("data")
    polls = db.select("encuestas")
    poll = polls[polls.id == poll_id].squeeze()
    await update.callback_query.delete_message()

    logger.warning(f"{context.user_data['user'].apodo} ha cerrado la encuesta {poll.question}")
    text = f"La encuesta {poll.question} ha finalizado.\n"
    text2 = f"Estos son los miserables que odian la democracia:\n"
    all_voted = True
    for _, persona in data.iterrows():
        if persona.id not in poll.votes:
            all_voted = False
            text2 += f"<a href='tg://user?id={persona.id}'>{persona.apodo}</a>\n"
    if not all_voted:
        text += text2
    db.update_fields_table(table="encuestas", idx=poll.id, finished=True)

    await context.bot.stopPoll(ID_MANITOBA, int(poll.message_id))
    await context.bot.forwardMessage(ID_MANITOBA, ID_MANITOBA, int(poll.message_id))
    await context.bot.sendMessage(ID_MANITOBA, text, parse_mode="HTML")

    await polls_state(update, context)


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
