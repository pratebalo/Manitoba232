from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters

from decouple import config
from datetime import datetime
from utils import sheets_drive
from utils.logger_config import logger
import utils.gillweb
import src.utilitys as ut
import utils.database as db

# Stages
ASSISTANCE, SELECT_SECTION, SELECT_NAME, SELECT_PERSON, SELECT_PERSON2, EDIT_ASSISTANCE, DELETE_ASSISTANCE, FINAL_OPTION = range(8)

ID_MANITOBA = int(config("ID_MANITOBA"))


async def assistance_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.effective_chat.id == ID_MANITOBA:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando asistencia desde Manitoba")
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /asistencia")
        return ConversationHandler.END

    if update.message:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entro en el comando asistencia")
    else:
        await update.callback_query.delete_message()
        logger.warning(f"{context.user_data['user'].apodo} ha vuelto al inicio de asistencia")

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Añadir asistencia", callback_data="ADD")],
                                         [InlineKeyboardButton("Modificar asistencia", callback_data="EDIT")],
                                         [InlineKeyboardButton("Ver resumen asistencia", callback_data="VIEW")],
                                         [InlineKeyboardButton("Terminar", callback_data="END")]])
    await update.effective_chat.send_message("<b>¿Qué quieres hacer?</b>", reply_markup=reply_markup, parse_mode="HTML")
    return ASSISTANCE


async def select_section_assistance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} seleccionó {update.callback_query.data}")
    action = update.callback_query.data
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Castores", callback_data=f"{action}1")],
                                         [InlineKeyboardButton("Manada", callback_data=f"{action}2")],
                                         [InlineKeyboardButton("Tropa", callback_data=f"{action}3")],
                                         [InlineKeyboardButton("Escultas", callback_data=f"{action}4")],
                                         [InlineKeyboardButton("Rover", callback_data=f"{action}5")],
                                         [InlineKeyboardButton("Terminar", callback_data="END")]])
    await update.callback_query.edit_message_text("<b>Elige la unidad:</b>", reply_markup=reply_markup, parse_mode='HTML')
    return SELECT_SECTION


