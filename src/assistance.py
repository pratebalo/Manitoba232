from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

from decouple import config
from datetime import datetime
from utils import sheets_drive
import logging
import utils.gillweb
import src.utilitys as ut
import utils.database as db

# Stages
ASSISTANCE, SELECT_SECTION, SELECT_NAME, SELECT_PERSON, SELECT_PERSON2, EDIT_ASSISTANCE, DELETE_ASSISTANCE, FINAL_OPTION = range(8)

ID_MANITOBA = int(config("ID_MANITOBA"))
logger = logging.getLogger("tareas")
download_thread = None


def assistance_state(update: Update, context: CallbackContext):
    if update.message:
        update.message.delete()
    else:
        update.callback_query.delete_message()
    if update.effective_chat.id == ID_MANITOBA:
        context.bot.sendMessage(chat_id=update.effective_user.id, text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /asistencia")
        return
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} entro en el comando asistencia")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Añadir asistencia", callback_data="ADD")],
                                         [InlineKeyboardButton("Modificar asistencia", callback_data="EDIT")],
                                         [InlineKeyboardButton("Ver resumen asistencia", callback_data="VIEW")],
                                         [InlineKeyboardButton("Terminar", callback_data="END")]])
    context.bot.sendMessage(update.effective_chat.id, "<b>¿Qué quieres hacer?</b>", reply_markup=reply_markup, parse_mode="HTML")
    return ASSISTANCE


def select_section_assistance(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} seleccionó {update.callback_query.data}")
    action = update.callback_query.data
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Castores", callback_data=f"{action}1")],
                                         [InlineKeyboardButton("Manada", callback_data=f"{action}2")],
                                         [InlineKeyboardButton("Tropa", callback_data=f"{action}3")],
                                         [InlineKeyboardButton("Escultas", callback_data=f"{action}4")],
                                         [InlineKeyboardButton("Rover", callback_data=f"{action}5")],
                                         [InlineKeyboardButton("Terminar", callback_data="END")]])
    update.callback_query.edit_message_text("<b>Elige la unidad:</b>", reply_markup=reply_markup, parse_mode='HTML')
    return SELECT_SECTION


def view_assistance_state(update: Update, context: CallbackContext):
    section = update.callback_query.data.replace('VIEW', '')
    sheet_id = sheets_drive.sheet_sections[int(section)]
    context.bot.sendMessage(update.effective_user.id, text=f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0')
    assistance_state(update, context)
    return ASSISTANCE


def edit_assistance_state(update: Update, context: CallbackContext):
    context.user_data['section'] = update.callback_query.data.replace('EDIT', '')
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} selecionó {context.user_data['section']}")
    meetings = db.select_where('assistance', ['section'], [context.user_data['section']])
    keyboard = []
    for meeting in meetings.itertuples(index=False):
        keyboard.append([InlineKeyboardButton(meeting.meeting_name, callback_data="None"),
                         InlineKeyboardButton("✍️", callback_data=f"EDIT{meeting.id}"),
                         InlineKeyboardButton("🗑️", callback_data=f"DELETE{meeting.id}")])

    keyboard.append([InlineKeyboardButton("Terminar", callback_data="END")])
    update.callback_query.edit_message_text('<b>¿Qúe reunión quieres editar?</b>', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    context.user_data["data_gillweb"] = get_persons_gillweb(context.user_data['section'])
    context.user_data["action"] = "EDIT"
    return EDIT_ASSISTANCE


def add_assistance_name(update: Update, context: CallbackContext):
    context.user_data['section'] = update.callback_query.data.replace('ADD', '')
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} selecionó {context.user_data['section']}")

    text = "<b>Escribe el nombre de la actividad:</b>\nReunión 17/02 /// Acampada de Navidad /// Consejo"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Terminar", callback_data=str("END"))]])
    context.user_data['oldMessage'] = update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')

    context.user_data["data_gillweb"] = get_persons_gillweb(context.user_data['section'])
    context.user_data["assigned_persons"] = []
    context.user_data["action"] = "ADD"
    return SELECT_NAME


def get_persons_gillweb(section):
    data_gillweb = utils.gillweb.download_data_gillweb(section)
    data_gillweb['unique_name'] = data_gillweb['name']
    duplicates = data_gillweb['name'].duplicated(keep=False)
    for index, is_duplicate in enumerate(duplicates):
        if is_duplicate:
            name = data_gillweb.at[index, 'name']
            surname = data_gillweb.at[index, 'surname']
            counter = 1
            while True:
                new_name = f"{name} {surname[:counter]}"
                if not data_gillweb['unique_name'].str.contains(new_name).any():
                    data_gillweb.at[index, 'unique_name'] = new_name
                    break
                counter += 1
    return data_gillweb[['id', 'unique_name']]


def assign_persons(update: Update, context: CallbackContext):
    if update.message:
        context.user_data['meeting_name'] = update.message.text
        update.message.delete()
        context.bot.deleteMessage(context.user_data['oldMessage'].chat_id, context.user_data['oldMessage'].message_id)
    else:
        if 'EDIT' in update.callback_query.data:
            meeting_id = update.callback_query.data.replace('EDIT', '')
            context.user_data['meeting_id'] = meeting_id
            meeting = db.select_where('assistance', ['id'], [int(meeting_id)]).squeeze()
            context.user_data['assigned_persons'] = meeting.people_id
        else:
            if int(update.callback_query.data) in context.user_data['assigned_persons']:
                context.user_data['assigned_persons'].remove(int(update.callback_query.data))
            else:
                context.user_data['assigned_persons'].append(int(update.callback_query.data))
    data_gillweb = context.user_data["data_gillweb"]
    keyboard = []
    part_keyboard = []
    for i, persona in data_gillweb.sort_values(by="unique_name", ignore_index=True).iterrows():
        part_keyboard.append(InlineKeyboardButton(
            f"{persona.unique_name} {'✅' if persona.id in context.user_data['assigned_persons'] else '❌'}", callback_data=persona.id))
        if i % 3 == 2 or i == len(data_gillweb) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []

    keyboard.append([InlineKeyboardButton("Confirmar asistencia", callback_data="CONFIRM")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        update.callback_query.edit_message_text(parse_mode="HTML", reply_markup=reply_markup, text="<b>¿Quiénes han asistido?</b>")
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id, parse_mode="HTML", reply_markup=reply_markup, text="<b>¿Quiénes han asistido?</b>")

    return SELECT_PERSON


def end_creation(update: Update, context: CallbackContext):
    if context.user_data["action"] == "ADD":
        db.insert_into_table(["section", "meeting_name", "people_id", "date"],
                             [context.user_data['section'], context.user_data['meeting_name'],
                              context.user_data['assigned_persons'], datetime.today().strftime('%d/%m/%Y')],
                             "assistance")
    else:
        db.update_field_table(int(context.user_data['meeting_id']), ["people_id"], [context.user_data['assigned_persons']], "assistance")
    assistance_state(update, context)
    sheets_drive.generate_sheet_assistance(int(context.user_data['section']))
    return ASSISTANCE


def delete_assistance(update: Update, context: CallbackContext):
    text = f"¿Seguro que quieres eliminar la asistencia?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data=update.callback_query.data),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_ASSISTANCE


def delete_assistance2(update: Update, context: CallbackContext):
    id_assistance = int(update.callback_query.data.replace("DELETE", ""))
    assist = db.delete("assistance", id_assistance).iloc[0]
    logger.warning(f"{update.effective_chat.type} -> {update.effective_user.first_name} ha eliminado la asistencia '{assist}'")
    assistance_state(update, context)
    sheets_drive.generate_sheet_assistance(int(context.user_data['section']))
    return ASSISTANCE


for i in range(1, 6):
    sheets_drive.generate_sheet_assistance(i)


def end(update: Update, _: CallbackContext):
    update.callback_query.delete_message()

    return ConversationHandler.END


def get_conv_handler_assistance():
    return ConversationHandler(
        entry_points=[CommandHandler('asistencia', assistance_state)],
        states={
            ASSISTANCE: [CallbackQueryHandler(select_section_assistance, pattern='^ADD'),
                         CallbackQueryHandler(select_section_assistance, pattern='^EDIT'),
                         CallbackQueryHandler(select_section_assistance, pattern='^VIEW'),
                         CallbackQueryHandler(end, pattern='^END')],
            SELECT_SECTION: [CallbackQueryHandler(add_assistance_name, pattern='^ADD'),
                             CallbackQueryHandler(edit_assistance_state, pattern='^EDIT'),
                             CallbackQueryHandler(view_assistance_state, pattern='^VIEW'),
                             CallbackQueryHandler(end, pattern='^END')],
            SELECT_NAME: [MessageHandler(Filters.text & ~Filters.command, assign_persons),
                          CallbackQueryHandler(end, pattern='^END')],
            EDIT_ASSISTANCE: [CallbackQueryHandler(assign_persons, pattern='^EDIT'),
                              CallbackQueryHandler(delete_assistance, pattern='^DELETE'),
                              CallbackQueryHandler(end, pattern='^END')],
            DELETE_ASSISTANCE: [CallbackQueryHandler(delete_assistance2, pattern='^DELETE'),
                                CallbackQueryHandler(assistance_state, pattern='^BACK')],
            # CREAR_TAREA1: [MessageHandler(Filters.text & ~Filters.command, elegir_fecha)],
            # CREAR_TAREA2: [CallbackQueryHandler(elegir_fecha2)],
            SELECT_PERSON: [CallbackQueryHandler(end_creation, pattern='^CONFIRM$'),
                            CallbackQueryHandler(assign_persons)],
            # FINAL_OPTION: [
            #     CallbackQueryHandler(tareas, pattern='^CONTINUAR$'),
            #     CallbackQueryHandler(editar_tarea, pattern='^CONTINUAR_EDITAR$'),
            #     CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
        },
        fallbacks=[CommandHandler('asistencia', assistance_state)],
    )