async def view_assistance_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    section = update.callback_query.data.replace('VIEW', '')
    logger.warning(f"{context.user_data['user'].apodo} seleccionó ver la sección {section}")
    sheet_id = sheets_drive.sheet_sections[int(section)]
    await update.effective_chat.send_message(text=f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0')
    await assistance_state(update, context)
    return ASSISTANCE


async def edit_assistance_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['section'] = update.callback_query.data.replace('EDIT', '')
    logger.warning(f"{context.user_data['user'].apodo} selecionó editar la sección {context.user_data['section']}")
    meetings = db.select_where('assistance', ['section'], [context.user_data['section']])
    keyboard = []
    for meeting in meetings.itertuples(index=False):
        keyboard.append([InlineKeyboardButton(meeting.meeting_name, callback_data="None"),
                         InlineKeyboardButton("✍️", callback_data=f"EDIT{meeting.id}"),
                         InlineKeyboardButton("🗑️", callback_data=f"DELETE{meeting.id}")])

    keyboard.append([InlineKeyboardButton("Terminar", callback_data="END")])
    await update.callback_query.edit_message_text('<b>¿Qúe reunión quieres editar?</b>', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    context.user_data["data_gillweb"] = get_persons_gillweb(context.user_data['section'])
    context.user_data["action"] = "EDIT"
    return EDIT_ASSISTANCE


async def add_assistance_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['section'] = update.callback_query.data.replace('ADD', '')
    logger.warning(f"{context.user_data['user'].apodo} selecionó añadir a la sección {context.user_data['section']}")

    text = "<b>Escribe el nombre de la actividad:</b>\nReunión 17/02 /// Acampada de Navidad /// Consejo"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Terminar", callback_data=str("END"))]])
    context.user_data['oldMessage'] = await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')

    context.user_data["data_gillweb"] = get_persons_gillweb(context.user_data['section'])
    context.user_data["assigned_persons"] = []
    context.user_data["action"] = "ADD"
    return SELECT_NAME


async def assign_persons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        context.user_data['meeting_name'] = update.message.text
        await update.message.delete()
        await context.user_data['oldMessage'].delete()
        logger.warning(f"{context.user_data['user'].apodo} escribió {context.user_data['meeting_name']}")
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
    data_gillweb['unique_name2'] = data_gillweb['unique_name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    for i, persona in data_gillweb.sort_values(by="unique_name2", ignore_index=True).iterrows():
        part_keyboard.append(InlineKeyboardButton(
            f"{persona.unique_name} {'✅' if persona.id in context.user_data['assigned_persons'] else '❌'}", callback_data=persona.id))
        if i % 3 == 2 or i == len(data_gillweb) - 1:
            keyboard.append(part_keyboard)
            part_keyboard = []

    keyboard.extend([[InlineKeyboardButton("Confirmar asistencia", callback_data="CONFIRM")],
                     [InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(parse_mode="HTML", reply_markup=reply_markup, text="<b>¿Quiénes han asistido?</b>")
    else:
        await update.effective_chat.send_message(parse_mode="HTML", reply_markup=reply_markup, text="<b>¿Quiénes han asistido?</b>")

    return SELECT_PERSON


async def end_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data["action"] == "ADD":
        assist = db.insert_into_table(["section", "meeting_name", "people_id", "date"],
                                      [context.user_data['section'], context.user_data['meeting_name'],
                                       context.user_data['assigned_persons'], datetime.today().strftime('%d/%m/%Y')],
                                      "assistance")
        logger.warning(f"{update.effective_user.first_name} ha añadido la asistencia '{assist.squeeze().to_list()}'")
    else:
        assist = db.update_fields_table(table="assistance", idx=int(context.user_data['meeting_id']), people_id=context.user_data['assigned_persons'])
        logger.warning(f"{update.effective_user.first_name} ha actualizado la asistencia '{assist.squeeze().to_list()}'")
    await assistance_state(update, context)
    sheets_drive.generate_sheet_assistance(int(context.user_data['section']))
    return ASSISTANCE


async def delete_assistance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} selectionó eliminar la asistencia")
    text = f"¿Seguro que quieres eliminar la asistencia?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data=update.callback_query.data),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_ASSISTANCE


async def delete_assistance2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_assistance = int(update.callback_query.data.replace("DELETE", ""))
    assist = db.delete("assistance", id_assistance).iloc[0]
    logger.warning(f"{update.effective_user.first_name} ha eliminado la asistencia '{assist.to_list()}'")
    await assistance_state(update, context)
    sheets_drive.generate_sheet_assistance(int(context.user_data['section']))
    return ASSISTANCE


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando asistencia")
    return ConversationHandler.END


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


def get_conv_handler():
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
            SELECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_persons),
                          CallbackQueryHandler(end, pattern='^END')],
            EDIT_ASSISTANCE: [CallbackQueryHandler(assign_persons, pattern='^EDIT'),
                              CallbackQueryHandler(delete_assistance, pattern='^DELETE'),
                              CallbackQueryHandler(end, pattern='^END')],
            DELETE_ASSISTANCE: [CallbackQueryHandler(delete_assistance2, pattern='^DELETE'),
                                CallbackQueryHandler(assistance_state, pattern='^BACK')],
            # CREAR_TAREA1: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir_fecha)],
            # CREAR_TAREA2: [CallbackQueryHandler(elegir_fecha2)],
            SELECT_PERSON: [CallbackQueryHandler(end_creation, pattern='^CONFIRM$'),
                            CallbackQueryHandler(assistance_state, pattern='^CANCEL'),
                            CallbackQueryHandler(assign_persons)],
            # FINAL_OPTION: [
            #     CallbackQueryHandler(tareas, pattern='^CONTINUAR$'),
            #     CallbackQueryHandler(editar_tarea, pattern='^CONTINUAR_EDITAR$'),
            #     CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
        },
        fallbacks=[CommandHandler('asistencia', assistance_state)],
    )
